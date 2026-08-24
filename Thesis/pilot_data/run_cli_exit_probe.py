"""Run the one authorized LM Studio CLI help probe without starting a daemon."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
from typing import Any

from cli_transport import CliTransportError, CliTransportTimeout, run_cli
from validate_cli_exit_transport_decision import validate as validate_decision


ROOT = Path(__file__).resolve().parents[2]
DECISION = Path(__file__).parent / "review_evidence" / "phase6_cli_exit_transport_decision.json"
CACHE = ROOT / ".replay_cache" / "local_cli_transport_probe"
OUTPUT = CACHE / "result.json"
TEMPORARY_CLI = CACHE / "lms.exe"
CLI_BYTES = 120772792
CLI_SHA256 = "976d4389f97b2cf95b38a4eb673855d8a846f2db21a20eb4fe5e79f7179722f5"
PROCESS_NAMES = {"lm studio.exe", "lms.exe"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_cli(path: Path, label: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"{label}_missing")
    if path.stat().st_size != CLI_BYTES:
        raise RuntimeError(f"{label}_size_mismatch")
    if file_sha256(path) != CLI_SHA256:
        raise RuntimeError(f"{label}_digest_mismatch")


def matching_process_ids() -> tuple[int, ...]:
    completed = subprocess.run(
        ("tasklist.exe", "/FO", "CSV", "/NH"),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
        timeout=15,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        raise RuntimeError("process_inventory_failed")
    rows = csv.reader(io.StringIO(completed.stdout.decode("utf-8", errors="replace")))
    found: list[int] = []
    for row in rows:
        if len(row) < 2 or row[0].strip().lower() not in PROCESS_NAMES:
            continue
        try:
            found.append(int(row[1]))
        except ValueError as error:
            raise RuntimeError("process_inventory_pid_invalid") from error
    return tuple(sorted(found))


def port_1234_listening() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(0.25)
        return client.connect_ex(("127.0.0.1", 1234)) == 0


def terminate_probe_processes(process_ids: tuple[int, ...]) -> bool:
    success = True
    for process_id in process_ids:
        completed = subprocess.run(
            ("taskkill.exe", "/PID", str(process_id), "/T", "/F"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            check=False,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        success = success and completed.returncode == 0
    return success


def write_result(record: dict[str, Any]) -> None:
    OUTPUT.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    decision = validate_decision(DECISION)
    if not decision["execution_gate"]["cli_help_probe_authorized_once"]:
        raise SystemExit("CLI help probe is not authorized")

    CACHE.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    baseline_processes: tuple[int, ...] = ()
    post_processes: tuple[int, ...] = ()
    baseline_port = False
    post_port = False
    forced_cleanup_required = False
    forced_cleanup_succeeded = True
    temporary_copy_staged = False
    temporary_copy_deleted = False
    canonical_identity_after = False
    exit_code: int | None = None
    stdout_bytes = 0
    stderr_bytes = 0
    stdout_sha256: str | None = None
    stderr_sha256: str | None = None
    stdout_nonempty = False
    elapsed_milliseconds: int | None = None

    home = Path(os.environ["USERPROFILE"])
    canonical_cli = home / ".lmstudio" / "bin" / "lms.exe"

    try:
        if OUTPUT.exists():
            raise RuntimeError("prior_probe_result_present")
        if TEMPORARY_CLI.exists():
            raise RuntimeError("temporary_cli_present_at_baseline")
        baseline_processes = matching_process_ids()
        if baseline_processes:
            raise RuntimeError("probe_process_present_at_baseline")
        baseline_port = port_1234_listening()
        if baseline_port:
            raise RuntimeError("port_1234_present_at_baseline")
        assert_cli(canonical_cli, "canonical_cli")

        shutil.copyfile(canonical_cli, TEMPORARY_CLI)
        temporary_copy_staged = True
        assert_cli(TEMPORARY_CLI, "temporary_cli")

        result = run_cli(
            (str(TEMPORARY_CLI.resolve()), "--help"),
            cwd=ROOT,
            timeout_seconds=30,
            max_output_bytes=1048576,
        )
        exit_code = result.returncode
        stdout_bytes = len(result.stdout)
        stderr_bytes = len(result.stderr)
        stdout_sha256 = hashlib.sha256(result.stdout).hexdigest()
        stderr_sha256 = hashlib.sha256(result.stderr).hexdigest()
        stdout_nonempty = bool(result.stdout)
        elapsed_milliseconds = result.elapsed_milliseconds
        if exit_code != 0:
            failures.append("help_probe_exit_nonzero")
        if not stdout_nonempty:
            failures.append("help_probe_stdout_empty")
    except CliTransportTimeout:
        failures.append("help_probe_timeout")
    except CliTransportError:
        failures.append("help_probe_transport_error")
    except (OSError, RuntimeError, KeyError, json.JSONDecodeError) as error:
        failures.append(str(error))
    finally:
        try:
            assert_cli(canonical_cli, "canonical_cli_after")
            canonical_identity_after = True
        except (OSError, RuntimeError):
            failures.append("canonical_cli_identity_changed_after")

        TEMPORARY_CLI.unlink(missing_ok=True)
        temporary_copy_deleted = not TEMPORARY_CLI.exists()
        if not temporary_copy_deleted:
            failures.append("temporary_cli_retained")

        try:
            post_processes = matching_process_ids()
            if post_processes:
                forced_cleanup_required = True
                forced_cleanup_succeeded = terminate_probe_processes(post_processes)
                if not forced_cleanup_succeeded:
                    failures.append("probe_process_cleanup_failed")
            remaining = matching_process_ids()
            if remaining:
                failures.append("probe_process_retained")
            post_processes = remaining
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            failures.append("post_probe_process_inventory_failed")
        post_port = port_1234_listening()
        if post_port:
            failures.append("port_1234_listener_after_probe")

        accepted = (
            not failures
            and temporary_copy_staged
            and exit_code == 0
            and stdout_nonempty
            and stdout_bytes + stderr_bytes <= 1048576
            and not baseline_processes
            and not baseline_port
            and not forced_cleanup_required
            and not post_processes
            and not post_port
            and canonical_identity_after
            and temporary_copy_deleted
        )
        record: dict[str, Any] = {
            "schema_version": "1.0.0-local",
            "status": "cli_help_probe_passed" if accepted else "cli_help_probe_failed",
            "decision_record": DECISION.name,
            "transport_module_sha256": file_sha256(Path(__file__).parent / "cli_transport.py"),
            "runner_sha256": file_sha256(Path(__file__)),
            "cli": {
                "version": "1.3.3",
                "bytes": CLI_BYTES,
                "sha256": CLI_SHA256,
                "temporary_copy_staged": temporary_copy_staged,
                "command": "temporary_lms_exe --help",
                "numeric_exit_code": exit_code,
                "elapsed_milliseconds": elapsed_milliseconds,
            },
            "output": {
                "stdout_bytes": stdout_bytes,
                "stderr_bytes": stderr_bytes,
                "stdout_sha256": stdout_sha256,
                "stderr_sha256": stderr_sha256,
                "stdout_nonempty": stdout_nonempty,
                "raw_output_retained": False,
            },
            "runtime_boundary": {
                "baseline_process_count": len(baseline_processes),
                "baseline_port_1234_listener": baseline_port,
                "daemon_command_count": 0,
                "model_load_command_count": 0,
                "inference_request_count": 0,
                "http_server_start_count": 0,
                "cyxcode_invocation_count": 0,
                "docker_container_count": 0,
                "post_process_count": len(post_processes),
                "post_port_1234_listener": post_port,
            },
            "cleanup": {
                "forced_cleanup_required": forced_cleanup_required,
                "forced_cleanup_succeeded": forced_cleanup_succeeded,
                "canonical_cli_identity_matches_after": canonical_identity_after,
                "temporary_cli_deleted": temporary_copy_deleted,
            },
            "failures": failures,
            "accepted": accepted,
        }
        write_result(record)
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
