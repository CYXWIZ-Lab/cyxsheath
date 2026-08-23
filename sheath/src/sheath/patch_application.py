"""Fail-closed application of canonical patches to fresh workspace snapshots."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import uuid

from .artifacts import ArtifactError, ArtifactStore, StoredArtifact
from .patches import PatchError, _decode_record
from .snapshots import (
    WorkspaceSnapshot,
    _WorkspaceEntry,
    _workspace_entries,
    directory_digest,
)


def _metadata(entry: _WorkspaceEntry) -> dict[str, object]:
    record: dict[str, object] = {"kind": entry.kind}
    if entry.kind == "file":
        record["digest"] = entry.digest
        record["size_bytes"] = entry.size_bytes
    elif entry.kind == "symlink":
        record["target"] = entry.target
    return record


def _after_metadata(entry: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in entry.items() if key != "content_base64"}


def _target(root: Path, relative: str) -> Path:
    return root.joinpath(*PurePosixPath(relative).parts)


def _validate_transition(
    snapshot: WorkspaceSnapshot,
    record: dict[str, object],
) -> None:
    current = {
        entry.path: _metadata(entry) for entry in _workspace_entries(snapshot.root)
    }
    final = dict(current)
    changes = record["changes"]
    assert isinstance(changes, list)
    for change in changes:
        assert isinstance(change, dict)
        path = change["path"]
        assert isinstance(path, str)
        if current.get(path) != change["before"]:
            raise PatchError(f"snapshot entry does not match patch before state: {path}")
        after = change["after"]
        if after is None:
            final.pop(path, None)
        else:
            assert isinstance(after, dict)
            final[path] = _after_metadata(after)

    for path in final:
        parts = PurePosixPath(path).parts
        for depth in range(1, len(parts)):
            parent = PurePosixPath(*parts[:depth]).as_posix()
            if final.get(parent) != {"kind": "directory"}:
                raise PatchError(f"patch result has a non-directory parent: {path}")


def _remove_changed_paths(root: Path, changes: list[dict[str, object]]) -> None:
    removals = [change for change in changes if change["before"] is not None]
    removals.sort(
        key=lambda change: len(PurePosixPath(str(change["path"])).parts),
        reverse=True,
    )
    for change in removals:
        path = _target(root, str(change["path"]))
        before = change["before"]
        assert isinstance(before, dict)
        if before["kind"] == "directory":
            path.rmdir()
        else:
            path.unlink()


def _create_changed_paths(root: Path, changes: list[dict[str, object]]) -> None:
    additions = [change for change in changes if change["after"] is not None]
    additions.sort(key=lambda change: len(PurePosixPath(str(change["path"])).parts))
    for change in additions:
        path = _target(root, str(change["path"]))
        after = change["after"]
        assert isinstance(after, dict)
        if after["kind"] == "directory":
            path.mkdir()
        elif after["kind"] == "symlink":
            os.symlink(str(after["target"]), path)
        else:
            content = base64.b64decode(str(after["content_base64"]), validate=True)
            temporary = path.parent / f".sheath-patch-{uuid.uuid4().hex}.tmp"
            try:
                temporary.write_bytes(content)
                os.replace(temporary, path)
            finally:
                if temporary.exists():
                    temporary.unlink()


@dataclass(frozen=True, slots=True)
class PatchApplication:
    patch_artifact_id: str
    source_digest: str
    result_digest: str
    changed_paths: tuple[str, ...]


class PatchApplier:
    """Applies one verified artifact and discards the snapshot on any failure."""

    def __init__(self, max_patch_bytes: int = 4_194_304) -> None:
        if (
            isinstance(max_patch_bytes, bool)
            or not isinstance(max_patch_bytes, int)
            or max_patch_bytes < 1
        ):
            raise PatchError("max_patch_bytes must be a positive integer")
        self._maximum = max_patch_bytes

    def apply(
        self,
        snapshot: WorkspaceSnapshot,
        patch: StoredArtifact,
        store: ArtifactStore,
    ) -> PatchApplication:
        if not isinstance(snapshot, WorkspaceSnapshot) or snapshot.closed:
            raise PatchError("an active WorkspaceSnapshot is required")
        try:
            if not isinstance(patch, StoredArtifact) or patch.kind != "patch":
                raise PatchError("patch must be a stored patch artifact")
            if not isinstance(store, ArtifactStore):
                raise PatchError("store must be an ArtifactStore")
            store.verify(patch)
            if patch.size_bytes > self._maximum:
                raise PatchError("canonical patch exceeds the patch byte limit")
            encoded = (store.root / patch.path).read_bytes()
            record, paths = _decode_record(encoded, snapshot.source_digest)
            if directory_digest(snapshot.source_root) != snapshot.source_digest:
                raise PatchError("source no longer matches the staged revision")
            if directory_digest(snapshot.root) != snapshot.source_digest:
                raise PatchError("patch application requires a fresh snapshot")
            _validate_transition(snapshot, record)
            changes = record["changes"]
            assert isinstance(changes, list)
            _remove_changed_paths(snapshot.root, changes)
            _create_changed_paths(snapshot.root, changes)
            result_digest = directory_digest(snapshot.root)
            if result_digest != record["result_digest"]:
                raise PatchError("applied tree does not match patch result_digest")
            if directory_digest(snapshot.source_root) != snapshot.source_digest:
                raise PatchError("source changed during patch application")
        except (ArtifactError, OSError, PatchError, ValueError) as error:
            snapshot.close()
            if isinstance(error, PatchError):
                raise
            raise PatchError("patch application failed") from error
        return PatchApplication(
            patch.id,
            record["source_digest"],
            record["result_digest"],
            paths,
        )
