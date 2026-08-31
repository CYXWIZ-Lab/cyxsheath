"""Extract a verified ZIP into one marker-owned staging directory."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Callable
from zipfile import ZipFile

try:
    from .llmster_archive_inventory import (
        ArchiveInventoryError,
        canonicalize_member_path,
        inspect_archive,
        validate_member_kind,
    )
except ImportError:
    from llmster_archive_inventory import (
        ArchiveInventoryError,
        canonicalize_member_path,
        inspect_archive,
        validate_member_kind,
    )


CHUNK_BYTES = 8 * 1024 * 1024
MINIMUM_FREE_BYTES_AFTER = 4 * 1024 * 1024 * 1024
MARKER_NAME = ".cyxsheath-staging-owner.json"
STAGING_NAME = re.compile(r"^llmster-([0-9a-f]{32})$")
SIGNATURE_SUFFIXES = {".dll", ".exe", ".node", ".ps1"}


class StagingError(ValueError):
    """Raised when staging cannot preserve the frozen ownership contract."""


@dataclass(frozen=True, slots=True)
class StagingResult:
    staging_path: Path
    entry_count: int
    file_count: int
    directory_count: int
    total_written_bytes: int
    content_manifest_sha256: str
    signature_candidate_count: int
    signature_candidate_paths_sha256: str
    existing_destination_overwrite_count: int
    binary_launch_count: int
    installer_invocation_count: int
    network_request_count: int

    def to_record(self) -> dict[str, int | str]:
        return {
            "entry_count": self.entry_count,
            "file_count": self.file_count,
            "directory_count": self.directory_count,
            "total_written_bytes": self.total_written_bytes,
            "content_manifest_sha256": self.content_manifest_sha256,
            "signature_candidate_count": self.signature_candidate_count,
            "signature_candidate_paths_sha256": self.signature_candidate_paths_sha256,
            "existing_destination_overwrite_count": self.existing_destination_overwrite_count,
            "binary_launch_count": self.binary_launch_count,
            "installer_invocation_count": self.installer_invocation_count,
            "network_request_count": self.network_request_count,
        }


def _default_free_bytes(path: Path) -> int:
    return shutil.disk_usage(path).free


def _checked_free_bytes(free_bytes: Callable[[Path], int], parent: Path) -> int:
    available = free_bytes(parent)
    if isinstance(available, bool) or not isinstance(available, int) or available < 0:
        raise StagingError("free_bytes_result_invalid")
    return available


def _file_identity(item: object) -> tuple[int, int, int, int]:
    return (
        int(getattr(item, "st_dev")),
        int(getattr(item, "st_ino")),
        int(getattr(item, "st_size")),
        int(getattr(item, "st_mtime_ns")),
    )


def _marker_payload(token: str, archive_sha256: str) -> dict[str, str]:
    return {
        "schema_version": "1.0.0",
        "owner": "cyxsheath-llmster-staging",
        "token": token,
        "archive_sha256": archive_sha256,
    }


def _validate_parent_and_name(parent: Path, staging_name: str) -> tuple[Path, str]:
    if not isinstance(parent, Path) or not parent.is_absolute():
        raise StagingError("staging_parent_must_be_absolute")
    if not parent.is_dir() or parent.is_symlink():
        raise StagingError("staging_parent_missing_or_symlink")
    match = STAGING_NAME.fullmatch(staging_name)
    if match is None:
        raise StagingError("staging_name_invalid")
    return parent.resolve(strict=True), match.group(1)


def _write_marker(root: Path, token: str, archive_sha256: str) -> None:
    marker = root / MARKER_NAME
    with marker.open("x", encoding="utf-8", newline="\n") as target:
        json.dump(
            _marker_payload(token, archive_sha256),
            target,
            sort_keys=True,
            separators=(",", ":"),
        )
        target.write("\n")


def _verify_owned_root(
    root: Path, expected_parent: Path, token: str, archive_sha256: str
) -> None:
    parent, parsed_token = _validate_parent_and_name(expected_parent, root.name)
    if parsed_token != token or root.parent.resolve(strict=True) != parent:
        raise StagingError("staging_ownership_scope_mismatch")
    if not root.is_dir() or root.is_symlink():
        raise StagingError("owned_staging_missing_or_symlink")
    marker = root / MARKER_NAME
    try:
        actual = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StagingError("ownership_marker_missing_or_invalid") from error
    if actual != _marker_payload(token, archive_sha256):
        raise StagingError("ownership_marker_mismatch")


def remove_owned_staging(
    root: Path, *, expected_parent: Path, token: str, archive_sha256: str
) -> None:
    """Remove only a marker-verified staging child."""

    _verify_owned_root(root, expected_parent, token, archive_sha256)
    try:
        shutil.rmtree(root)
    except OSError as error:
        raise StagingError("owned_staging_cleanup_failed") from error


def _safe_destination(root: Path, parts: tuple[str, ...]) -> Path:
    destination = root.joinpath(*parts)
    resolved = destination.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise StagingError("canonical_destination_escaped_staging")
    return destination


def _cleanup_after_failure(
    root: Path,
    *,
    parent: Path,
    token: str,
    archive_sha256: str,
    original: BaseException,
) -> None:
    try:
        remove_owned_staging(
            root,
            expected_parent=parent,
            token=token,
            archive_sha256=archive_sha256,
        )
    except StagingError as cleanup_error:
        raise StagingError("staging_failed_and_cleanup_failed") from cleanup_error
    if isinstance(original, StagingError):
        raise original
    raise StagingError("staging_member_write_failed") from original


def stage_archive(
    archive_path: Path,
    *,
    staging_parent: Path,
    staging_name: str,
    expected_bytes: int,
    expected_sha256: str,
    expected_sha512: str,
    expected_inventory_sha256: str,
    expected_total_uncompressed_bytes: int,
    minimum_free_bytes_after: int = MINIMUM_FREE_BYTES_AFTER,
    free_bytes: Callable[[Path], int] = _default_free_bytes,
) -> StagingResult:
    """Verify and stream one archive into a new marker-owned child."""

    parent, token = _validate_parent_and_name(staging_parent, staging_name)
    if not isinstance(archive_path, Path) or not archive_path.is_absolute():
        raise StagingError("archive_path_must_be_absolute")
    if archive_path.resolve(strict=False).is_relative_to(parent):
        raise StagingError("archive_must_be_outside_staging_parent")
    root = parent / staging_name
    if root.exists() or root.is_symlink():
        raise StagingError("staging_child_already_exists")
    if minimum_free_bytes_after != MINIMUM_FREE_BYTES_AFTER:
        raise StagingError("minimum_free_bytes_after_policy_drift")

    try:
        identity_before_inventory = archive_path.stat()
        inventory = inspect_archive(
            archive_path,
            expected_bytes=expected_bytes,
            expected_sha256=expected_sha256,
            expected_sha512=expected_sha512,
        )
    except ArchiveInventoryError as error:
        raise StagingError("archive_inventory_rejected") from error
    except OSError as error:
        raise StagingError("archive_unavailable_before_inventory") from error
    if inventory.canonical_inventory_sha256 != expected_inventory_sha256:
        raise StagingError("inventory_digest_mismatch")
    if inventory.total_uncompressed_bytes != expected_total_uncompressed_bytes:
        raise StagingError("inventory_uncompressed_total_mismatch")
    try:
        source_identity = archive_path.stat()
    except OSError as error:
        raise StagingError("archive_unavailable_after_inventory") from error
    if archive_path.is_symlink() or _file_identity(source_identity) != _file_identity(
        identity_before_inventory
    ):
        raise StagingError("archive_changed_after_inventory")
    required_before = expected_total_uncompressed_bytes + minimum_free_bytes_after
    if _checked_free_bytes(free_bytes, parent) < required_before:
        raise StagingError("preflight_storage_reserve_failed")

    try:
        root.mkdir()
    except OSError as error:
        raise StagingError("staging_child_creation_failed") from error
    marker_created = False
    try:
        _write_marker(root, token, expected_sha256)
        marker_created = True
        manifest: list[dict[str, int | str]] = []
        signature_candidates: list[str] = []
        total_written = 0
        files = 0
        directories = 0
        with ZipFile(archive_path, mode="r", allowZip64=False) as archive:
            for info in archive.infolist():
                is_directory = info.is_dir()
                canonical_name, parts = canonicalize_member_path(
                    info.orig_filename, is_directory
                )
                kind = validate_member_kind(info.external_attr, is_directory)
                destination = _safe_destination(root, parts)
                if kind == "directory":
                    if destination.is_symlink() or (
                        destination.exists() and not destination.is_dir()
                    ):
                        raise StagingError("existing_destination_rejected")
                    destination.mkdir(parents=True, exist_ok=True)
                    directories += 1
                    continue
                if destination.exists() or destination.is_symlink():
                    raise StagingError("existing_destination_rejected")
                destination.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                written = 0
                with archive.open(info, mode="r") as source, destination.open("xb") as target:
                    while chunk := source.read(CHUNK_BYTES):
                        target.write(chunk)
                        digest.update(chunk)
                        written += len(chunk)
                if written != info.file_size:
                    raise StagingError("written_file_size_mismatch")
                files += 1
                total_written += written
                manifest.append(
                    {"path": canonical_name, "bytes": written, "sha256": digest.hexdigest()}
                )
                if Path(canonical_name).suffix.casefold() in SIGNATURE_SUFFIXES:
                    signature_candidates.append(canonical_name)
        if total_written != expected_total_uncompressed_bytes:
            raise StagingError("total_written_bytes_mismatch")
        if files != inventory.file_count or directories != inventory.directory_count:
            raise StagingError("written_entry_count_mismatch")
        final_identity = archive_path.stat()
        if _file_identity(final_identity) != _file_identity(source_identity):
            raise StagingError("archive_changed_during_staging")
        if _checked_free_bytes(free_bytes, parent) < minimum_free_bytes_after:
            raise StagingError("final_storage_reserve_failed")
    except Exception as error:
        if marker_created or (root / MARKER_NAME).exists():
            _cleanup_after_failure(
                root,
                parent=parent,
                token=token,
                archive_sha256=expected_sha256,
                original=error,
            )
        try:
            root.rmdir()
        except OSError as cleanup_error:
            raise StagingError("unmarked_staging_cleanup_failed") from cleanup_error
        raise StagingError("staging_marker_creation_failed") from error

    manifest.sort(key=lambda item: str(item["path"]).encode("utf-8"))
    manifest_bytes = json.dumps(
        manifest, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    candidate_bytes = "\n".join(
        sorted(signature_candidates, key=lambda item: item.encode("utf-8"))
    ).encode("utf-8")
    return StagingResult(
        staging_path=root,
        entry_count=inventory.entry_count,
        file_count=files,
        directory_count=directories,
        total_written_bytes=total_written,
        content_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        signature_candidate_count=len(signature_candidates),
        signature_candidate_paths_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        existing_destination_overwrite_count=0,
        binary_launch_count=0,
        installer_invocation_count=0,
        network_request_count=0,
    )
