"""Validate the fail-closed engine/CLI recovery result."""

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


class EngineCliRecoveryResultError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise EngineCliRecoveryResultError(message)


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


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(record["status"] == "daemon_started_model_load_not_attempted_protocol_failed", "unsafe status")
    expect(
        record["decision_scope"] == "final_one_shot_engine_cli_recovery_result_not_retry_or_inference_admission",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    decision = record["recovery_decision"]
    expect(decision["record"] == "phase6_local_engine_cli_recovery_decision.json", "decision record drift")
    expect_digest(decision["sha256"], "recovery decision")
    decision_path = path.parent / decision["record"]
    expect(decision_path.is_file(), "recovery decision missing")
    expect(hashlib.sha256(decision_path.read_bytes()).hexdigest() == decision["sha256"], "decision digest mismatch")

    prelaunch = record["prelaunch_event"]
    expect(
        prelaunch["classification"] == "host_powershell_execution_policy_blocked_before_runner_start",
        "prelaunch classification drift",
    )
    for key in ("runner_started", "daemon_or_model_process_started", "temporary_cli_staged", "counts_as_authorized_attempt"):
        expect(prelaunch[key] is False, f"prelaunch overclaim: {key}")

    attempt = record["authorized_attempt"]
    expect_digest(attempt["runner_sha256"], "runner")
    expect(attempt["runner_bytes"] == 22036, "runner size drift")
    expect(attempt["temporary_cli_staged"] is True, "temporary CLI staging concealed")
    expect(attempt["daemon_service_root_observed"] is True, "daemon service root concealed")
    expect(attempt["daemon_client_numeric_exit_captured"] is False, "daemon exit overclaim")
    expect(attempt["daemon_client_exit_code"] is None, "daemon exit value invented")
    expect(attempt["model_load_command_invocation_count"] == 0, "model load invocation overclaim")
    expect(attempt["model_activation_observed"] is False, "model activation overclaim")
    for key in (
        "load_observation_samples",
        "post_load_observation_samples",
        "inference_request_count",
        "http_server_start_count",
        "cyxcode_invocation_count",
        "docker_container_count",
    ):
        expect(attempt[key] == 0, f"unexpected execution count: {key}")

    identity = record["pinned_identity_outcome"]
    expect(identity["engine_package"] == "llama.cpp-win-x86_64-nvidia-cuda-avx2-2.29.1", "engine drift")
    for key in ("engine_inventory_sha256", "engine_preference_sha256", "cli_sha256"):
        expect_digest(identity[key], key)
    for key in (
        "engine_identity_matches_after",
        "engine_preference_matches_after",
        "canonical_cli_matches_after",
        "temporary_cli_deleted_after",
    ):
        expect(identity[key] is True, f"identity or cleanup failure concealed: {key}")
    expect(identity["cli_version"] == "1.3.3", "CLI version drift")

    lifecycle = record["cli_lifecycle_outcome"]
    expect(lifecycle["temporary_copy_mechanism_executed"] is True, "temporary-copy execution concealed")
    expect(lifecycle["bounded_application_log_eperm_event_count"] == 0, "EPERM count drift")
    expect(lifecycle["bounded_application_log_failed_extraction_event_count"] == 0, "extraction count drift")
    expect(lifecycle["extraction_lock_resolution_conclusion_allowed"] is False, "lock resolution overclaim")
    expect(lifecycle["numeric_exit_evidence_missing"] is True, "missing exit evidence concealed")
    expect(
        lifecycle["treatment"] == "missing_numeric_daemon_exit_fails_closed_before_model_load",
        "CLI treatment drift",
    )

    resources = record["resource_observation"]
    expect(resources["preload_available_memory_bytes"] > 0, "preload memory missing")
    expect(resources["post_cleanup_available_memory_bytes"] > 0, "post-cleanup memory missing")
    expect(resources["activation_resource_samples"] == 0, "activation samples invented")
    expect(resources["resource_gate_conclusion_allowed"] is False, "resource conclusion overclaim")

    cleanup = record["cleanup"]
    expect(cleanup["forced_cleanup_required"] is True, "forced cleanup concealed")
    for key in (
        "activation_processes_absent_after",
        "port_1234_listener_absent_after",
        "partial_weight_absent_after",
        "temporary_cli_absent_after",
        "raw_runner_output_absent_after",
        "loaded_inventory_empty_after",
        "safety_cleanup_complete",
    ):
        expect(cleanup[key] is True, f"cleanup failure: {key}")
    expect(cleanup["protocol_cleanup_gate_passed"] is False, "protocol cleanup overclaim")

    local = record["local_evidence"]
    for key in ("ignored_result_sha256", "application_log_sha256_at_inspection"):
        expect_digest(local[key], key)
    expect(local["bounded_window_line_count"] == 11, "log window drift")
    expect(local["raw_log_or_cli_content_in_curated_evidence"] is False, "raw local evidence retained")

    acceptance = record["acceptance"]
    for key in ("engine_identity_gate_passed", "temporary_cli_integrity_gate_passed", "cleanup_safety_outcome_passed"):
        expect(acceptance[key] is True, f"observed pass missing: {key}")
    for key in (
        "daemon_client_exit_gate_passed",
        "model_load_gate_executed",
        "exact_loaded_inventory_gate_passed",
        "observation_window_gate_passed",
        "resource_gate_passed",
        "protocol_cleanup_gate_passed",
        "load_health_gate_passed",
        "model_health_conclusion_allowed",
    ):
        expect(acceptance[key] is False, f"acceptance overclaim: {key}")

    gate = record["execution_gate"]
    expect(gate["authorized_attempt_consumed"] is True, "attempt consumption concealed")
    for key in (
        "automatic_retry_authorized",
        "synthetic_canary_authorized",
        "authenticated_http_server_authorized",
        "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"]
        == "make_explicit_cli_exit_observation_design_decision_before_any_further_runtime_execution",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, EngineCliRecoveryResultError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(
        "VALID: daemon=observed; numeric_exit=missing; model_load=not_attempted; "
        "cleanup=complete; load_health=failed; retry=blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
