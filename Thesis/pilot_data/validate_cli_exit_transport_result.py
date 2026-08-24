"""Validate the successful numeric-exit CLI help probe result."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
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


class CliExitTransportResultError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise CliExitTransportResultError(message)


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
    target = (base / relative).resolve()
    expect(target.is_file(), f"{label} missing")
    expect(hashlib.sha256(target.read_bytes()).hexdigest() == expected, f"{label} digest mismatch")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(record["status"] == "cli_help_probe_passed_numeric_exit_observed", "unsafe status")
    expect(
        record["decision_scope"] == "final_cli_help_probe_result_not_daemon_model_or_load_health_authorization",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    decision = record["transport_decision"]
    expect(decision["record"] == "phase6_cli_exit_transport_decision.json", "decision record drift")
    expect_file_digest(path.parent, decision["record"], decision["sha256"], "transport decision")
    expect(
        decision["status"] == "synchronous_transport_verified_cli_help_probe_authorized_once",
        "decision status drift",
    )

    identity = record["execution_identity"]
    expect(identity["runner"] == "../run_cli_exit_probe.py", "runner path drift")
    expect(identity["runner_bytes"] == 9639, "runner size drift")
    expect_file_digest(path.parent, identity["runner"], identity["runner_sha256"], "probe runner")
    expect(identity["transport"] == "../cli_transport.py", "transport path drift")
    expect_file_digest(path.parent, identity["transport"], identity["transport_sha256"], "CLI transport")
    expect_digest(identity["ignored_result_sha256"], "ignored result")

    probe = record["cli_probe"]
    expect(probe["version"] == "1.3.3", "CLI version drift")
    expect(probe["bytes"] == 120772792, "CLI size drift")
    expect_digest(probe["sha256"], "CLI")
    expect(probe["temporary_copy_staged"] is True, "temporary staging concealed")
    expect(probe["command"] == "temporary_lms_exe --help", "probe command drift")
    expect(probe["timeout_seconds"] == 30, "timeout drift")
    expect(probe["maximum_combined_output_bytes"] == 1048576, "output bound drift")
    expect(probe["numeric_exit_code"] == 0, "numeric exit overclaim")
    expect(0 <= probe["elapsed_milliseconds"] <= 30000, "elapsed time outside bound")

    output = record["output_evidence"]
    expect(output["stdout_bytes"] == 1207, "stdout size drift")
    expect(output["stderr_bytes"] == 0, "stderr size drift")
    expect(output["combined_bytes"] == output["stdout_bytes"] + output["stderr_bytes"], "combined size mismatch")
    expect(output["combined_bytes"] <= probe["maximum_combined_output_bytes"], "output bound failed")
    expect_digest(output["stdout_sha256"], "stdout")
    expect(output["stderr_sha256"] == EMPTY_SHA256, "stderr digest drift")
    expect(output["stdout_nonempty"] is True, "stdout overclaim")
    expect(output["raw_output_retained"] is False, "raw output retained")

    boundary = record["runtime_boundary"]
    for key in (
        "baseline_process_count",
        "daemon_command_count",
        "model_load_command_count",
        "inference_request_count",
        "http_server_start_count",
        "cyxcode_invocation_count",
        "docker_container_count",
        "post_process_count",
    ):
        expect(boundary[key] == 0, f"runtime boundary failed: {key}")
    for key in ("baseline_port_1234_listener", "post_port_1234_listener"):
        expect(boundary[key] is False, f"port boundary failed: {key}")

    cleanup = record["cleanup"]
    expect(cleanup["forced_cleanup_required"] is False, "forced cleanup concealed")
    for key in (
        "canonical_cli_identity_matches_after",
        "temporary_cli_deleted",
        "raw_output_absent",
        "cleanup_gate_passed",
    ):
        expect(cleanup[key] is True, f"cleanup failed: {key}")

    acceptance = record["acceptance"]
    for key in (
        "pinned_cli_identity_gate_passed",
        "numeric_zero_exit_gate_passed",
        "bounded_output_gate_passed",
        "clean_process_and_port_gate_passed",
        "temporary_cleanup_gate_passed",
        "cli_transport_probe_passed",
    ):
        expect(acceptance[key] is True, f"observed pass missing: {key}")
    for key in (
        "daemon_health_conclusion_allowed",
        "model_health_conclusion_allowed",
        "model_quality_conclusion_allowed",
        "load_health_gate_passed",
    ):
        expect(acceptance[key] is False, f"acceptance overclaim: {key}")

    gate = record["execution_gate"]
    expect(gate["cli_help_probe_consumed"] is True, "probe consumption concealed")
    for key in (
        "automatic_probe_retry_authorized",
        "load_health_retry_authorized",
        "synthetic_canary_authorized",
        "authenticated_http_server_authorized",
        "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"]
        == "make_explicit_load_health_transport_integration_decision_before_any_daemon_or_model_command",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, CliExitTransportResultError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(
        "VALID: help_exit=0; output=bounded; process=clean; cleanup=passed; "
        "daemon=blocked; model_load=blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
