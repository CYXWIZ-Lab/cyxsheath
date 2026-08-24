"""Validate the synchronous CLI-exit transport and help-probe decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN = {
    "hostname",
    "machine_id",
    "serial_number",
    "username",
    "resolved_ip",
    "credential",
    "api_token",
    "problem_statement",
    "raw_prompt",
    "raw_response",
    "patch",
    "test_patch",
    "eval_script",
}


class CliExitTransportDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise CliExitTransportDecisionError(message)


def check_forbidden(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN & set(value)
        expect(not found, f"{where}: forbidden keys {sorted(found)}")
        for key, child in value.items():
            check_forbidden(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_forbidden(child, f"{where}[{index}]")


def expect_digest(value: object, name: str) -> None:
    expect(isinstance(value, str) and DIGEST.fullmatch(value) is not None, f"malformed digest: {name}")


def expect_file_digest(base: Path, relative: str, expected: str, label: str) -> None:
    expect_digest(expected, label)
    path = (base / relative).resolve()
    expect(path.is_file(), f"{label} file missing")
    expect(hashlib.sha256(path.read_bytes()).hexdigest() == expected, f"{label} digest mismatch")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"] == "synchronous_transport_verified_cli_help_probe_authorized_once",
        "unsafe status",
    )
    expect(
        record["decision_scope"] == "cli_exit_transport_and_identity_probe_not_runtime_or_model_activation",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    failed = record["failed_recovery_result"]
    expect(failed["record"] == "phase6_local_engine_cli_recovery_result.json", "failed-result record drift")
    expect_file_digest(path.parent, failed["record"], failed["sha256"], "failed result")
    expect(failed["status"] == "daemon_started_model_load_not_attempted_protocol_failed", "failed status drift")

    structure = record["structural_decision"]
    expect(structure["new_module"] == "../cli_transport.py", "transport module drift")
    expect(structure["new_dependency_count"] == 0, "dependency growth admitted")
    expect(structure["core_sheath_change_required"] is False, "core expansion admitted")

    identity = record["transport_identity"]
    expect(identity["module"] == "../cli_transport.py", "module identity drift")
    expect(identity["bytes"] == 3114, "module size drift")
    expect_file_digest(path.parent, identity["module"], identity["sha256"], "transport module")
    expect(identity["test_module"] == "../test_cli_transport.py", "test identity drift")
    expect(identity["test_bytes"] == 2935, "test size drift")
    expect_file_digest(path.parent, identity["test_module"], identity["test_sha256"], "transport tests")

    contract = record["transport_contract"]
    expect(contract["implementation"] == "python_standard_library_subprocess_run", "implementation drift")
    for key in (
        "absolute_existing_executable_required",
        "absolute_existing_working_directory_required",
        "numeric_returncode_required",
        "nonzero_returncode_is_returned_to_caller",
        "timeout_required_positive_finite",
        "combined_output_retention_limit_required",
        "windows_no_console_flag",
    ):
        expect(contract[key] is True, f"transport contract weakened: {key}")
    for key in ("shell", "environment_override_supported"):
        expect(contract[key] is False, f"transport surface widened: {key}")
    expect(contract["stdin"] == "null_device", "stdin drift")

    failure = record["failure_contract"]
    expect(failure["invalid_input"] == "fail_before_process_start", "invalid-input behavior drift")
    expect(
        failure["timeout"] == "direct_child_terminated_by_subprocess_run_and_no_exit_claim_returned",
        "timeout behavior drift",
    )
    expect(failure["nonzero_exit"] == "numeric_result_returned_and_caller_must_fail_closed", "exit behavior drift")

    limit = record["known_limit"]
    expect(limit["output_limit_kind"] == "post_completion_combined_retention_acceptance_bound", "limit drift")
    expect(limit["streaming_memory_limit_enforced"] is False, "streaming bound overclaim")
    expect(limit["general_purpose_process_runner_claimed"] is False, "generality overclaim")

    fixture = record["fixture_evidence"]
    for version in ("python_3_12", "python_3_14"):
        expect(fixture[version] == {"tests_run": 8, "tests_passed": 8}, f"fixture evidence drift: {version}")
    expect(len(fixture["verified_behaviors"]) == 8, "fixture behavior set drift")
    expect(fixture["lm_studio_invocation_count"] == 0, "LM Studio fixture invocation admitted")

    probe = record["authorized_cli_probe"]
    expect(probe["maximum_attempts"] == 1, "probe attempts widened")
    expect(probe["canonical_cli_relative_path"] == "lmstudio_home/bin/lms.exe", "canonical path drift")
    expect(probe["canonical_cli_bytes"] == 120772792, "canonical CLI size drift")
    expect_digest(probe["canonical_cli_sha256"], "canonical CLI")
    expect(
        probe["temporary_cli_relative_path"] == ".replay_cache/local_cli_transport_probe/lms.exe",
        "temporary path drift",
    )
    expect(probe["temporary_copy_count"] == 1, "temporary copies widened")
    expect(probe["command"] == "temporary_lms_exe --help", "probe command widened")
    expect(probe["timeout_seconds"] == 30, "probe timeout widened")
    expect(probe["maximum_combined_output_bytes"] == 1048576, "probe output bound widened")
    expect(probe["required_exit_code"] == 0, "probe exit gate weakened")
    for key in (
        "nonempty_stdout_required",
        "temporary_cli_deleted_after",
        "clean_process_and_port_baseline_required",
    ):
        expect(probe[key] is True, f"probe gate weakened: {key}")
    for key in ("raw_output_retained", "new_lm_studio_process_after_allowed", "port_1234_listener_allowed"):
        expect(probe[key] is False, f"probe boundary widened: {key}")

    boundary = record["security_and_research_boundary"]
    for key, value in boundary.items():
        if key.endswith("_count"):
            expect(value == 0, f"runtime operation admitted: {key}")
        else:
            expect(value is False, f"research boundary widened: {key}")

    gate = record["execution_gate"]
    expect(gate["cli_help_probe_authorized_once"] is True, "CLI probe not authorized")
    for key in (
        "load_health_retry_authorized",
        "synthetic_canary_authorized",
        "authenticated_http_server_authorized",
        "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"]
        == "execute_exact_cli_help_probe_once_and_record_numeric_exit_cleanup_and_identity_result",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, CliExitTransportDecisionError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(
        "VALID: transport=synchronous-subprocess; fixtures=16/16; "
        "cli_help_probe=authorized-once; daemon=blocked; model_load=blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
