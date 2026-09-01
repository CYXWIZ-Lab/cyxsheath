"""Construct and parse one bounded Windows Authenticode inspection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Protocol

try:
    from .cli_transport import (
        CliTransportError,
        CliTransportResult,
        CliTransportTimeout,
        run_cli,
    )
    from .llmster_authenticode_review import InspectionObservation
except ImportError:
    from cli_transport import (
        CliTransportError,
        CliTransportResult,
        CliTransportTimeout,
        run_cli,
    )
    from llmster_authenticode_review import InspectionObservation


SCRIPT_PATH = Path(__file__).resolve().with_name("get_authenticode_status.ps1")
SCRIPT_SHA256 = "493fde84b50f1f10497b89345882962db9db912f8e54d8c992bbad5dc728d8e9"
TIMEOUT_SECONDS = 10.0
MAX_COMBINED_OUTPUT_BYTES = 4096
MAX_STDOUT_JSON_BYTES = 512
CANDIDATE_SUFFIXES = {".dll", ".exe", ".node", ".ps1"}
STATUS_TEXT = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")


class Transport(Protocol):
    def __call__(
        self,
        argv: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: float,
        max_output_bytes: int,
    ) -> CliTransportResult: ...


class WindowsAuthenticodeAdapterError(ValueError):
    """Raised when adapter identity or input invariants do not hold."""


def _expect(condition: bool, code: str) -> None:
    if not condition:
        raise WindowsAuthenticodeAdapterError(code)


def _is_link_like(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction is not None and is_junction())


def _identity(path: Path, code: str) -> tuple[int, int, int, int]:
    try:
        item = path.stat(follow_symlinks=False)
    except OSError as error:
        raise WindowsAuthenticodeAdapterError(code) from error
    return (int(item.st_dev), int(item.st_ino), int(item.st_size), int(item.st_mtime_ns))


def _sha256(path: Path, code: str) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise WindowsAuthenticodeAdapterError(code) from error
    return digest.hexdigest()


def _validate_regular_absolute(path: Path, label: str) -> tuple[int, int, int, int]:
    _expect(isinstance(path, Path) and path.is_absolute(), f"{label}_must_be_absolute")
    _expect(path.is_file() and not _is_link_like(path), f"{label}_must_be_regular_non_link")
    return _identity(path, f"{label}_stat_failed")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _parse_status(stdout: bytes) -> InspectionObservation:
    if not isinstance(stdout, bytes) or len(stdout) > MAX_STDOUT_JSON_BYTES:
        return InspectionObservation.tool_error()
    try:
        decoded = stdout.decode("utf-8-sig")
        payload = json.loads(decoded, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return InspectionObservation.tool_error()
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "status"}:
        return InspectionObservation.tool_error()
    if payload["schema_version"] != "1.0.0":
        return InspectionObservation.tool_error()
    status = payload["status"]
    if not isinstance(status, str) or STATUS_TEXT.fullmatch(status) is None:
        return InspectionObservation.tool_error()
    return InspectionObservation.status(status)


def inspect_candidate(
    candidate_path: Path,
    *,
    powershell_path: Path,
    expected_powershell_sha256: str,
    transport: Transport = run_cli,
) -> InspectionObservation:
    """Inspect one candidate through the exact source-bound transport contract."""

    _expect(callable(transport), "transport_not_callable")
    executable_identity = _validate_regular_absolute(powershell_path, "powershell")
    _expect(powershell_path.name.casefold() == "powershell.exe", "powershell_name_rejected")
    _expect(
        isinstance(expected_powershell_sha256, str)
        and re.fullmatch(r"[0-9a-f]{64}", expected_powershell_sha256) is not None,
        "powershell_digest_invalid",
    )
    _expect(
        _sha256(powershell_path, "powershell_read_failed")
        == expected_powershell_sha256,
        "powershell_digest_mismatch",
    )
    _expect(
        _identity(powershell_path, "powershell_stat_failed") == executable_identity,
        "powershell_changed_during_identity_check",
    )

    script_identity = _validate_regular_absolute(SCRIPT_PATH, "script")
    _expect(_sha256(SCRIPT_PATH, "script_read_failed") == SCRIPT_SHA256, "script_digest_mismatch")
    _expect(
        _identity(SCRIPT_PATH, "script_stat_failed") == script_identity,
        "script_changed_during_identity_check",
    )

    candidate_identity = _validate_regular_absolute(candidate_path, "candidate")
    _expect(
        candidate_path.suffix.casefold() in CANDIDATE_SUFFIXES,
        "candidate_suffix_rejected",
    )
    argv = (
        str(powershell_path),
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-File",
        str(SCRIPT_PATH),
        "-CandidatePath",
        str(candidate_path),
    )

    observation: InspectionObservation
    try:
        result = transport(
            argv,
            cwd=SCRIPT_PATH.parent,
            timeout_seconds=TIMEOUT_SECONDS,
            max_output_bytes=MAX_COMBINED_OUTPUT_BYTES,
        )
    except CliTransportTimeout:
        observation = InspectionObservation.timeout()
    except CliTransportError:
        observation = InspectionObservation.tool_error()
    else:
        if not isinstance(result, CliTransportResult):
            observation = InspectionObservation.tool_error()
        elif result.returncode != 0 or result.stderr:
            observation = InspectionObservation.tool_error()
        else:
            observation = _parse_status(result.stdout)

    _expect(
        _identity(powershell_path, "powershell_stat_failed") == executable_identity,
        "powershell_changed_during_transport",
    )
    _expect(
        _identity(SCRIPT_PATH, "script_stat_failed") == script_identity,
        "script_changed_during_transport",
    )
    _expect(
        _identity(candidate_path, "candidate_stat_failed") == candidate_identity,
        "candidate_changed_during_transport",
    )
    return observation
