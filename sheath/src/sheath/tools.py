"""Non-executing command authorization and observation binding."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
from threading import RLock

from .artifacts import ArtifactError, ArtifactStore, digest_bytes
from .decision import Finding, Severity
from .ledger import Evidence, EvidenceLedger


class ToolBoundaryError(ValueError):
    """Raised when a tool-boundary invariant is violated."""


REQUIRED_SANDBOX_GUARANTEES = (
    "filesystem_isolated",
    "network_disabled",
    "process_isolated",
    "resource_limits_enforced",
    "executable_identity_enforced",
)


def _non_empty(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ToolBoundaryError(f"{field} must be a non-empty string without NUL")


def _positive_number(value: float, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ToolBoundaryError(f"{field} must be positive")


def _parse_timestamp(value: str, field: str) -> datetime:
    _non_empty(value, field)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ToolBoundaryError(f"{field} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ToolBoundaryError(f"{field} must include a timezone")
    return parsed


def _validate_digest(value: str, field: str) -> None:
    _non_empty(value, field)
    prefix, separator, digest = value.partition(":")
    if separator != ":" or prefix != "sha256" or len(digest) != 64:
        raise ToolBoundaryError(f"{field} must be a sha256 digest")
    try:
        int(digest, 16)
    except ValueError as error:
        raise ToolBoundaryError(f"{field} must be a sha256 digest") from error


def _digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ExecutableIdentity:
    id: str
    name: str
    path: str
    digest: str
    size_bytes: int
    scope: str = "host_file"
    image_digest: str | None = None

    def __post_init__(self) -> None:
        for field in ("id", "name", "path"):
            _non_empty(getattr(self, field), field)
        if "/" in self.name or "\\" in self.name:
            raise ToolBoundaryError("executable name must be bare")
        if self.name != self.name.casefold():
            raise ToolBoundaryError("executable name must be case-folded")
        if self.scope not in {"host_file", "container_image"}:
            raise ToolBoundaryError("unsupported executable scope")
        _validate_digest(self.digest, "executable digest")
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int):
            raise ToolBoundaryError("executable size_bytes must be an integer")
        if self.scope == "host_file":
            if not Path(self.path).is_absolute():
                raise ToolBoundaryError("host executable path must be absolute")
            if self.size_bytes < 1:
                raise ToolBoundaryError("host executable size_bytes must be positive")
            if self.image_digest is not None:
                raise ToolBoundaryError("host executable cannot have an image digest")
        else:
            if not PurePosixPath(self.path).is_absolute() or ".." in PurePosixPath(
                self.path
            ).parts:
                raise ToolBoundaryError("container executable path must be absolute")
            if self.size_bytes != 0:
                raise ToolBoundaryError("container executable size_bytes must be zero")
            if self.image_digest is None:
                raise ToolBoundaryError("container executable requires an image digest")
            _validate_digest(self.image_digest, "image_digest")
            expected_digest = _container_identity_digest(
                self.path,
                self.image_digest,
            )
            if self.digest != expected_digest:
                raise ToolBoundaryError("container executable digest is noncanonical")
        expected_id = (
            f"executable:{self.name}:{self.digest.removeprefix('sha256:')}"
        )
        if self.id != expected_id:
            raise ToolBoundaryError("executable ID must match its name and digest")

    def matches_source(self) -> bool:
        if self.scope == "container_image":
            assert self.image_digest is not None
            return self.digest == _container_identity_digest(
                self.path,
                self.image_digest,
            )
        path = Path(self.path)
        try:
            return (
                path.is_file()
                and path.stat().st_size == self.size_bytes
                and _digest_file(path) == self.digest
            )
        except OSError:
            return False


def _container_identity_digest(path: str, image_digest: str) -> str:
    payload = json.dumps(
        {"image_digest": image_digest, "path": path},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return digest_bytes(payload)


def identify_executable(name: str, path: Path) -> ExecutableIdentity:
    """Resolve and hash one explicitly selected executable without invoking it."""

    _non_empty(name, "executable name")
    if "/" in name or "\\" in name:
        raise ToolBoundaryError("executable name must be bare")
    try:
        resolved = Path(path).resolve(strict=True)
    except OSError as error:
        raise ToolBoundaryError("executable path must exist") from error
    if not resolved.is_file():
        raise ToolBoundaryError("executable path must identify a file")
    digest = _digest_file(resolved)
    return ExecutableIdentity(
        id=f"executable:{name.casefold()}:{digest.removeprefix('sha256:')}",
        name=name.casefold(),
        path=str(resolved),
        digest=digest,
        size_bytes=resolved.stat().st_size,
    )


def identify_container_executable(
    name: str,
    path: str,
    image_digest: str,
) -> ExecutableIdentity:
    """Bind a container path to an immutable image digest without running it."""

    _non_empty(name, "executable name")
    if "/" in name or "\\" in name:
        raise ToolBoundaryError("executable name must be bare")
    _non_empty(path, "container executable path")
    _validate_digest(image_digest, "image_digest")
    digest = _container_identity_digest(path, image_digest)
    return ExecutableIdentity(
        id=f"executable:{name.casefold()}:{digest.removeprefix('sha256:')}",
        name=name.casefold(),
        path=path,
        digest=digest,
        size_bytes=0,
        scope="container_image",
        image_digest=image_digest,
    )


@dataclass(frozen=True, slots=True)
class CommandAction:
    id: str
    argv: tuple[str, ...]
    working_directory: str = "."
    timeout_seconds: float = 30
    max_output_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        _non_empty(self.id, "action id")
        if not isinstance(self.argv, tuple) or not self.argv:
            raise ToolBoundaryError("argv must be a non-empty tuple")
        if any(not isinstance(item, str) or "\x00" in item for item in self.argv):
            raise ToolBoundaryError("argv items must be strings without NUL")
        _non_empty(self.argv[0], "argv[0]")
        _non_empty(self.working_directory, "working_directory")
        _positive_number(self.timeout_seconds, "timeout_seconds")
        if (
            isinstance(self.max_output_bytes, bool)
            or not isinstance(self.max_output_bytes, int)
            or self.max_output_bytes < 1
        ):
            raise ToolBoundaryError("max_output_bytes must be a positive integer")


@dataclass(frozen=True, slots=True)
class Authorization:
    id: str
    action_id: str
    revision: str
    allowed: bool
    reason_codes: tuple[str, ...]
    resolved_working_directory: str | None
    executable_id: str | None
    policy_digest: str


@dataclass(frozen=True, slots=True)
class CommandPolicy:
    workspace_root: Path
    trusted_executables: tuple[ExecutableIdentity, ...]
    max_timeout_seconds: float = 60
    max_output_bytes: int = 4_194_304

    def __post_init__(self) -> None:
        root = Path(self.workspace_root).resolve()
        if not root.is_dir():
            raise ToolBoundaryError("workspace_root must be an existing directory")
        if not isinstance(self.trusted_executables, tuple) or not self.trusted_executables:
            raise ToolBoundaryError("trusted_executables must be a non-empty tuple")
        if any(
            not isinstance(executable, ExecutableIdentity)
            for executable in self.trusted_executables
        ):
            raise ToolBoundaryError("trusted_executables must contain identities")
        names = tuple(item.name.casefold() for item in self.trusted_executables)
        if len(names) != len(set(names)):
            raise ToolBoundaryError("trusted executable names must be unique")
        if any(not item.matches_source() for item in self.trusted_executables):
            raise ToolBoundaryError("trusted executable identity does not match its source")
        _positive_number(self.max_timeout_seconds, "max_timeout_seconds")
        if (
            isinstance(self.max_output_bytes, bool)
            or not isinstance(self.max_output_bytes, int)
            or self.max_output_bytes < 1
        ):
            raise ToolBoundaryError("max_output_bytes must be a positive integer")
        object.__setattr__(self, "workspace_root", root)

    @property
    def digest(self) -> str:
        payload = json.dumps(
            {
                "workspace_root": str(self.workspace_root),
                "trusted_executables": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "path": item.path,
                        "digest": item.digest,
                        "size_bytes": item.size_bytes,
                        "scope": item.scope,
                        "image_digest": item.image_digest,
                    }
                    for item in sorted(
                        self.trusted_executables,
                        key=lambda executable: executable.name,
                    )
                ],
                "max_timeout_seconds": self.max_timeout_seconds,
                "max_output_bytes": self.max_output_bytes,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return digest_bytes(payload)

    def authorize(self, action: CommandAction, revision: str) -> Authorization:
        _non_empty(revision, "revision")
        reasons: list[str] = []
        identities = {
            item.name.casefold(): item for item in self.trusted_executables
        }
        identity = identities.get(action.argv[0].casefold())
        if identity is None:
            reasons.append("policy.executable_not_allowed")
        elif not identity.matches_source():
            reasons.append("policy.executable_identity_changed")
        if action.timeout_seconds > self.max_timeout_seconds:
            reasons.append("policy.timeout_exceeded")
        if action.max_output_bytes > self.max_output_bytes:
            reasons.append("policy.output_limit_exceeded")

        requested = Path(action.working_directory)
        candidate = requested if requested.is_absolute() else self.workspace_root / requested
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            reasons.append("policy.cwd_outside_root")
            resolved_text = None
        else:
            resolved_text = str(resolved)
            if not resolved.is_dir():
                reasons.append("policy.cwd_missing")

        allowed = not reasons
        return Authorization(
            id=f"authorization:{action.id}",
            action_id=action.id,
            revision=revision,
            allowed=allowed,
            reason_codes=tuple(reasons or ("policy.command_allowed",)),
            resolved_working_directory=resolved_text,
            executable_id=None if identity is None else identity.id,
            policy_digest=self.digest,
        )


@dataclass(frozen=True, slots=True)
class Observation:
    id: str
    action_id: str
    revision: str
    started_at: str
    ended_at: str
    exit_code: int | None
    timed_out: bool
    stdout_digest: str
    stderr_digest: str
    stdout_artifact_id: str
    stderr_artifact_id: str
    environment_digest: str
    sandbox_id: str
    sandbox_version: str
    sandbox_digest: str
    sandbox_guarantees: tuple[str, ...]
    stdout_truncated: bool
    stderr_truncated: bool

    def __post_init__(self) -> None:
        for field in (
            "id",
            "action_id",
            "revision",
            "stdout_artifact_id",
            "stderr_artifact_id",
            "sandbox_id",
            "sandbox_version",
        ):
            _non_empty(getattr(self, field), field)
        started = _parse_timestamp(self.started_at, "started_at")
        ended = _parse_timestamp(self.ended_at, "ended_at")
        if ended < started:
            raise ToolBoundaryError("ended_at cannot precede started_at")
        if not isinstance(self.timed_out, bool):
            raise ToolBoundaryError("timed_out must be boolean")
        if self.timed_out and self.exit_code is not None:
            raise ToolBoundaryError("timed-out observations cannot have an exit code")
        if (
            not self.timed_out
            and (isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int))
        ):
            raise ToolBoundaryError("completed observations require an integer exit code")
        for field in (
            "stdout_digest",
            "stderr_digest",
            "environment_digest",
            "sandbox_digest",
        ):
            _validate_digest(getattr(self, field), field)
        if not isinstance(self.stdout_truncated, bool):
            raise ToolBoundaryError("stdout_truncated must be boolean")
        if not isinstance(self.stderr_truncated, bool):
            raise ToolBoundaryError("stderr_truncated must be boolean")
        if self.sandbox_guarantees != REQUIRED_SANDBOX_GUARANTEES:
            raise ToolBoundaryError("sandbox guarantees are incomplete or noncanonical")

    @property
    def passed(self) -> bool:
        return (
            not self.timed_out
            and self.exit_code == 0
            and not self.stdout_truncated
            and not self.stderr_truncated
        )


class ToolSession:
    """Binds policy decisions and supplied observations to one evidence ledger."""

    def __init__(
        self,
        policy: CommandPolicy,
        ledger: EvidenceLedger,
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self._policy = policy
        self._ledger = ledger
        self._artifact_store = artifact_store
        self._lock = RLock()
        self._actions: dict[str, CommandAction] = {}
        self._authorizations: dict[str, Authorization] = {}
        self._observations: dict[str, Observation] = {}

    @property
    def actions(self) -> tuple[CommandAction, ...]:
        with self._lock:
            return tuple(self._actions.values())

    @property
    def authorizations(self) -> tuple[Authorization, ...]:
        with self._lock:
            return tuple(self._authorizations.values())

    @property
    def observations(self) -> tuple[Observation, ...]:
        with self._lock:
            return tuple(self._observations.values())

    @property
    def executables(self) -> tuple[ExecutableIdentity, ...]:
        return self._policy.trusted_executables

    @property
    def policy(self) -> CommandPolicy:
        return self._policy

    @property
    def ledger(self) -> EvidenceLedger:
        return self._ledger

    @property
    def artifact_store(self) -> ArtifactStore | None:
        return self._artifact_store

    @property
    def blocking_findings(self) -> tuple[Finding, ...]:
        with self._lock:
            return tuple(
                Finding(
                    id=f"finding:{authorization.id}",
                    category="unsafe_action",
                    severity=Severity.BLOCKING,
                    message="Command authorization failed: "
                    + ", ".join(authorization.reason_codes),
                    evidence_ids=(authorization.id,),
                    source="policy",
                )
                for authorization in self._authorizations.values()
                if not authorization.allowed
            )

    def request_action(self, action: CommandAction) -> Authorization:
        with self._lock:
            if action.id in self._actions:
                raise ToolBoundaryError(f"duplicate action ID: {action.id}")
            revision = self._ledger.current_revision
            authorization = self._policy.authorize(action, revision)
            if self._ledger.has_evidence(authorization.id):
                raise ToolBoundaryError(
                    f"authorization evidence already exists: {authorization.id}"
                )
            self._ledger.record_tool_request(
                action.id,
                authorization.id,
                allowed=authorization.allowed,
            )
            self._ledger.record_evidence(
                Evidence(
                    id=authorization.id,
                    check_id="policy.command",
                    revision=revision,
                    passed=authorization.allowed,
                    source="policy",
                    detail=";".join(authorization.reason_codes),
                )
            )
            self._actions[action.id] = action
            self._authorizations[action.id] = authorization
            return authorization

    def record_observation(
        self,
        observation: Observation,
        check_ids: tuple[str, ...],
    ) -> tuple[Evidence, ...]:
        if not isinstance(check_ids, tuple) or not check_ids:
            raise ToolBoundaryError("check_ids must be a non-empty tuple")
        if any(not isinstance(item, str) or not item.strip() for item in check_ids):
            raise ToolBoundaryError("check IDs must be non-empty strings")
        if len(check_ids) != len(set(check_ids)):
            raise ToolBoundaryError("check_ids must be unique")

        with self._lock:
            if observation.id in self._observations:
                raise ToolBoundaryError(f"duplicate observation ID: {observation.id}")
            action = self._actions.get(observation.action_id)
            authorization = self._authorizations.get(observation.action_id)
            if action is None or authorization is None:
                raise ToolBoundaryError("observation references an unknown action")
            if not authorization.allowed:
                raise ToolBoundaryError("blocked actions cannot produce observations")
            current_revision = self._ledger.current_revision
            if authorization.revision != current_revision:
                raise ToolBoundaryError("action authorization is stale")
            if observation.revision != current_revision:
                raise ToolBoundaryError("observation revision is not current")

            if self._artifact_store is None:
                raise ToolBoundaryError("observations require an ArtifactStore")
            try:
                stdout = self._artifact_store.get(observation.stdout_artifact_id)
                stderr = self._artifact_store.get(observation.stderr_artifact_id)
            except ArtifactError as error:
                raise ToolBoundaryError(str(error)) from error
            if stdout.kind != "stdout" or stdout.digest != observation.stdout_digest:
                raise ToolBoundaryError("stdout artifact does not match observation")
            if stderr.kind != "stderr" or stderr.digest != observation.stderr_digest:
                raise ToolBoundaryError("stderr artifact does not match observation")

            evidence_ids = tuple(
                f"observation:{observation.id}:{check_id}" for check_id in check_ids
            )
            if any(self._ledger.has_evidence(item) for item in evidence_ids):
                raise ToolBoundaryError("observation would duplicate an evidence ID")

            detail = (
                f"action={action.id};observation={observation.id};"
                f"exit_code={observation.exit_code};timed_out={observation.timed_out};"
                f"stdout_truncated={observation.stdout_truncated};"
                f"stderr_truncated={observation.stderr_truncated};"
                f"stdout={observation.stdout_digest};stderr={observation.stderr_digest}"
            )
            evidence = tuple(
                Evidence(
                    id=evidence_id,
                    check_id=check_id,
                    revision=current_revision,
                    passed=observation.passed,
                    source="tool",
                    detail=detail,
                )
                for evidence_id, check_id in zip(evidence_ids, check_ids)
            )
            self._ledger.record_tool_observation(
                action.id,
                observation.id,
                passed=observation.passed,
            )
            for item in evidence:
                self._ledger.record_evidence(item)
            self._observations[observation.id] = observation
            return evidence
