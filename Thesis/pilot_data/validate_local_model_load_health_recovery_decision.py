"""Validate the fail-closed attempt-1 record and bounded load-health retry."""

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


class LoadHealthRecoveryDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LoadHealthRecoveryDecisionError(message)


def check_forbidden(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN & set(value)
        expect(not found, f"{where}: forbidden keys {sorted(found)}")
        for key, child in value.items():
            check_forbidden(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_forbidden(child, f"{where}[{index}]")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(record["status"] == "preload_measurement_failure_retry_authorized_once", "unsafe status")
    expect(
        record["decision_scope"] == "recover_transient_gpu_measurement_before_any_model_activation",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    original = record["original_decision"]
    expect(original["record"] == "phase6_local_model_load_health_decision.json", "original decision drift")
    expect(DIGEST.fullmatch(original["sha256"]) is not None, "malformed original decision digest")
    original_path = path.parent / original["record"]
    expect(original_path.is_file(), "original decision missing")
    expect(hashlib.sha256(original_path.read_bytes()).hexdigest() == original["sha256"], "original decision digest mismatch")
    expect(original["status"] == "load_only_health_check_authorized_once", "original status drift")

    attempt = record["attempt_1"]
    for key in ("started_at", "completed_at"):
        expect(attempt[key].endswith("Z"), f"attempt timestamp not UTC: {key}")
    expect(DIGEST.fullmatch(attempt["runner_sha256"]) is not None, "malformed attempt runner digest")
    expect(attempt["status"] == "preload_gpu_measurement_failed", "attempt status overclaim")
    expect(
        attempt["classification"] == "measurement_harness_failure_not_model_or_runtime_failure",
        "attempt classification drift",
    )
    for key in ("daemon_start_attempted", "load_command_started", "model_loaded"):
        expect(attempt[key] is False, f"attempt activation overclaim: {key}")
    for key in (
        "observation_samples",
        "inference_request_count",
        "http_server_start_count",
        "cyxcode_invocation_count",
        "docker_container_count",
    ):
        expect(attempt[key] == 0, f"attempt count drift: {key}")
    expect(attempt["failure_code"] == "gpu_measurement_failed", "attempt failure drift")
    for key in (
        "activation_processes_absent_after",
        "port_1234_listener_absent_after",
        "partial_weight_absent_after",
        "raw_cli_output_deleted",
    ):
        expect(attempt[key] is True, f"attempt cleanup failed: {key}")

    diagnostic = record["diagnostic"]
    expect(diagnostic["method"] == "read_only_nvidia_smi_repetition_without_runtime_start", "diagnostic drift")
    expect(diagnostic["samples"] == 2 and diagnostic["successful_samples"] == 2, "diagnostic sample drift")
    expect(diagnostic["reported_used_memory_mib"] == [0, 0], "diagnostic result drift")
    expect(
        diagnostic["interpretation"] == "transient_first_sample_failure_reproducibility_not_established",
        "diagnostic certainty overclaim",
    )

    retry = record["retry_delta"]
    expect(DIGEST.fullmatch(retry["corrected_runner_sha256"]) is not None, "malformed corrected runner digest")
    expect(retry["gpu_executable_resolution"] == "exact_command_source_before_measurement", "GPU command drift")
    expect(retry["gpu_measurement_attempts_per_sample"] == 3, "measurement retries widened")
    expect(retry["gpu_measurement_retry_delay_seconds"] == 1, "measurement delay drift")
    expect(retry["require_zero_exit_and_integer_parse"] is True, "GPU parse gate weakened")
    expect(retry["all_original_model_and_resource_settings_unchanged"] is True, "original contract changed")
    expect(retry["new_dependency_added"] is False, "dependency added")
    expect(retry["fallback_without_gpu_measurement_allowed"] is False, "missing GPU measurement admitted")

    authorization = record["authorization"]
    expect(
        authorization["reason"] == "first_attempt_ended_before_daemon_or_load_and_cleanup_passed",
        "retry reason drift",
    )
    expect(authorization["maximum_recovery_attempts"] == 1, "recovery attempts widened")
    expect(authorization["executed_recovery_attempts_at_decision"] == 0, "prior recovery overclaim")
    for key in (
        "different_model_or_load_settings_authorized",
        "http_server_start_authorized",
        "inference_request_authorized",
        "synthetic_canary_authorized",
        "benchmark_input_authorized",
    ):
        expect(authorization[key] is False, f"authorization widened: {key}")

    gate = record["execution_gate"]
    expect(gate["recovery_load_health_check_authorized_once"] is True, "recovery execution not authorized")
    expect(gate["original_contract_controls"] is True, "original contract detached")
    expect(gate["fail_closed_if_gpu_measurement_still_missing"] is True, "GPU fail-closed removed")
    expect(
        gate["next_action"] == "execute_corrected_load_only_monitor_once_and_record_result",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, LoadHealthRecoveryDecisionError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(
        f"VALID: attempt1={record['attempt_1']['status']}; model_load=false; "
        "recovery_attempts=1; inference=blocked; server=blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
