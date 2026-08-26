"""Run one owned child while a caller performs synchronous health samples."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
from pathlib import Path
import subprocess
import time


class MonitoredProcessError(RuntimeError):
    """Raised when a monitored child cannot produce an admissible result."""


class MonitoredProcessTimeout(MonitoredProcessError):
    """Raised after terminating a child that exceeded its timeout."""


class MonitoredProcessOutputLimit(MonitoredProcessError):
    """Raised after terminating a child whose sampled output crossed a limit."""


class MonitoredProcessCheckFailed(MonitoredProcessError):
    """Raised after terminating a child because its monitor failed."""


@dataclass(frozen=True, slots=True)
class MonitoredProcessResult:
    returncode: int
    stdout_bytes: int
    stderr_bytes: int
    elapsed_milliseconds: int
    monitor_calls: int


def _positive_finite(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


def _validate_output(path: Path, label: str) -> None:
    if not isinstance(path, Path) or not path.is_absolute():
        raise MonitoredProcessError(f"{label} must be an absolute path")
    if not path.parent.is_dir():
        raise MonitoredProcessError(f"{label} parent must exist")
    if path.exists():
        raise MonitoredProcessError(f"{label} must not already exist")


def _stop_direct_child(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_monitored_process(
    argv: tuple[str, ...],
    *,
    cwd: Path,
    timeout_seconds: float,
    sample_interval_seconds: float,
    max_output_file_bytes: int,
    stdout_path: Path,
    stderr_path: Path,
    monitor: Callable[[int], None],
) -> MonitoredProcessResult:
    """Run one direct child, sampling until exit and deleting temporary output."""

    if (
        not isinstance(argv, tuple)
        or not argv
        or any(not isinstance(item, str) or not item for item in argv)
    ):
        raise MonitoredProcessError("argv must be a non-empty tuple of non-empty text")
    executable = Path(argv[0])
    if not executable.is_absolute() or not executable.is_file():
        raise MonitoredProcessError("argv[0] must be an existing absolute executable")
    if not isinstance(cwd, Path) or not cwd.is_absolute() or not cwd.is_dir():
        raise MonitoredProcessError("cwd must be an existing absolute directory")
    if not _positive_finite(timeout_seconds):
        raise MonitoredProcessError("timeout_seconds must be positive and finite")
    if not _positive_finite(sample_interval_seconds):
        raise MonitoredProcessError("sample_interval_seconds must be positive and finite")
    if (
        isinstance(max_output_file_bytes, bool)
        or not isinstance(max_output_file_bytes, int)
        or max_output_file_bytes < 1
    ):
        raise MonitoredProcessError("max_output_file_bytes must be a positive integer")
    if not callable(monitor):
        raise MonitoredProcessError("monitor must be callable")
    _validate_output(stdout_path, "stdout_path")
    _validate_output(stderr_path, "stderr_path")
    if stdout_path == stderr_path:
        raise MonitoredProcessError("stdout_path and stderr_path must differ")

    process: subprocess.Popen[bytes] | None = None
    started = time.monotonic_ns()
    monitor_calls = 0
    stdout_bytes = 0
    stderr_bytes = 0
    try:
        with stdout_path.open("xb") as stdout_handle, stderr_path.open("xb") as stderr_handle:
            try:
                process = subprocess.Popen(
                    argv,
                    cwd=cwd,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    shell=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except OSError as error:
                raise MonitoredProcessError(f"monitored child could not start: {error}") from error

            deadline = time.monotonic() + float(timeout_seconds)
            while True:
                stdout_handle.flush()
                stderr_handle.flush()
                stdout_bytes = stdout_path.stat().st_size
                stderr_bytes = stderr_path.stat().st_size
                if max(stdout_bytes, stderr_bytes) > max_output_file_bytes:
                    raise MonitoredProcessOutputLimit(
                        "monitored child crossed the sampled output threshold"
                    )
                returncode = process.poll()
                if returncode is not None:
                    break
                if time.monotonic() >= deadline:
                    raise MonitoredProcessTimeout("monitored child exceeded the frozen timeout")
                try:
                    monitor(process.pid)
                    monitor_calls += 1
                except Exception as error:
                    raise MonitoredProcessCheckFailed("monitor callback failed") from error
                stdout_handle.flush()
                stderr_handle.flush()
                if max(stdout_path.stat().st_size, stderr_path.stat().st_size) > max_output_file_bytes:
                    raise MonitoredProcessOutputLimit(
                        "monitored child crossed the sampled output threshold"
                    )
                remaining = max(0.0, deadline - time.monotonic())
                time.sleep(min(float(sample_interval_seconds), remaining))

            process.wait()
            if isinstance(process.returncode, bool) or not isinstance(process.returncode, int):
                raise MonitoredProcessError("monitored child did not provide a numeric exit code")
            stdout_handle.flush()
            stderr_handle.flush()
            stdout_bytes = stdout_path.stat().st_size
            stderr_bytes = stderr_path.stat().st_size
            if max(stdout_bytes, stderr_bytes) > max_output_file_bytes:
                raise MonitoredProcessOutputLimit(
                    "monitored child crossed the sampled output threshold"
                )
            elapsed = max(0, (time.monotonic_ns() - started) // 1_000_000)
            return MonitoredProcessResult(
                returncode=process.returncode,
                stdout_bytes=stdout_bytes,
                stderr_bytes=stderr_bytes,
                elapsed_milliseconds=elapsed,
                monitor_calls=monitor_calls,
            )
    finally:
        try:
            if process is not None:
                _stop_direct_child(process)
        finally:
            stdout_path.unlink(missing_ok=True)
            stderr_path.unlink(missing_ok=True)
