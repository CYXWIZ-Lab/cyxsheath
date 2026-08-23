"""Validate the final fail-closed local-model load-health result."""

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


class LoadHealthResultError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LoadHealthResultError(message)


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
    expect(record["status"] == "model_activation_observed_protocol_acceptance_failed", "unsafe status")
    expect(
        record["decision_scope"] == "final_load_health_result_not_inference_or_canary_admission",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    decision = record["final_recovery_decision"]
    expect(decision["record"] == "phase6_local_model_load_health_daemon_recovery_decision.json", "decision drift")
    expect(DIGEST.fullmatch(decision["sha256"]) is not None, "malformed decision digest")
    decision_path = path.parent / decision["record"]
    expect(decision_path.is_file(), "final recovery decision missing")
    expect(hashlib.sha256(decision_path.read_bytes()).hexdigest() == decision["sha256"], "decision digest mismatch")

    attempt = record["attempt_3"]
    expect(DIGEST.fullmatch(attempt["runner_sha256"]) is not None, "malformed runner digest")
    expect(attempt["model_key"] == "qwen2.5-coder-7b-instruct", "model key drift")
    expect(attempt["load_identifier"] == "cyxsheath-qwen25-coder-7b-q4km", "identifier drift")
    expect(attempt["weight_bytes"] == 4683073536, "weight size drift")
    expect(attempt["load_command_exit_zero"] is False, "load-client failure concealed")
    expect(attempt["model_activation_observed_in_service_log"] is True, "service activation concealed")
    expect(attempt["service_log_weight_identity_matches"] is True, "service weight identity drift")
    expect(attempt["service_log_context_length_tokens"] == 8192, "context drift")
    expect(attempt["service_log_gpu_offload_layers"] == 0, "GPU offload drift")
    expect(attempt["service_log_unload_observed"] is True, "service unload missing")
    expect(attempt["exact_post_load_inventory_captured"] is False, "inventory overclaim")
    expect(attempt["observation_samples"] == 13, "observation count drift")
    expect(attempt["required_observation_samples"] == 15, "observation requirement weakened")
    for key in ("inference_request_count", "http_server_start_count", "cyxcode_invocation_count", "docker_container_count"):
        expect(attempt[key] == 0, f"unexpected invocation: {key}")

    resources = record["observed_resources"]
    expect(resources["minimum_available_memory_bytes"] >= resources["minimum_required_available_memory_bytes"], "memory floor failed")
    expect(resources["maximum_available_memory_drop_bytes"] <= resources["allowed_available_memory_drop_bytes"], "memory drop failed")
    expect(resources["peak_activation_tree_private_bytes"] <= resources["allowed_activation_tree_private_bytes"], "private memory failed")
    expect(resources["peak_activation_tree_working_set_bytes"] <= resources["allowed_activation_tree_working_set_bytes"], "working set failed")
    expect(resources["maximum_gpu_used_memory_delta_mib"] <= resources["allowed_gpu_used_memory_delta_mib"], "GPU delta failed")
    expect(resources["http_listener_observed"] is False, "HTTP listener observed")
    expect(resources["all_observed_resource_ceilings_passed"] is True, "resource result overclaim")

    drift = record["runtime_drift"]
    expect(drift["approved_engine_package"].endswith("2.28.2"), "approved engine drift")
    expect(drift["active_engine_preference"].endswith("2.29.1"), "active engine drift")
    expect(DIGEST.fullmatch(drift["active_preference_file_sha256"]) is not None, "malformed preference digest")
    expect(drift["active_engine_file_count"] == 20, "active engine inventory drift")
    expect(drift["engine_identity_matches_decision"] is False, "engine drift concealed")
    expect(drift["engine_change_authorized"] is False, "engine change retroactively authorized")
    expect(drift["treatment"] == "protocol_failure_requires_new_runtime_identity_decision", "engine treatment drift")

    cli = record["cli_lifecycle_failure"]
    expect(cli["classification"] == "lms_self_extraction_lock_after_service_side_load", "CLI failure drift")
    expect(cli["locked_component"] == "lms.exe", "locked component drift")
    expect(cli["error_family"] == "EPERM_operation_not_permitted_unlink", "CLI error drift")
    expect(cli["recorded_retry_count"] == 5, "CLI retry count drift")
    for key in ("load_client_exit_zero", "unload_client_exit_zero"):
        expect(cli[key] is False, f"CLI exit overclaim: {key}")
    for key in ("service_side_load_observed", "service_side_unload_observed"):
        expect(cli[key] is True, f"service event missing: {key}")

    cleanup = record["cleanup"]
    for key in (
        "loaded_inventory_empty_after_unload",
        "graceful_service_stop_attempted",
        "activation_processes_absent_after",
        "port_1234_listener_absent_after",
        "partial_weight_absent_after",
        "raw_cli_output_deleted",
    ):
        expect(cleanup[key] is True, f"cleanup failed: {key}")
    expect(cleanup["forced_cleanup_required"] is False, "forced cleanup overclaim")

    logs = record["local_log_evidence"]
    for key in ("server_log_sha256_at_inspection", "application_log_sha256_at_inspection"):
        expect(DIGEST.fullmatch(logs[key]) is not None, f"malformed log digest: {key}")
    expect(logs["raw_log_content_in_curated_evidence"] is False, "raw local log retained")

    acceptance = record["acceptance"]
    for key in ("model_activation_observed", "resource_gate_passed", "cleanup_gate_passed"):
        expect(acceptance[key] is True, f"observed pass missing: {key}")
    for key in (
        "load_command_exit_gate_passed",
        "exact_loaded_inventory_gate_passed",
        "observation_window_gate_passed",
        "approved_engine_identity_gate_passed",
        "load_health_gate_passed",
        "scientific_model_health_conclusion_allowed",
    ):
        expect(acceptance[key] is False, f"protocol acceptance overclaim: {key}")

    gate = record["execution_gate"]
    for key in (
        "automatic_retry_authorized",
        "synthetic_canary_authorized",
        "authenticated_http_server_authorized",
        "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"] == "make_explicit_engine_drift_and_cli_lifecycle_design_decision_before_further_activation",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, LoadHealthResultError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(
        "VALID: activation=observed; resources=passed; cleanup=passed; "
        "engine=drifted; protocol=failed; retry=blocked; canary=blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
