"""Admit and aggregate Authenticode review outcomes without owning a tool."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import unicodedata

try:
    from .llmster_archive_staging import (
        CHUNK_BYTES,
        MARKER_NAME,
        SIGNATURE_SUFFIXES,
        StagingError,
        _verify_owned_root,
    )
except ImportError:
    from llmster_archive_staging import (
        CHUNK_BYTES,
        MARKER_NAME,
        SIGNATURE_SUFFIXES,
        StagingError,
        _verify_owned_root,
    )


SIGNATURE_STATUS_OUTCOMES = {
    "Valid": "signed_valid",
    "NotSigned": "unsigned",
    "HashMismatch": "invalid",
    "UnknownError": "invalid",
    "NotTrusted": "untrusted",
    "NotSupportedFileFormat": "unsupported",
    "Incompatible": "incompatible",
}
OUTCOMES = (
    "signed_valid",
    "unsigned",
    "invalid",
    "untrusted",
    "unsupported",
    "incompatible",
    "unknown",
    "timeout",
    "tool_error",
)


class AuthenticodeReviewError(ValueError):
    """Raised when review cannot preserve its frozen admission contract."""


@dataclass(frozen=True, slots=True)
class InspectionObservation:
    kind: str
    signature_status: str | None = None

    @classmethod
    def status(cls, signature_status: str) -> "InspectionObservation":
        return cls(kind="status", signature_status=signature_status)

    @classmethod
    def timeout(cls) -> "InspectionObservation":
        return cls(kind="timeout")

    @classmethod
    def tool_error(cls) -> "InspectionObservation":
        return cls(kind="tool_error")


@dataclass(frozen=True, slots=True)
class ReviewExpectations:
    expected_parent: Path
    token: str
    archive_sha256: str
    payload_file_count: int
    payload_bytes: int
    content_manifest_sha256: str
    candidate_count: int
    candidate_paths_sha256: str


@dataclass(frozen=True, slots=True)
class AuthenticodeReviewResult:
    payload_file_count: int
    payload_bytes: int
    content_manifest_sha256: str
    candidate_count: int
    candidate_paths_sha256: str
    outcome_counts: tuple[tuple[str, int], ...]
    classification_manifest_sha256: str
    inspector_call_count: int

    def to_record(self) -> dict[str, int | str | dict[str, int]]:
        return {
            "payload_file_count": self.payload_file_count,
            "payload_bytes": self.payload_bytes,
            "content_manifest_sha256": self.content_manifest_sha256,
            "candidate_count": self.candidate_count,
            "candidate_paths_sha256": self.candidate_paths_sha256,
            "outcome_counts": dict(self.outcome_counts),
            "classification_manifest_sha256": self.classification_manifest_sha256,
            "inspector_call_count": self.inspector_call_count,
        }


@dataclass(frozen=True, slots=True)
class _PayloadFile:
    path: Path
    relative_path: str
    bytes: int
    sha256: str
    identity: tuple[int, int, int, int]


def _expect(condition: bool, code: str) -> None:
    if not condition:
        raise AuthenticodeReviewError(code)


def _identity(path: Path) -> tuple[int, int, int, int]:
    try:
        item = path.stat(follow_symlinks=False)
    except OSError as error:
        raise AuthenticodeReviewError("payload_stat_failed") from error
    return (int(item.st_dev), int(item.st_ino), int(item.st_size), int(item.st_mtime_ns))


def _is_link_like(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction is not None and is_junction())


def _relative_path(root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise AuthenticodeReviewError("payload_path_escaped_root") from error
    _expect(relative.parts and all(part not in ("", ".", "..") for part in relative.parts), "payload_path_invalid")
    _expect(all(unicodedata.normalize("NFC", part) == part for part in relative.parts), "payload_path_not_nfc")
    canonical = relative.as_posix()
    _expect("\\" not in canonical, "payload_path_not_canonical")
    return canonical


def _hash_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("rb") as source:
            while chunk := source.read(CHUNK_BYTES):
                digest.update(chunk)
                total += len(chunk)
    except OSError as error:
        raise AuthenticodeReviewError("payload_read_failed") from error
    return total, digest.hexdigest()


def _walk_payload(root: Path) -> list[_PayloadFile]:
    found: list[_PayloadFile] = []
    casefolded: set[str] = set()

    def visit(directory: Path) -> None:
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda item: item.name.encode("utf-8"))
        except OSError as error:
            raise AuthenticodeReviewError("payload_enumeration_failed") from error
        for entry in entries:
            path = Path(entry.path)
            if path == root / MARKER_NAME:
                _expect(entry.is_file(follow_symlinks=False) and not _is_link_like(path), "ownership_marker_not_regular")
                continue
            _expect(not _is_link_like(path), "link_or_junction_rejected")
            if entry.is_dir(follow_symlinks=False):
                visit(path)
                continue
            _expect(entry.is_file(follow_symlinks=False), "special_payload_rejected")
            relative = _relative_path(root, path)
            folded = relative.casefold()
            _expect(folded not in casefolded, "casefold_path_collision")
            casefolded.add(folded)
            identity_before = _identity(path)
            size, digest = _hash_file(path)
            identity_after = _identity(path)
            _expect(identity_before == identity_after and size == identity_after[2], "payload_changed_during_manifest")
            found.append(_PayloadFile(path, relative, size, digest, identity_after))

    visit(root)
    found.sort(key=lambda item: item.relative_path.encode("utf-8"))
    return found


def _manifest_digest(files: list[_PayloadFile]) -> str:
    rows = [{"path": item.relative_path, "bytes": item.bytes, "sha256": item.sha256} for item in files]
    encoded = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_observation(observation: InspectionObservation) -> str:
    _expect(isinstance(observation, InspectionObservation), "inspector_observation_invalid")
    if observation.kind == "status":
        _expect(isinstance(observation.signature_status, str) and bool(observation.signature_status), "signature_status_invalid")
        return SIGNATURE_STATUS_OUTCOMES.get(observation.signature_status, "unknown")
    if observation.kind in ("timeout", "tool_error"):
        _expect(observation.signature_status is None, "operational_outcome_has_status")
        return observation.kind
    raise AuthenticodeReviewError("inspector_observation_kind_invalid")


def review_staged_candidates(
    root: Path,
    *,
    expectations: ReviewExpectations,
    inspector: Callable[[Path], InspectionObservation],
) -> AuthenticodeReviewResult:
    """Review one admitted tree through an injected non-executing inspector."""

    _expect(isinstance(root, Path) and root.is_absolute(), "owned_root_must_be_absolute")
    _expect(isinstance(expectations, ReviewExpectations), "expectations_invalid")
    _expect(callable(inspector), "inspector_not_callable")
    for name, value in (
        ("payload_file_count", expectations.payload_file_count),
        ("payload_bytes", expectations.payload_bytes),
        ("candidate_count", expectations.candidate_count),
    ):
        _expect(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"{name}_invalid")
    for name, value in (
        ("content_manifest_sha256", expectations.content_manifest_sha256),
        ("candidate_paths_sha256", expectations.candidate_paths_sha256),
        ("archive_sha256", expectations.archive_sha256),
    ):
        _expect(isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value), f"{name}_invalid")

    try:
        _verify_owned_root(root, expectations.expected_parent, expectations.token, expectations.archive_sha256)
    except StagingError as error:
        raise AuthenticodeReviewError("owned_staging_rejected") from error

    files = _walk_payload(root)
    payload_bytes = sum(item.bytes for item in files)
    manifest_sha256 = _manifest_digest(files)
    _expect(len(files) == expectations.payload_file_count, "payload_file_count_mismatch")
    _expect(payload_bytes == expectations.payload_bytes, "payload_bytes_mismatch")
    _expect(manifest_sha256 == expectations.content_manifest_sha256, "content_manifest_mismatch")

    candidates = [item for item in files if Path(item.relative_path).suffix.casefold() in SIGNATURE_SUFFIXES]
    candidate_bytes = "\n".join(item.relative_path for item in candidates).encode("utf-8")
    candidate_paths_sha256 = hashlib.sha256(candidate_bytes).hexdigest()
    _expect(len(candidates) == expectations.candidate_count, "candidate_count_mismatch")
    _expect(candidate_paths_sha256 == expectations.candidate_paths_sha256, "candidate_paths_digest_mismatch")

    counts = {outcome: 0 for outcome in OUTCOMES}
    classification_rows: list[dict[str, str]] = []
    for candidate in candidates:
        _expect(_identity(candidate.path) == candidate.identity, "candidate_changed_before_inspection")
        observation = inspector(candidate.path)
        _expect(_identity(candidate.path) == candidate.identity, "candidate_changed_during_inspection")
        outcome = normalize_observation(observation)
        counts[outcome] += 1
        classification_rows.append({"path": candidate.relative_path, "outcome": outcome})

    try:
        _verify_owned_root(root, expectations.expected_parent, expectations.token, expectations.archive_sha256)
    except StagingError as error:
        raise AuthenticodeReviewError("owned_staging_changed_during_inspection") from error
    _expect(sum(counts.values()) == len(candidates), "outcome_count_mismatch")
    classification_bytes = json.dumps(classification_rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return AuthenticodeReviewResult(
        payload_file_count=len(files),
        payload_bytes=payload_bytes,
        content_manifest_sha256=manifest_sha256,
        candidate_count=len(candidates),
        candidate_paths_sha256=candidate_paths_sha256,
        outcome_counts=tuple((outcome, counts[outcome]) for outcome in OUTCOMES),
        classification_manifest_sha256=hashlib.sha256(classification_bytes).hexdigest(),
        inspector_call_count=len(candidates),
    )
