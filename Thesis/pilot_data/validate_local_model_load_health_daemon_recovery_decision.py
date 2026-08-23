"""Validate the daemon-lifecycle failure record and final bounded retry."""

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


class DaemonRecoveryDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise DaemonRecoveryDecisionError(message)


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
    expect(record["status"] == "daemon_lifecycle_harness_failure_final_retry_authorized_once", "unsafe status")
    expect(
        record["decision_scope"] == "capture_spawned_daemon_readiness_and_cleanup_before_model_load",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    prior = record["prior_recovery_decision"]
    expect(prior["record"] == "phase6_local_model_load_health_recovery_decision.json", "prior record drift")
    expect(DIGEST.fullmatch(prior["sha256"]) is not None, "malformed prior digest")
    prior_path = path.parent / prior["record"]
    expect(prior_path.is_file(), "prior recovery decision missing")
    expect(hashlib.sha256(prior_path.read_bytes()).hexdigest() == prior["sha256"], "prior digest mismatch")
    expect(prior["status"] == "preload_measurement_failure_retry_authorized_once", "prior status drift")

    attempt = record["attempt_2"]
    expect(DIGEST.fullmatch(attempt["runner_sha256"]) is not None, "malformed attempt runner digest")
    expect(attempt["status"] == "daemon_cli_nonzero_after_service_spawn", "attempt status drift")
    expect(
        attempt["classification"] == "daemon_lifecycle_harness_failure_not_model_health_result",
        "model-health overclaim",
    )
    expect(attempt["gpu_measurement_passed"] is True, "GPU correction did not pass")
    expect(attempt["daemon_cli_exit_zero"] is False, "daemon CLI result rewritten")
    expect(attempt["daemon_service_process_tree_created"] is True, "service spawn concealed")
    expect(attempt["daemon_process_count"] == 5, "daemon process inventory drift")
    for key in ("load_command_started", "model_loaded"):
        expect(attempt[key] is False, f"model activation overclaim: {key}")
    for key in (
        "observation_samples",
        "inference_request_count",
        "http_server_start_count",
        "cyxcode_invocation_count",
        "docker_container_count",
    ):
        expect(attempt[key] == 0, f"attempt count drift: {key}")
    expect(attempt["port_1234_listener_present"] is False, "HTTP listener overclaim")
    expect(attempt["automatic_cleanup_passed"] is False, "automatic cleanup rewritten")
    expect(attempt["raw_cli_output_deleted"] is True, "raw CLI output retained")

    cleanup = record["manual_cleanup"]
    expect(cleanup["scope"] == "exact_spawned_service_root_and_four_children", "cleanup scope drift")
    expect(cleanup["graceful_root_stop_attempted"] is True, "graceful cleanup missing")
    expect(cleanup["forced_cleanup_required"] is False, "force-cleanup overclaim")
    for key in ("activation_processes_absent_after", "port_1234_listener_absent_after", "partial_weight_absent_after"):
        expect(cleanup[key] is True, f"manual cleanup failed: {key}")

    correction = record["correction"]
    expect(DIGEST.fullmatch(correction["corrected_runner_sha256"]) is not None, "malformed corrected runner digest")
    expect(correction["capture_exact_service_root_after_daemon_command_regardless_of_exit"] is True, "root capture missing")
    expect(correction["nonzero_daemon_cli_exit_alone_proves_readiness"] is False, "nonzero exit treated as readiness")
    expect(correction["readiness_requires_exact_service_root_count"] == 1, "root-count gate drift")
    for key in (
        "readiness_requires_empty_loaded_inventory",
        "readiness_requires_port_1234_absent",
        "cleanup_captures_exact_service_root_on_all_exit_paths",
        "all_original_model_resource_and_security_settings_unchanged",
    ):
        expect(correction[key] is True, f"correction weakened: {key}")
    expect(correction["new_dependency_added"] is False, "dependency added")

    authorization = record["authorization"]
    expect(
        authorization["reason"] == "two_attempts_ended_before_load_and_exact_cleanup_is_now_fail_safe",
        "authorization reason drift",
    )
    expect(authorization["maximum_final_recovery_attempts"] == 1, "final attempts widened")
    expect(authorization["executed_final_recovery_attempts_at_decision"] == 0, "prior final attempt overclaim")
    for key in (
        "different_model_or_load_settings_authorized",
        "http_server_start_authorized",
        "inference_request_authorized",
        "synthetic_canary_authorized",
        "benchmark_input_authorized",
    ):
        expect(authorization[key] is False, f"authorization widened: {key}")

    gate = record["execution_gate"]
    expect(gate["final_recovery_load_health_check_authorized_once"] is True, "final recovery not authorized")
    expect(gate["original_contract_controls"] is True, "original contract detached")
    expect(gate["no_further_automatic_retry"] is True, "automatic retries admitted")
    expect(
        gate["next_action"] == "execute_final_corrected_load_only_monitor_once_and_record_result",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, DaemonRecoveryDecisionError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(
        f"VALID: attempt2={record['attempt_2']['status']}; model_load=false; "
        "final_recovery=1; inference=blocked; server=blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
