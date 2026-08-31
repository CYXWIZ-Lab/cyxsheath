"""Inspect the pinned llmster ZIP metadata without reading member contents."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
import stat
import struct
import unicodedata
from pathlib import Path
from typing import BinaryIO
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile


ARCHIVE_RELATIVE = Path(
    ".replay_cache/llmster_acquisition/0.0.21-2-win32-x64.full.zip"
)
EXPECTED_BYTES = 867_394_409
EXPECTED_SHA256 = "e6556e8edd7240c43da28aa555bac12197ba3e2199247bba773c81c6ae94170c"
EXPECTED_SHA512 = (
    "ec13183ddc2f56d68b48fc13428e0cdca84c29bfc2b87a7aa2b9befeb7b79a8c"
    "dd3ea5a7c50d6e941fcf43545c8730f8b2bf2665b030b98e5ccfab6a3d43efff"
)
MAXIMUM_ENTRIES = 50_000
MAXIMUM_CENTRAL_DIRECTORY_BYTES = 33_554_432
MAXIMUM_TOTAL_UNCOMPRESSED_BYTES = 4_294_967_296
MAXIMUM_ENTRY_UNCOMPRESSED_BYTES = 2_147_483_648
MAXIMUM_COMPRESSION_RATIO_MILLI = 500_000
MAXIMUM_PATH_CHARACTERS = 1_024
ALLOWED_COMPRESSION_METHODS = {ZIP_STORED, ZIP_DEFLATED}
SENSITIVE_SUFFIXES = {".bat", ".cmd", ".dll", ".exe", ".js", ".node", ".ps1", ".sh"}
EOCD_SIGNATURE = b"PK\x05\x06"
EOCD_BYTES = 22
EOCD_SEARCH_BYTES = EOCD_BYTES + 65_535
DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")
WINDOWS_DEVICE = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])$", re.IGNORECASE)


class ArchiveInventoryError(ValueError):
    """Raised when ZIP metadata violates the frozen inspection contract."""


@dataclass(frozen=True, slots=True)
class ArchiveInventoryResult:
    archive_bytes: int
    sha256: str
    sha512: str
    entry_count: int
    file_count: int
    directory_count: int
    central_directory_bytes: int
    archive_comment_bytes: int
    total_compressed_bytes: int
    total_uncompressed_bytes: int
    maximum_entry_uncompressed_bytes: int
    maximum_compression_ratio_milli: int
    compression_methods: tuple[int, ...]
    top_level_components: tuple[str, ...]
    sensitive_suffix_counts: tuple[tuple[str, int], ...]
    sensitive_paths_sha256: str
    canonical_inventory_sha256: str
    member_content_read_count: int
    extraction_count: int

    def to_record(self) -> dict:
        record = asdict(self)
        record["compression_methods"] = list(self.compression_methods)
        record["top_level_components"] = list(self.top_level_components)
        record["sensitive_suffix_counts"] = [
            {"suffix": suffix, "count": count}
            for suffix, count in self.sensitive_suffix_counts
        ]
        return record


@dataclass(frozen=True, slots=True)
class _Eocd:
    entries: int
    central_directory_bytes: int
    central_directory_offset: int
    comment_bytes: int
    absolute_offset: int


def _hash_stream(source: BinaryIO) -> tuple[int, str, str]:
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    total = 0
    source.seek(0)
    while chunk := source.read(8 * 1024 * 1024):
        if not isinstance(chunk, bytes):
            raise ArchiveInventoryError("archive_chunk_not_bytes")
        total += len(chunk)
        sha256.update(chunk)
        sha512.update(chunk)
    return total, sha256.hexdigest(), sha512.hexdigest()


def _read_eocd(source: BinaryIO, archive_bytes: int) -> _Eocd:
    tail_bytes = min(archive_bytes, EOCD_SEARCH_BYTES)
    source.seek(archive_bytes - tail_bytes)
    tail = source.read(tail_bytes)
    position = tail.rfind(EOCD_SIGNATURE)
    if position < 0 or position + EOCD_BYTES > len(tail):
        raise ArchiveInventoryError("zip_eocd_missing")
    (
        signature,
        disk_number,
        central_directory_disk,
        entries_on_disk,
        total_entries,
        central_directory_bytes,
        central_directory_offset,
        comment_bytes,
    ) = struct.unpack_from("<4s4H2LH", tail, position)
    if signature != EOCD_SIGNATURE:
        raise ArchiveInventoryError("zip_eocd_signature_invalid")
    if position + EOCD_BYTES + comment_bytes != len(tail):
        raise ArchiveInventoryError("zip_trailing_or_comment_length_invalid")
    if (
        entries_on_disk == 0xFFFF
        or total_entries == 0xFFFF
        or central_directory_bytes == 0xFFFFFFFF
        or central_directory_offset == 0xFFFFFFFF
    ):
        raise ArchiveInventoryError("zip64_rejected")
    if disk_number != 0 or central_directory_disk != 0 or entries_on_disk != total_entries:
        raise ArchiveInventoryError("multi_disk_zip_rejected")
    if total_entries > MAXIMUM_ENTRIES:
        raise ArchiveInventoryError("entry_count_ceiling_exceeded")
    if central_directory_bytes > MAXIMUM_CENTRAL_DIRECTORY_BYTES:
        raise ArchiveInventoryError("central_directory_ceiling_exceeded")
    absolute_offset = archive_bytes - tail_bytes + position
    if central_directory_offset + central_directory_bytes > absolute_offset:
        raise ArchiveInventoryError("central_directory_bounds_invalid")
    return _Eocd(
        entries=total_entries,
        central_directory_bytes=central_directory_bytes,
        central_directory_offset=central_directory_offset,
        comment_bytes=comment_bytes,
        absolute_offset=absolute_offset,
    )


def _safe_path(raw_name: str, is_directory: bool) -> tuple[str, tuple[str, ...]]:
    if not raw_name or "\x00" in raw_name:
        raise ArchiveInventoryError("member_name_empty_or_nul")
    if unicodedata.normalize("NFC", raw_name) != raw_name:
        raise ArchiveInventoryError("member_name_not_nfc")
    if len(raw_name) > MAXIMUM_PATH_CHARACTERS:
        raise ArchiveInventoryError("member_path_too_long")
    if "\\" in raw_name:
        raise ArchiveInventoryError("member_backslash_rejected")
    if raw_name.startswith("/") or DRIVE_PREFIX.match(raw_name):
        raise ArchiveInventoryError("member_absolute_path_rejected")
    if is_directory != raw_name.endswith("/"):
        raise ArchiveInventoryError("directory_marker_mismatch")
    body = raw_name[:-1] if is_directory else raw_name
    if not body:
        raise ArchiveInventoryError("member_root_entry_rejected")
    parts = tuple(body.split("/"))
    for part in parts:
        if not part or part in {".", ".."}:
            raise ArchiveInventoryError("member_traversal_segment_rejected")
        if part.endswith((" ", ".")):
            raise ArchiveInventoryError("member_windows_trailing_character_rejected")
        if ":" in part or any(ord(character) < 32 for character in part):
            raise ArchiveInventoryError("member_windows_unsafe_character_rejected")
        device_stem = part.split(".", 1)[0]
        if WINDOWS_DEVICE.fullmatch(device_stem):
            raise ArchiveInventoryError("member_windows_device_name_rejected")
    return body, parts


def _entry_kind(external_attr: int, is_directory: bool) -> str:
    mode = external_attr >> 16
    file_type = stat.S_IFMT(mode)
    if file_type == stat.S_IFLNK:
        raise ArchiveInventoryError("symlink_member_rejected")
    if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
        raise ArchiveInventoryError("special_member_rejected")
    if is_directory and file_type == stat.S_IFREG:
        raise ArchiveInventoryError("directory_mode_mismatch")
    if not is_directory and file_type == stat.S_IFDIR:
        raise ArchiveInventoryError("file_mode_mismatch")
    return "directory" if is_directory else "file"


def inspect_archive(
    archive_path: Path,
    *,
    expected_bytes: int,
    expected_sha256: str,
    expected_sha512: str,
) -> ArchiveInventoryResult:
    """Read archive identity and central-directory metadata only."""

    if not isinstance(archive_path, Path) or not archive_path.is_absolute():
        raise ArchiveInventoryError("archive_path_must_be_absolute")
    if not archive_path.is_file() or archive_path.is_symlink():
        raise ArchiveInventoryError("archive_file_missing_or_symlink")
    before = archive_path.stat()
    if before.st_size != expected_bytes:
        raise ArchiveInventoryError("archive_size_mismatch")

    try:
        with archive_path.open("rb") as source:
            actual_bytes, sha256, sha512 = _hash_stream(source)
            if actual_bytes != expected_bytes or sha256 != expected_sha256 or sha512 != expected_sha512:
                raise ArchiveInventoryError("archive_identity_mismatch")
            eocd = _read_eocd(source, actual_bytes)
            source.seek(0)
            with ZipFile(source, mode="r", allowZip64=False) as archive:
                entries = archive.infolist()
    except ArchiveInventoryError:
        raise
    except (BadZipFile, OSError, RuntimeError, NotImplementedError) as error:
        raise ArchiveInventoryError("zip_metadata_read_failed") from error

    after = archive_path.stat()
    if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
        raise ArchiveInventoryError("archive_changed_during_inventory")
    if len(entries) != eocd.entries:
        raise ArchiveInventoryError("central_directory_entry_count_mismatch")

    names: set[str] = set()
    canonical_entries: list[dict] = []
    sensitive_paths: list[str] = []
    suffix_counts: dict[str, int] = {}
    top_levels: set[str] = set()
    methods: set[int] = set()
    files = 0
    directories = 0
    total_compressed = 0
    total_uncompressed = 0
    maximum_entry = 0
    maximum_ratio_milli = 0

    for info in entries:
        raw_name = info.orig_filename
        is_directory = info.is_dir()
        safe_name, parts = _safe_path(raw_name, is_directory)
        collision_key = unicodedata.normalize("NFC", safe_name).casefold()
        if collision_key in names:
            raise ArchiveInventoryError("duplicate_or_case_colliding_member_rejected")
        names.add(collision_key)
        kind = _entry_kind(info.external_attr, is_directory)
        if info.flag_bits & 0x01:
            raise ArchiveInventoryError("encrypted_member_rejected")
        if info.flag_bits & ((1 << 5) | (1 << 6)):
            raise ArchiveInventoryError("unsupported_member_flag_rejected")
        if info.compress_type not in ALLOWED_COMPRESSION_METHODS:
            raise ArchiveInventoryError("compression_method_rejected")
        if info.file_size > MAXIMUM_ENTRY_UNCOMPRESSED_BYTES:
            raise ArchiveInventoryError("entry_uncompressed_ceiling_exceeded")
        if is_directory and info.file_size != 0:
            raise ArchiveInventoryError("directory_payload_rejected")
        if info.file_size > 0 and info.compress_size == 0:
            raise ArchiveInventoryError("zero_compressed_nonempty_member_rejected")
        ratio_milli = (
            0 if info.file_size == 0 else (info.file_size * 1000) // info.compress_size
        )
        if ratio_milli > MAXIMUM_COMPRESSION_RATIO_MILLI:
            raise ArchiveInventoryError("compression_ratio_ceiling_exceeded")

        total_compressed += info.compress_size
        total_uncompressed += info.file_size
        if total_uncompressed > MAXIMUM_TOTAL_UNCOMPRESSED_BYTES:
            raise ArchiveInventoryError("total_uncompressed_ceiling_exceeded")
        maximum_entry = max(maximum_entry, info.file_size)
        maximum_ratio_milli = max(maximum_ratio_milli, ratio_milli)
        methods.add(info.compress_type)
        top_levels.add(parts[0])
        if kind == "directory":
            directories += 1
        else:
            files += 1
            suffix = Path(safe_name).suffix.casefold()
            if suffix in SENSITIVE_SUFFIXES:
                suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
                sensitive_paths.append(safe_name)
        canonical_entries.append(
            {
                "path": safe_name,
                "kind": kind,
                "compressed_bytes": info.compress_size,
                "uncompressed_bytes": info.file_size,
                "crc32": f"{info.CRC:08x}",
                "compression_method": info.compress_type,
                "external_attr": info.external_attr,
                "flag_bits": info.flag_bits,
            }
        )

    canonical_entries.sort(key=lambda item: item["path"].encode("utf-8"))
    encoded = json.dumps(
        canonical_entries, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    sensitive_encoded = "\n".join(
        sorted(sensitive_paths, key=lambda item: item.encode("utf-8"))
    ).encode("utf-8")
    return ArchiveInventoryResult(
        archive_bytes=actual_bytes,
        sha256=sha256,
        sha512=sha512,
        entry_count=len(entries),
        file_count=files,
        directory_count=directories,
        central_directory_bytes=eocd.central_directory_bytes,
        archive_comment_bytes=eocd.comment_bytes,
        total_compressed_bytes=total_compressed,
        total_uncompressed_bytes=total_uncompressed,
        maximum_entry_uncompressed_bytes=maximum_entry,
        maximum_compression_ratio_milli=maximum_ratio_milli,
        compression_methods=tuple(sorted(methods)),
        top_level_components=tuple(
            sorted(top_levels, key=lambda item: item.encode("utf-8"))
        ),
        sensitive_suffix_counts=tuple(sorted(suffix_counts.items())),
        sensitive_paths_sha256=hashlib.sha256(sensitive_encoded).hexdigest(),
        canonical_inventory_sha256=hashlib.sha256(encoded).hexdigest(),
        member_content_read_count=0,
        extraction_count=0,
    )


def inspect_exact_archive(repository_root: Path) -> ArchiveInventoryResult:
    """Inspect only the acquired archive at its frozen ignored path."""

    if not isinstance(repository_root, Path) or not repository_root.is_absolute():
        raise ArchiveInventoryError("repository_root_must_be_absolute")
    archive_path = repository_root / ARCHIVE_RELATIVE
    return inspect_archive(
        archive_path,
        expected_bytes=EXPECTED_BYTES,
        expected_sha256=EXPECTED_SHA256,
        expected_sha512=EXPECTED_SHA512,
    )
