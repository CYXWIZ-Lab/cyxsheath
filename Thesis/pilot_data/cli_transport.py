"""Run one local CLI process with an observable exit and bounded retention."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import subprocess
import time


class CliTransportError(RuntimeError):
    """Raised when the CLI transport cannot produce an admissible result."""


class CliTransportTimeout(CliTransportError):
    """Raised when the direct child does not exit within the frozen timeout."""


@dataclass(frozen=True, slots=True)
class CliTransportResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    elapsed_milliseconds: int


def run_cli(
    argv: tuple[str, ...],
    *,
    cwd: Path,
    timeout_seconds: float,
    max_output_bytes: int,
) -> CliTransportResult:
    """Execute one absolute command without a shell and return its numeric exit."""

    if (
        not isinstance(argv, tuple)
        or not argv
        or any(not isinstance(item, str) or not item for item in argv)
    ):
        raise CliTransportError("argv must be a non-empty tuple of non-empty text")
    executable = Path(argv[0])
    if not executable.is_absolute() or not executable.is_file():
        raise CliTransportError("argv[0] must be an existing absolute executable")
    if not isinstance(cwd, Path) or not cwd.is_absolute() or not cwd.is_dir():
        raise CliTransportError("cwd must be an existing absolute directory")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise CliTransportError("timeout_seconds must be positive and finite")
    if (
        isinstance(max_output_bytes, bool)
        or not isinstance(max_output_bytes, int)
        or max_output_bytes < 1
    ):
        raise CliTransportError("max_output_bytes must be a positive integer")

    started = time.monotonic_ns()
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            check=False,
            timeout=float(timeout_seconds),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as error:
        raise CliTransportTimeout("CLI child exceeded the frozen timeout") from error
    except OSError as error:
        raise CliTransportError(f"CLI child could not start: {error}") from error

    elapsed = max(0, (time.monotonic_ns() - started) // 1_000_000)
    if isinstance(completed.returncode, bool) or not isinstance(completed.returncode, int):
        raise CliTransportError("CLI child did not provide a numeric exit code")
    if len(completed.stdout) + len(completed.stderr) > max_output_bytes:
        raise CliTransportError("CLI output exceeded the retention bound")
    return CliTransportResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        elapsed_milliseconds=elapsed,
    )
