"""Content-addressed, tamper-evident storage for run output bytes."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from threading import RLock


class ArtifactError(ValueError):
    """Raised when artifact storage or verification fails."""


_KINDS = {
    "prompt",
    "response",
    "patch",
    "stdout",
    "stderr",
    "test_report",
    "analysis_report",
    "manifest",
    "other",
}


def digest_bytes(content: bytes) -> str:
    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")
    return "sha256:" + hashlib.sha256(content).hexdigest()


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    id: str
    kind: str
    path: str
    digest: str
    size_bytes: int
    redacted: bool = False


class ArtifactStore:
    """Stores bytes once under their SHA-256 digest and verifies them on access."""

    def __init__(self, root: Path) -> None:
        requested = Path(root)
        if requested.exists() and not requested.is_dir():
            raise ArtifactError("artifact root must be a directory")
        requested.mkdir(parents=False, exist_ok=True)
        self._root = requested.resolve()
        self._lock = RLock()
        self._artifacts: dict[str, StoredArtifact] = {}

    @property
    def root(self) -> Path:
        return self._root

    @property
    def artifacts(self) -> tuple[StoredArtifact, ...]:
        with self._lock:
            return tuple(self._artifacts.values())

    def store_bytes(
        self,
        kind: str,
        content: bytes,
        *,
        redacted: bool = False,
    ) -> StoredArtifact:
        if kind not in _KINDS:
            raise ArtifactError(f"unsupported artifact kind: {kind}")
        if not isinstance(content, bytes):
            raise TypeError("artifact content must be bytes")
        if not isinstance(redacted, bool):
            raise ArtifactError("redacted must be boolean")

        digest = digest_bytes(content)
        hexadecimal = digest.removeprefix("sha256:")
        relative = Path("objects") / "sha256" / hexadecimal[:2] / hexadecimal
        target = self._root / relative
        artifact_id = f"artifact:{kind}:{hexadecimal}"
        artifact = StoredArtifact(
            id=artifact_id,
            kind=kind,
            path=relative.as_posix(),
            digest=digest,
            size_bytes=len(content),
            redacted=redacted,
        )

        with self._lock:
            prior = self._artifacts.get(artifact_id)
            if prior is not None:
                if prior.redacted != redacted:
                    raise ArtifactError("artifact metadata conflicts with prior storage")
                self._verify_file(prior)
                return prior

            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with target.open("xb") as stream:
                    stream.write(content)
            except FileExistsError:
                pass

            self._verify_file(artifact)
            self._artifacts[artifact_id] = artifact
            return artifact

    def get(self, artifact_id: str) -> StoredArtifact:
        with self._lock:
            try:
                artifact = self._artifacts[artifact_id]
            except KeyError as error:
                raise ArtifactError(f"unknown artifact ID: {artifact_id}") from error
            self._verify_file(artifact)
            return artifact

    def verify(self, artifact: StoredArtifact) -> None:
        with self._lock:
            known = self._artifacts.get(artifact.id)
            if known != artifact:
                raise ArtifactError(f"artifact is not registered: {artifact.id}")
            self._verify_file(artifact)

    def _verify_file(self, artifact: StoredArtifact) -> None:
        target = (self._root / artifact.path).resolve()
        try:
            target.relative_to(self._root)
        except ValueError as error:
            raise ArtifactError("artifact path escapes its store") from error
        try:
            content = target.read_bytes()
        except OSError as error:
            raise ArtifactError(f"artifact bytes are unavailable: {artifact.id}") from error
        if len(content) != artifact.size_bytes or digest_bytes(content) != artifact.digest:
            raise ArtifactError(f"artifact integrity check failed: {artifact.id}")
