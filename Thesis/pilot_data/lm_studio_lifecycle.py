"""Parse and verify LM Studio daemon lifecycle control observations."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import time
from typing import Callable, Any

from cli_transport import CliTransportResult


class LifecycleError(RuntimeError):
    """Raised when LM Studio lifecycle evidence violates the frozen contract."""


@dataclass(frozen=True, slots=True)
class ControlObservation:
    command: str
    returncode: int
    stdout_bytes: int
    stdout_sha256: str
    stderr_bytes: int
    stderr_sha256: str
    elapsed_milliseconds: int
    diagnostic_code: str

    def to_record(self) -> dict[str, int | str]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "stdout_bytes": self.stdout_bytes,
            "stdout_sha256": self.stdout_sha256,
            "stderr_bytes": self.stderr_bytes,
            "stderr_sha256": self.stderr_sha256,
            "elapsed_milliseconds": self.elapsed_milliseconds,
            "diagnostic_code": self.diagnostic_code,
        }


@dataclass(frozen=True, slots=True)
class DaemonInfo:
    status: str
    pid: int
    is_daemon: bool
    version: str

    def to_record(self) -> dict[str, int | bool | str]:
        return {
            "status": self.status,
            "pid": self.pid,
            "isDaemon": self.is_daemon,
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class DaemonStatus:
    status: str
    pid: int | None = None
    is_daemon: bool | None = None

    def to_record(self) -> dict[str, int | bool | str]:
        record: dict[str, int | bool | str] = {"status": self.status}
        if self.pid is not None:
            record["pid"] = self.pid
        if self.is_daemon is not None:
            record["isDaemon"] = self.is_daemon
        return record


@dataclass(frozen=True, slots=True)
class ShutdownObservation:
    status_before: DaemonStatus
    status_before_control: ControlObservation
    daemon_down_control: ControlObservation
    status_after: DaemonStatus
    status_after_control: ControlObservation
    status_poll_count: int

    def to_record(self) -> dict[str, Any]:
        return {
            "status_before": self.status_before.to_record(),
            "status_before_control": self.status_before_control.to_record(),
            "daemon_down_control": self.daemon_down_control.to_record(),
            "status_after": self.status_after.to_record(),
            "status_after_control": self.status_after_control.to_record(),
            "status_poll_count": self.status_poll_count,
        }


def _decode(payload: bytes) -> str:
    return payload.decode("utf-8-sig", errors="replace")


def _diagnostic_code(command: str, result: CliTransportResult) -> str:
    combined = f"{_decode(result.stdout)}\n{_decode(result.stderr)}"
    if command == "daemon_down":
        if "The daemon is currently running as part of LM Studio" in combined:
            return "desktop_service_refusal"
        if "Daemon is not running." in combined:
            return "daemon_not_running"
        if "Shutting down llmster" in combined and "Done." in combined:
            return "shutdown_requested"
    if command in {"daemon_up_json", "daemon_status_json"}:
        try:
            if isinstance(json.loads(_decode(result.stdout)), dict):
                return "json_payload"
        except json.JSONDecodeError:
            pass
    if not result.stdout and not result.stderr:
        return "no_output"
    return "unclassified"


def observe_control(command: str, result: CliTransportResult) -> ControlObservation:
    if command not in {"daemon_up_json", "daemon_status_json", "daemon_down"}:
        raise LifecycleError("control_observation_command_invalid")
    return ControlObservation(
        command=command,
        returncode=result.returncode,
        stdout_bytes=len(result.stdout),
        stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
        stderr_bytes=len(result.stderr),
        stderr_sha256=hashlib.sha256(result.stderr).hexdigest(),
        elapsed_milliseconds=result.elapsed_milliseconds,
        diagnostic_code=_diagnostic_code(command, result),
    )


def _parse_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        raw = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LifecycleError(f"{label}_json_invalid") from error
    if not isinstance(raw, dict):
        raise LifecycleError(f"{label}_shape_invalid")
    return raw


def _positive_pid(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise LifecycleError(f"{label}_pid_invalid")
    return value


def parse_daemon_up(result: CliTransportResult) -> DaemonInfo:
    if result.returncode != 0:
        raise LifecycleError("daemon_up_exit_nonzero")
    raw = _parse_object(result.stdout, "daemon_up")
    if raw.get("status") != "running":
        raise LifecycleError("daemon_up_status_invalid")
    if not isinstance(raw.get("isDaemon"), bool):
        raise LifecycleError("daemon_up_mode_invalid")
    version = raw.get("version")
    if not isinstance(version, str) or not version:
        raise LifecycleError("daemon_up_version_invalid")
    return DaemonInfo(
        status="running",
        pid=_positive_pid(raw.get("pid"), "daemon_up"),
        is_daemon=raw["isDaemon"],
        version=version,
    )


def parse_daemon_status(result: CliTransportResult) -> DaemonStatus:
    if result.returncode != 0:
        raise LifecycleError("daemon_status_exit_nonzero")
    raw = _parse_object(result.stdout, "daemon_status")
    status = raw.get("status")
    if status == "not-running":
        return DaemonStatus(status="not-running")
    if status != "running":
        raise LifecycleError("daemon_status_value_invalid")
    if not isinstance(raw.get("isDaemon"), bool):
        raise LifecycleError("daemon_status_mode_invalid")
    return DaemonStatus(
        status="running",
        pid=_positive_pid(raw.get("pid"), "daemon_status"),
        is_daemon=raw["isDaemon"],
    )


def require_standalone_start(info: DaemonInfo, *, owned_root_pid: int) -> None:
    if info.status != "running":
        raise LifecycleError("daemon_start_not_running")
    if not info.is_daemon:
        raise LifecycleError("desktop_service_mode_incompatible")
    if info.pid != owned_root_pid:
        raise LifecycleError("daemon_pid_owned_root_mismatch")


def observe_standalone_shutdown(
    *,
    status_reader: Callable[[], CliTransportResult],
    down_runner: Callable[[], CliTransportResult],
    expected_pid: int,
    timeout_seconds: float,
    poll_interval_seconds: float,
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> ShutdownObservation:
    _positive_pid(expected_pid, "shutdown_expected")
    for value, label in (
        (timeout_seconds, "shutdown_timeout"),
        (poll_interval_seconds, "shutdown_poll_interval"),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise LifecycleError(f"{label}_invalid")

    before_result = status_reader()
    before_control = observe_control("daemon_status_json", before_result)
    before = parse_daemon_status(before_result)
    if before.status != "running" or before.is_daemon is not True:
        raise LifecycleError("shutdown_target_not_standalone_daemon")
    if before.pid != expected_pid:
        raise LifecycleError("shutdown_target_pid_mismatch")

    down_result = down_runner()
    down_control = observe_control("daemon_down", down_result)
    deadline = monotonic() + timeout_seconds
    poll_count = 0
    after = before
    after_control = before_control
    while True:
        status_result = status_reader()
        poll_count += 1
        after_control = observe_control("daemon_status_json", status_result)
        after = parse_daemon_status(status_result)
        if after.status == "not-running" or monotonic() >= deadline:
            break
        sleeper(poll_interval_seconds)
    return ShutdownObservation(
        status_before=before,
        status_before_control=before_control,
        daemon_down_control=down_control,
        status_after=after,
        status_after_control=after_control,
        status_poll_count=poll_count,
    )
