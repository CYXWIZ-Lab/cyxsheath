"""Fail-closed coordination for an externally isolated execution backend."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from typing import Protocol

from .artifacts import ArtifactError, digest_bytes
from .ledger import Evidence
from .tools import (
    REQUIRED_SANDBOX_GUARANTEES,
    Authorization,
    CommandAction,
    Observation,
    ToolBoundaryError,
    ToolSession,
)


class RunnerError(RuntimeError):
    """Raised when safe execution or trustworthy observation is unavailable."""


def _text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise RunnerError(f"{field} must be a non-empty string without NUL")


def _sha256(value: str, field: str) -> None:
    _text(value, field)
    prefix, separator, hexadecimal = value.partition(":")
    if separator != ":" or prefix != "sha256" or len(hexadecimal) != 64:
        raise RunnerError(f"{field} must be a sha256 digest")
    try:
        int(hexadecimal, 16)
    except ValueError as error:
        raise RunnerError(f"{field} must be a sha256 digest") from error


def _timestamp(value: str, field: str) -> datetime:
    _text(value, field)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RunnerError(f"{field} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise RunnerError(f"{field} must include a timezone")
    return parsed


@dataclass(frozen=True, slots=True)
class SandboxProfile:
    backend_id: str
    backend_version: str
    environment_digest: str
    filesystem_isolated: bool
    network_disabled: bool
    process_isolated: bool
    resource_limits_enforced: bool
    executable_identity_enforced: bool

    def __post_init__(self) -> None:
        _text(self.backend_id, "backend_id")
        _text(self.backend_version, "backend_version")
        _sha256(self.environment_digest, "environment_digest")
        for field in (
            "filesystem_isolated",
            "network_disabled",
            "process_isolated",
            "resource_limits_enforced",
            "executable_identity_enforced",
        ):
            if not isinstance(getattr(self, field), bool):
                raise RunnerError(f"{field} must be boolean")

    @property
    def id(self) -> str:
        return self.backend_id

    @property
    def guarantees(self) -> tuple[str, ...]:
        return tuple(
            field
            for field in REQUIRED_SANDBOX_GUARANTEES
            if getattr(self, field)
        )

    @property
    def secure(self) -> bool:
        return all(
            (
                self.filesystem_isolated,
                self.network_disabled,
                self.process_isolated,
                self.resource_limits_enforced,
                self.executable_identity_enforced,
            )
        )

    @property
    def digest(self) -> str:
        record = {
            "backend_id": self.backend_id,
            "backend_version": self.backend_version,
            "environment_digest": self.environment_digest,
            "executable_identity_enforced": self.executable_identity_enforced,
            "filesystem_isolated": self.filesystem_isolated,
            "network_disabled": self.network_disabled,
            "process_isolated": self.process_isolated,
            "resource_limits_enforced": self.resource_limits_enforced,
        }
        encoded = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        return digest_bytes(encoded)


@dataclass(frozen=True, slots=True)
class SandboxRequest:
    action_id: str
    executable_path: str
    executable_digest: str
    executable_size_bytes: int
    executable_scope: str
    executable_image_digest: str | None
    argv: tuple[str, ...]
    working_directory: str
    timeout_seconds: float
    max_output_bytes: int
    environment_digest: str


@dataclass(frozen=True, slots=True)
class SandboxResult:
    action_id: str
    sandbox_digest: str
    started_at: str
    ended_at: str
    exit_code: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    def __post_init__(self) -> None:
        _text(self.action_id, "action_id")
        _sha256(self.sandbox_digest, "sandbox_digest")
        started = _timestamp(self.started_at, "started_at")
        ended = _timestamp(self.ended_at, "ended_at")
        if ended < started:
            raise RunnerError("ended_at cannot precede started_at")
        if not isinstance(self.stdout, bytes) or not isinstance(self.stderr, bytes):
            raise RunnerError("sandbox output must be bytes")
        if not isinstance(self.timed_out, bool):
            raise RunnerError("timed_out must be boolean")
        if not isinstance(self.stdout_truncated, bool):
            raise RunnerError("stdout_truncated must be boolean")
        if not isinstance(self.stderr_truncated, bool):
            raise RunnerError("stderr_truncated must be boolean")
        if self.timed_out and self.exit_code is not None:
            raise RunnerError("timed-out results cannot have an exit code")
        if (
            not self.timed_out
            and (isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int))
        ):
            raise RunnerError("completed results require an integer exit code")


class SandboxBackend(Protocol):
    @property
    def profile(self) -> SandboxProfile: ...

    def execute(self, request: SandboxRequest) -> SandboxResult: ...


@dataclass(frozen=True, slots=True)
class ExecutionOutcome:
    authorization: Authorization
    observation: Observation | None
    evidence: tuple[Evidence, ...]


class ConstrainedRunner:
    """Dispatches only authorized actions to a backend claiming full isolation."""

    def __init__(self, session: ToolSession, backend: SandboxBackend) -> None:
        if session.artifact_store is None:
            raise RunnerError("runner requires an ArtifactStore")
        self._session = session
        self._backend = backend

    def execute(
        self,
        action: CommandAction,
        check_ids: tuple[str, ...],
    ) -> ExecutionOutcome:
        if not isinstance(check_ids, tuple) or not check_ids:
            raise RunnerError("check_ids must be a non-empty tuple")
        if any(not isinstance(item, str) or not item.strip() for item in check_ids):
            raise RunnerError("check IDs must be non-empty strings")
        if len(check_ids) != len(set(check_ids)):
            raise RunnerError("check_ids must be unique")

        authorization = self._session.request_action(action)
        if not authorization.allowed:
            return ExecutionOutcome(authorization, None, ())

        try:
            profile = self._backend.profile
        except Exception as error:
            self._session.ledger.record_tool_error(
                action.id,
                "sandbox.profile_failure",
            )
            raise RunnerError("sandbox backend profile is unavailable") from error
        if not isinstance(profile, SandboxProfile) or not profile.secure:
            raise self._error(
                action.id,
                "sandbox.isolation_unavailable",
                "sandbox backend does not guarantee required isolation",
            )

        identity = next(
            (
                item
                for item in self._session.executables
                if item.id == authorization.executable_id
            ),
            None,
        )
        if identity is None:
            raise self._error(
                action.id,
                "runner.executable_identity_missing",
                "authorization has no executable identity",
            )
        if authorization.resolved_working_directory is None:
            raise self._error(
                action.id,
                "runner.working_directory_missing",
                "authorization has no working directory",
            )

        request = SandboxRequest(
            action_id=action.id,
            executable_path=identity.path,
            executable_digest=identity.digest,
            executable_size_bytes=identity.size_bytes,
            executable_scope=identity.scope,
            executable_image_digest=identity.image_digest,
            argv=(identity.path, *action.argv[1:]),
            working_directory=authorization.resolved_working_directory,
            timeout_seconds=action.timeout_seconds,
            max_output_bytes=action.max_output_bytes,
            environment_digest=profile.environment_digest,
        )

        if not identity.matches_source():
            raise self._error(
                action.id,
                "sandbox.executable_identity_changed",
                "executable identity changed before sandbox dispatch",
            )
        try:
            result = self._backend.execute(request)
        except Exception as error:
            self._session.ledger.record_tool_error(
                action.id,
                "sandbox.backend_failure",
            )
            raise RunnerError("sandbox backend execution failed") from error
        try:
            self._validate_result(action, profile, result)
        except RunnerError:
            self._session.ledger.record_tool_error(
                action.id,
                "sandbox.invalid_result",
            )
            raise

        store = self._session.artifact_store
        assert store is not None
        try:
            stdout = store.store_bytes("stdout", result.stdout)
            stderr = store.store_bytes("stderr", result.stderr)
        except ArtifactError as error:
            self._session.ledger.record_tool_error(
                action.id,
                "runner.artifact_failure",
            )
            raise RunnerError(str(error)) from error

        try:
            observation = Observation(
                id=f"observation:{action.id}",
                action_id=action.id,
                revision=authorization.revision,
                started_at=result.started_at,
                ended_at=result.ended_at,
                exit_code=result.exit_code,
                timed_out=result.timed_out,
                stdout_digest=stdout.digest,
                stderr_digest=stderr.digest,
                stdout_artifact_id=stdout.id,
                stderr_artifact_id=stderr.id,
                environment_digest=profile.environment_digest,
                sandbox_id=profile.id,
                sandbox_version=profile.backend_version,
                sandbox_digest=profile.digest,
                sandbox_guarantees=profile.guarantees,
                stdout_truncated=result.stdout_truncated,
                stderr_truncated=result.stderr_truncated,
            )
            evidence = self._session.record_observation(observation, check_ids)
        except ToolBoundaryError as error:
            self._session.ledger.record_tool_error(
                action.id,
                "runner.observation_rejected",
            )
            raise RunnerError(str(error)) from error
        return ExecutionOutcome(authorization, observation, evidence)

    def _error(self, action_id: str, status: str, message: str) -> RunnerError:
        self._session.ledger.record_tool_error(action_id, status)
        return RunnerError(message)

    @staticmethod
    def _validate_result(
        action: CommandAction,
        profile: SandboxProfile,
        result: SandboxResult,
    ) -> None:
        if not isinstance(result, SandboxResult):
            raise RunnerError("sandbox backend returned an invalid result")
        if result.action_id != action.id:
            raise RunnerError("sandbox result references another action")
        if result.sandbox_digest != profile.digest:
            raise RunnerError("sandbox result profile does not match the request")
        if len(result.stdout) + len(result.stderr) > action.max_output_bytes:
            raise RunnerError("sandbox backend exceeded the output byte limit")
