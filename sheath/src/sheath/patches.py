"""Canonical, bounded delta extraction from a disposable workspace copy."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import math
from pathlib import Path, PurePosixPath
import sys
from typing import Any

from .artifacts import ArtifactStore, StoredArtifact, digest_bytes
from .docker_backend import DockerCliBackend, _runtime_source_digest
from .ledger import EvidenceLedger
from .runner import ConstrainedRunner
from .snapshots import (
    SnapshotError,
    WorkspaceSnapshot,
    _WorkspaceEntry,
    _workspace_entries,
    directory_digest,
)
from .tools import (
    CommandAction,
    CommandPolicy,
    ExecutableIdentity,
    ToolSession,
)


class PatchError(ValueError):
    """Raised when a workspace delta cannot be extracted or validated."""


_SCHEMA_VERSION = "1.0.0"
_WORKER_VERSION = "1"
_CONTAINER_BOOTSTRAP = (
    "from sheath.patches import _container_worker_main;"
    "raise SystemExit(_container_worker_main())"
)


def _runtime_digest() -> str:
    return _runtime_source_digest(Path(__file__).resolve().parents[1])


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise PatchError(f"{field} must be a sha256 digest")
    hexadecimal = value.removeprefix("sha256:")
    if len(hexadecimal) != 64:
        raise PatchError(f"{field} must be a sha256 digest")
    try:
        int(hexadecimal, 16)
    except ValueError as error:
        raise PatchError(f"{field} must be a sha256 digest") from error
    return value


def _safe_path(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\x00" in value
        or "\\" in value
    ):
        raise PatchError("patch path must be a non-empty relative POSIX path")
    path = PurePosixPath(value)
    if (
        value == "."
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != value
    ):
        raise PatchError("patch path must be a canonical relative POSIX path")
    return value


def _metadata(entry: _WorkspaceEntry) -> dict[str, Any]:
    record: dict[str, Any] = {"kind": entry.kind}
    if entry.kind == "file":
        record["digest"] = entry.digest
        record["size_bytes"] = entry.size_bytes
    elif entry.kind == "symlink":
        record["target"] = entry.target
    return record


def _changed_file_record(root: Path, entry: _WorkspaceEntry) -> dict[str, Any]:
    record = _metadata(entry)
    path = root.joinpath(*PurePosixPath(entry.path).parts)
    try:
        content = path.read_bytes()
    except OSError as error:
        raise PatchError("changed file could not be read") from error
    if len(content) != entry.size_bytes or digest_bytes(content) != entry.digest:
        raise PatchError("changed file did not match its inventory")
    record["content_base64"] = base64.b64encode(content).decode("ascii")
    return record


def _build_patch_record(
    source_root: Path,
    result_root: Path,
    expected_source_digest: str,
    python_digest: str,
    worker_digest: str,
    max_patch_bytes: int,
) -> bytes:
    source_before = directory_digest(source_root)
    if source_before != expected_source_digest:
        raise PatchError("source no longer matches the staged revision")
    result_before = directory_digest(result_root)
    source_entries = {entry.path: entry for entry in _workspace_entries(source_root)}
    result_entries = {entry.path: entry for entry in _workspace_entries(result_root)}
    changes: list[dict[str, Any]] = []
    encoded_content_bytes = 0
    for path in sorted(source_entries.keys() | result_entries.keys()):
        before = source_entries.get(path)
        after = result_entries.get(path)
        if before == after:
            continue
        if before is None:
            operation = "add"
        elif after is None:
            operation = "delete"
        else:
            operation = "modify"
        after_record = None
        if after is not None:
            if after.kind == "file" and after.size_bytes is not None:
                if after.size_bytes > max_patch_bytes:
                    raise PatchError("changed file exceeds the patch byte limit")
                encoded_content_bytes += 4 * ((after.size_bytes + 2) // 3)
                if encoded_content_bytes > max_patch_bytes:
                    raise PatchError("changed files exceed the patch byte limit")
                after_record = _changed_file_record(result_root, after)
            else:
                after_record = _metadata(after)
        changes.append(
            {
                "after": after_record,
                "before": None if before is None else _metadata(before),
                "operation": operation,
                "path": path,
            }
        )

    source_after = directory_digest(source_root)
    result_after = directory_digest(result_root)
    if source_before != source_after:
        raise PatchError("source changed during patch extraction")
    if result_before != result_after:
        raise PatchError("snapshot changed during patch extraction")
    record = {
        "changes": changes,
        "extractor": {
            "python_digest": python_digest,
            "worker_digest": worker_digest,
            "worker_version": _WORKER_VERSION,
        },
        "result_digest": result_after,
        "schema_version": _SCHEMA_VERSION,
        "source_digest": source_after,
    }
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    if len(encoded) > max_patch_bytes:
        raise PatchError("canonical patch exceeds the patch byte limit")
    return encoded


def _container_worker_main() -> int:
    try:
        (
            source_digest,
            maximum,
            python_digest,
            worker_digest,
        ) = sys.argv[1:]
        if _runtime_digest() != worker_digest:
            raise PatchError("mounted patch runtime has another identity")
        encoded = _build_patch_record(
            Path("/source"),
            Path("/workspace"),
            source_digest,
            python_digest,
            worker_digest,
            int(maximum),
        )
        sys.stdout.buffer.write(encoded)
    except Exception as error:
        detail = str(error).replace("\r", " ").replace("\n", " ")[:200]
        sys.stderr.write(f"{type(error).__name__}: {detail}\n")
        return 1
    return 0


def _entry(record: object, *, content_required: bool) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise PatchError("patch entry must be an object")
    kind = record.get("kind")
    if kind not in {"directory", "file", "symlink"}:
        raise PatchError("patch entry has an unsupported kind")
    expected = {"kind"}
    if kind == "file":
        expected |= {"digest", "size_bytes"}
        if content_required:
            expected.add("content_base64")
        if set(record) != expected:
            raise PatchError("file patch entry has unexpected fields")
        digest = _sha256(record["digest"], "file digest")
        size = record["size_bytes"]
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise PatchError("file patch entry size is invalid")
        if content_required:
            content_value = record["content_base64"]
            if not isinstance(content_value, str):
                raise PatchError("file content must be base64 text")
            try:
                content = base64.b64decode(content_value, validate=True)
            except ValueError as error:
                raise PatchError("file content is not valid base64") from error
            if len(content) != size or digest_bytes(content) != digest:
                raise PatchError("file content does not match its metadata")
    elif kind == "symlink":
        expected.add("target")
        if set(record) != expected:
            raise PatchError("symlink patch entry has unexpected fields")
        target = record["target"]
        if not isinstance(target, str) or "\x00" in target:
            raise PatchError("symlink target is invalid")
    elif set(record) != expected:
        raise PatchError("directory patch entry has unexpected fields")
    return record


def _decode_record(
    encoded: bytes,
    source_digest: str,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    try:
        record = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PatchError("patch worker returned invalid JSON") from error
    canonical = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    if canonical != encoded or not isinstance(record, dict):
        raise PatchError("patch record is not canonically encoded")
    if set(record) != {
        "changes",
        "extractor",
        "result_digest",
        "schema_version",
        "source_digest",
    }:
        raise PatchError("patch record has unexpected fields")
    if record["schema_version"] != _SCHEMA_VERSION:
        raise PatchError("patch record uses an unsupported schema")
    if record["source_digest"] != source_digest:
        raise PatchError("patch record uses another source revision")
    _sha256(record["result_digest"], "result_digest")
    extractor = record["extractor"]
    if not isinstance(extractor, dict) or set(extractor) != {
        "python_digest",
        "worker_digest",
        "worker_version",
    }:
        raise PatchError("patch extractor identity is invalid")
    _sha256(extractor["python_digest"], "extractor python_digest")
    _sha256(extractor["worker_digest"], "extractor worker_digest")
    if extractor["worker_version"] != _WORKER_VERSION:
        raise PatchError("patch record uses an unsupported worker")
    changes = record["changes"]
    if not isinstance(changes, list):
        raise PatchError("patch changes must be an array")
    paths: list[str] = []
    for change in changes:
        if not isinstance(change, dict) or set(change) != {
            "after",
            "before",
            "operation",
            "path",
        }:
            raise PatchError("patch change has unexpected fields")
        path = _safe_path(change["path"])
        operation = change["operation"]
        before = change["before"]
        after = change["after"]
        if operation == "add" and before is None and after is not None:
            content_required = isinstance(after, dict) and after.get("kind") == "file"
            _entry(after, content_required=content_required)
        elif operation == "delete" and before is not None and after is None:
            _entry(before, content_required=False)
        elif operation == "modify" and before is not None and after is not None:
            _entry(before, content_required=False)
            content_required = isinstance(after, dict) and after.get("kind") == "file"
            _entry(after, content_required=content_required)
            if before == after:
                raise PatchError("modify change has identical entries")
        else:
            raise PatchError("patch operation and entries are inconsistent")
        paths.append(path)
    if paths != sorted(set(paths)):
        raise PatchError("patch paths must be sorted and unique")
    return record, tuple(paths)


def _validate_record(
    encoded: bytes,
    source_digest: str,
    python_digest: str,
    worker_digest: str,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    record, paths = _decode_record(encoded, source_digest)
    if record["extractor"] != {
        "python_digest": python_digest,
        "worker_digest": worker_digest,
        "worker_version": _WORKER_VERSION,
    }:
        raise PatchError("patch record uses another extractor identity")
    return record, paths


@dataclass(frozen=True, slots=True)
class PatchExtraction:
    artifact: StoredArtifact
    source_digest: str
    result_digest: str
    changed_paths: tuple[str, ...]
    observation_id: str
    evidence_ids: tuple[str, ...]
    sandbox_digest: str
    stdout_artifact_id: str
    stderr_artifact_id: str


class DockerPatchExtractor:
    """Extracts a delta through the bounded Docker observation path."""

    def __init__(
        self,
        backend: DockerCliBackend,
        executable: ExecutableIdentity,
        *,
        timeout_seconds: float = 30,
        max_patch_bytes: int = 4_194_304,
    ) -> None:
        if not isinstance(backend, DockerCliBackend):
            raise PatchError("backend must be a DockerCliBackend")
        if not isinstance(executable, ExecutableIdentity):
            raise PatchError("executable must be an ExecutableIdentity")
        if executable.scope != "container_image":
            raise PatchError("patch executable must use a container image")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise PatchError("timeout_seconds must be positive")
        if (
            isinstance(max_patch_bytes, bool)
            or not isinstance(max_patch_bytes, int)
            or max_patch_bytes < 1
        ):
            raise PatchError("max_patch_bytes must be a positive integer")
        self._timeout = float(timeout_seconds)
        self._maximum = max_patch_bytes
        self._backend = backend
        self._executable = executable
        self._worker_digest = _runtime_digest()
        runtime_root = Path(__file__).resolve().parents[1]
        if backend.config.patch_runtime_root != runtime_root:
            raise PatchError("Docker backend does not mount the trusted patch runtime")
        if not backend.config.workspace.writable:
            raise PatchError("Docker patch extraction requires a writable snapshot")

    def extract(
        self,
        snapshot: WorkspaceSnapshot,
        store: ArtifactStore,
    ) -> PatchExtraction:
        if not isinstance(snapshot, WorkspaceSnapshot) or snapshot.closed:
            raise PatchError("an active WorkspaceSnapshot is required")
        if not isinstance(store, ArtifactStore):
            raise PatchError("store must be an ArtifactStore")
        if self._backend.config.workspace != snapshot.binding:
            raise PatchError("Docker backend uses another workspace snapshot")
        ledger = EvidenceLedger(snapshot.source_digest)
        policy = CommandPolicy(
            snapshot.root,
            (self._executable,),
            max_timeout_seconds=self._timeout,
            max_output_bytes=self._maximum,
        )
        session = ToolSession(policy, ledger, store)
        outcome = ConstrainedRunner(session, self._backend).execute(
            CommandAction(
                "action-patch-extract",
                (
                    self._executable.name,
                    "-c",
                    _CONTAINER_BOOTSTRAP,
                    snapshot.source_digest,
                    str(self._maximum),
                    self._executable.digest,
                    self._worker_digest,
                ),
                ".",
                self._timeout,
                self._maximum,
            ),
            ("patch.canonical",),
        )
        observation = outcome.observation
        if observation is None or not outcome.evidence or not outcome.evidence[0].passed:
            detail = ""
            if observation is not None:
                stderr = store.get(observation.stderr_artifact_id)
                detail = (store.root / stderr.path).read_bytes()[:256].decode(
                    "utf-8",
                    errors="replace",
                ).strip()
            raise PatchError(f"sandboxed patch extractor failed: {detail}")
        stdout = store.get(observation.stdout_artifact_id)
        encoded = (store.root / stdout.path).read_bytes()
        record, paths = _validate_record(
            encoded,
            snapshot.source_digest,
            self._executable.digest,
            self._worker_digest,
        )
        artifact = store.store_bytes("patch", encoded)
        return PatchExtraction(
            artifact,
            record["source_digest"],
            record["result_digest"],
            paths,
            observation.id,
            tuple(item.id for item in outcome.evidence),
            observation.sandbox_digest,
            observation.stdout_artifact_id,
            observation.stderr_artifact_id,
        )
