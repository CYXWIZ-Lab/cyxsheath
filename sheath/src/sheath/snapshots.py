"""Verified, disposable workspace copies for isolated tool execution."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
from types import TracebackType
import uuid


class SnapshotError(ValueError):
    """Raised when workspace staging or cleanup violates its boundary."""


_ACCESS_MODES = {"read_only", "writable_snapshot"}


def _directory(path: Path, field: str) -> Path:
    try:
        resolved = Path(path).resolve(strict=True)
    except (OSError, TypeError) as error:
        raise SnapshotError(f"{field} must be an existing directory") from error
    if not resolved.is_dir():
        raise SnapshotError(f"{field} must be an existing directory")
    return resolved


def _sha256(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise SnapshotError(f"{field} must be a sha256 digest")
    hexadecimal = value.removeprefix("sha256:")
    if len(hexadecimal) != 64:
        raise SnapshotError(f"{field} must be a sha256 digest")
    try:
        int(hexadecimal, 16)
    except ValueError as error:
        raise SnapshotError(f"{field} must be a sha256 digest") from error


def _contains(parent: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise SnapshotError(f"cannot read workspace file: {path}") from error
    return "sha256:" + digest.hexdigest()


@dataclass(frozen=True, slots=True)
class _WorkspaceEntry:
    path: str
    kind: str
    digest: str | None = None
    size_bytes: int | None = None
    target: str | None = None

    def record(self) -> dict[str, int | str]:
        record: dict[str, int | str] = {
            "kind": self.kind,
            "path": self.path,
        }
        if self.kind == "file":
            assert self.digest is not None
            assert self.size_bytes is not None
            record["digest"] = self.digest
            record["size_bytes"] = self.size_bytes
        elif self.kind == "symlink":
            assert self.target is not None
            record["target"] = self.target
        return record


def _workspace_entries(root: Path) -> tuple[_WorkspaceEntry, ...]:
    """Inventory a tree without following symlinks or accepting special files."""

    resolved = _directory(root, "root")
    entries: list[_WorkspaceEntry] = []
    try:
        walker = os.walk(resolved, topdown=True, followlinks=False)
        for current, directories, files in walker:
            directories.sort()
            files.sort()
            current_path = Path(current)
            for name in sorted((*directories, *files)):
                path = current_path / name
                relative = path.relative_to(resolved).as_posix()
                metadata = path.lstat()
                if stat.S_ISLNK(metadata.st_mode):
                    entry = _WorkspaceEntry(
                        relative,
                        "symlink",
                        target=os.readlink(path),
                    )
                elif stat.S_ISDIR(metadata.st_mode):
                    entry = _WorkspaceEntry(relative, "directory")
                elif stat.S_ISREG(metadata.st_mode):
                    entry = _WorkspaceEntry(
                        relative,
                        "file",
                        digest=_file_digest(path),
                        size_bytes=metadata.st_size,
                    )
                else:
                    raise SnapshotError(f"unsupported workspace entry: {path}")
                entries.append(entry)
    except OSError as error:
        raise SnapshotError(f"cannot inspect workspace: {resolved}") from error
    return tuple(entries)


def _entry_digest(entries: tuple[_WorkspaceEntry, ...]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        encoded = json.dumps(
            entry.record(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        digest.update(encoded + b"\n")
    return "sha256:" + digest.hexdigest()


def directory_digest(root: Path) -> str:
    """Hash relative paths, kinds, links, and regular-file bytes."""

    return _entry_digest(_workspace_entries(root))


@dataclass(frozen=True, slots=True)
class WorkspaceBinding:
    """A validated host directory and its intended container access mode."""

    root: Path
    access: str
    source_root: Path
    source_digest: str | None

    def __post_init__(self) -> None:
        root = _directory(self.root, "root")
        source = _directory(self.source_root, "source_root")
        if self.access not in _ACCESS_MODES:
            raise SnapshotError("access must be read_only or writable_snapshot")
        if self.access == "read_only":
            if root != source or self.source_digest is not None:
                raise SnapshotError("read_only binding must refer directly to its source")
        else:
            if root == source:
                raise SnapshotError("writable snapshot must be separate from its source")
            if self.source_digest is None:
                raise SnapshotError("writable snapshot requires its source digest")
            _sha256(self.source_digest, "source_digest")
        object.__setattr__(self, "root", root)
        object.__setattr__(self, "source_root", source)

    @property
    def writable(self) -> bool:
        return self.access == "writable_snapshot"


def read_only_workspace(root: Path) -> WorkspaceBinding:
    resolved = _directory(root, "root")
    return WorkspaceBinding(resolved, "read_only", resolved, None)


class WorkspaceSnapshot:
    """Owns one staged tree until its explicit or contextual cleanup."""

    def __init__(
        self,
        source_root: Path,
        root: Path,
        staging_root: Path,
        source_digest: str,
    ) -> None:
        self._binding = WorkspaceBinding(
            root,
            "writable_snapshot",
            source_root,
            source_digest,
        )
        self._staging_root = staging_root
        self._closed = False

    @property
    def binding(self) -> WorkspaceBinding:
        if self._closed:
            raise SnapshotError("snapshot is already closed")
        return self._binding

    @property
    def root(self) -> Path:
        return self._binding.root

    @property
    def source_root(self) -> Path:
        return self._binding.source_root

    @property
    def source_digest(self) -> str:
        assert self._binding.source_digest is not None
        return self._binding.source_digest

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if self._closed:
            return
        root = self._binding.root
        if root.parent != self._staging_root or not root.name.startswith(
            "sheath-snapshot-"
        ):
            raise SnapshotError("snapshot cleanup target is invalid")
        try:
            if root.is_symlink():
                root.unlink()
            elif root.exists():
                shutil.rmtree(root)
        except OSError as error:
            raise SnapshotError(f"cannot remove snapshot: {root}") from error
        self._closed = True

    def __enter__(self) -> WorkspaceSnapshot:
        if self._closed:
            raise SnapshotError("snapshot is already closed")
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception_type, exception, traceback
        self.close()


class SnapshotStager:
    """Copies a stable source tree into a caller-owned staging directory."""

    def __init__(self, staging_root: Path) -> None:
        requested = Path(staging_root)
        try:
            requested.mkdir(exist_ok=True)
        except OSError as error:
            raise SnapshotError("cannot create staging_root") from error
        self._root = _directory(requested, "staging_root")

    @property
    def root(self) -> Path:
        return self._root

    def stage(self, source_root: Path) -> WorkspaceSnapshot:
        source = _directory(source_root, "source_root")
        if _contains(source, self._root) or _contains(self._root, source):
            raise SnapshotError("source_root and staging_root cannot overlap")

        return self._copy(source)

    def restage(self, snapshot: WorkspaceSnapshot) -> WorkspaceSnapshot:
        """Copy an active snapshot to a sibling for the next revision attempt."""

        if not isinstance(snapshot, WorkspaceSnapshot) or snapshot.closed:
            raise SnapshotError("restage requires an active WorkspaceSnapshot")
        source = snapshot.root
        if source.parent != self._root or not source.name.startswith(
            "sheath-snapshot-"
        ):
            raise SnapshotError("snapshot is not owned by this stager")
        return self._copy(source)

    def _copy(self, source: Path) -> WorkspaceSnapshot:
        before = directory_digest(source)
        target = self._root / f"sheath-snapshot-{uuid.uuid4().hex}"
        try:
            shutil.copytree(source, target, symlinks=True)
            source_after = directory_digest(source)
            copied = directory_digest(target)
        except (OSError, shutil.Error, SnapshotError) as error:
            self._discard(target)
            if isinstance(error, SnapshotError):
                raise
            raise SnapshotError("workspace copy failed") from error
        if before != source_after or before != copied:
            self._discard(target)
            raise SnapshotError("source changed while the snapshot was staged")
        return WorkspaceSnapshot(source, target, self._root, before)

    def _discard(self, target: Path) -> None:
        if target.parent != self._root or not target.name.startswith(
            "sheath-snapshot-"
        ):
            raise SnapshotError("snapshot discard target is invalid")
        try:
            if target.is_symlink():
                target.unlink()
            elif target.exists():
                shutil.rmtree(target)
        except OSError as error:
            raise SnapshotError(f"cannot discard incomplete snapshot: {target}") from error
