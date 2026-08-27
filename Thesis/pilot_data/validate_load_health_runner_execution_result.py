"""Validate the final one-shot Phase-6 load-health runner result."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from validate_shutdown_observation_implementation_result import (
    historical_source_has_successor,
)


DIGEST = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN = {
    "hostname",
    "machine_id",
    "serial_number",
    "username",
    "credential",
    "api_token",
    "problem_statement",
    "raw_prompt",
    "raw_response",
    "patch",
    "test_patch",
    "eval_script",
}


class LoadHealthRunnerExecutionResultError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LoadHealthRunnerExecutionResultError(message)


def check_forbidden(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN & set(value)
        expect(not found, f"{where}: forbidden keys {sorted(found)}")
        for key, child in value.items():
            check_forbidden(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_forbidden(child, f"{where}[{index}]")


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"] == "model_load_and_resource_gates_observed_shutdown_acceptance_failed",
        "unsafe status",
    )
    expect(
        record["decision_scope"] == "final_one_shot_load_health_result_not_inference_or_canary_admission",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    decision = record["execution_decision"]
    expect(decision["record"] == "phase6_load_health_runner_execution_decision.json", "decision record drift")
    decision_path = path.parent / decision["record"]
    expect(file_digest(decision_path) == decision["sha256"], "execution decision digest drift")
    decision_record = json.loads(decision_path.read_text(encoding="utf-8"))
    expect(decision_record["status"] == decision["status"], "execution decision status drift")

    artifacts = record["retained_local_artifacts"]
    expect(artifacts["cache_relative_path"] == ".replay_cache/local_model_load_health_python", "cache path drift")
    expect(artifacts["runtime_result_file"] == "result.json", "result filename drift")
    expect(artifacts["execution_claim_file"] == "execution_claim.json", "claim filename drift")
    for key in ("runtime_result_sha256", "execution_claim_sha256"):
        expect(DIGEST.fullmatch(artifacts[key]) is not None, f"{key}: malformed digest")
    expect(
        artifacts["runtime_result_sha256"]
        == "1932829c7498f41bba77fbf21b840a11773d3c842a9436ca53c1e745b212540f",
        "runtime result artifact drift",
    )
    expect(
        artifacts["execution_claim_sha256"]
        == "38c916fbf4b59d2a5461a31a10eb5684e2110ee59e74bb6d498d9426671aa33f",
        "execution claim artifact drift",
    )
    expect(artifacts["claim_retained"] is True, "one-shot claim not retained")
    expect(artifacts["automatic_retry_count"] == 0, "automatic retry concealed")

    attempt = record["attempt"]
    expect(attempt["runner_exit_code"] == 1, "runner exit drift")
    expect(attempt["daemon_up_exit_code"] == 0, "daemon-up result drift")
    expect(attempt["load_exit_code"] == 0, "load result drift")
    expect(attempt["unload_exit_code"] == 0, "unload result drift")
    expect(attempt["daemon_down_exit_code"] == 1, "daemon-down result drift")
    expect(attempt["failures"] == ["daemon_down_exit_nonzero", "forced_cleanup_required"], "failure inventory drift")
    source_paths = {
        "runner_sha256": (path.parent.parent / "run_local_model_load_health.py", "../run_local_model_load_health.py"),
        "windows_adapter_sha256": (path.parent.parent / "lm_studio_windows.py", "../lm_studio_windows.py"),
        "monitored_process_sha256": (path.parent.parent / "monitored_process.py", "../monitored_process.py"),
    }
    for key, (target, relative) in source_paths.items():
        current = file_digest(target)
        if current != attempt[key]:
            expect(
                historical_source_has_successor(relative, attempt[key], current),
                f"{key}: source digest drift",
            )

    model = record["model_observation"]
    expect(model["model_key"] == "qwen2.5-coder-7b-instruct", "model key drift")
    expect(model["identifier"] == "cyxsheath-qwen25-coder-7b-q4km", "identifier drift")
    expect(model["context_length_tokens"] == 8192, "context drift")
    expect(model["gpu_offload"] == "off", "GPU offload drift")
    expect(model["loaded_identity_passed"] is True, "loaded identity overclaim")
    expect(model["loaded_inventory"] == [{
        "identifier": "cyxsheath-qwen25-coder-7b-q4km",
        "modelKey": "qwen2.5-coder-7b-instruct",
        "contextLength": 8192,
    }], "loaded inventory drift")
    expect(model["post_load_samples"] == model["required_post_load_samples"] == 15, "observation count drift")
    expect(model["http_listener_observed"] is False, "HTTP listener concealed")

    resources = record["observed_resources"]
    expect(resources["minimum_available_memory_bytes"] >= resources["minimum_required_available_memory_bytes"], "available-memory floor failed")
    expect(resources["maximum_available_memory_drop_bytes"] <= resources["allowed_available_memory_drop_bytes"], "memory-drop ceiling failed")
    expect(resources["peak_activation_tree_private_bytes"] <= resources["allowed_activation_tree_private_bytes"], "private-memory ceiling failed")
    expect(resources["peak_activation_tree_working_set_bytes"] <= resources["allowed_activation_tree_working_set_bytes"], "working-set ceiling failed")
    expect(resources["maximum_gpu_used_memory_delta_mib"] <= resources["allowed_gpu_used_memory_delta_mib"], "GPU ceiling failed")
    expect(resources["post_load_samples"] == 15, "resource observation count drift")
    expect(resources["resource_gate_passed"] is True, "resource gate concealed")

    cleanup = record["identity_and_cleanup"]
    for key in (
        "canonical_cli_matches_after",
        "engine_matches_after",
        "preference_matches_after",
        "weight_matches_after",
        "activation_processes_absent",
        "port_1234_listener_absent",
        "partial_weight_absent",
        "raw_cli_output_deleted",
        "temporary_cli_deleted",
        "forced_cleanup_required",
        "final_safety_cleanup_passed",
    ):
        expect(cleanup[key] is True, f"cleanup fact drift: {key}")
    expect(cleanup["loaded_inventory_after_unload"] == [], "post-unload inventory not empty")
    expect(cleanup["graceful_cleanup_gate_passed"] is False, "graceful cleanup overclaim")
    expect(cleanup["engine_inventory_sha256"] == "f40cc6918e6d17975cdcb3151f4953e8788d87bc7e565242d40bd292f7385fd0", "engine digest drift")

    independent = record["independent_post_run_checkpoint"]
    expect(independent["matching_runtime_process_count"] == 0, "post-run process retained")
    expect(independent["port_1234_listening"] is False, "post-run port retained")
    expect(independent["available_memory_bytes"] > 0, "post-run memory observation missing")
    expect(independent["gpu_used_memory_mib"] >= 0, "post-run GPU observation invalid")

    acceptance = record["acceptance"]
    for key in ("model_load_observed", "exact_loaded_inventory_gate_passed", "resource_gate_passed", "final_safety_cleanup_passed"):
        expect(acceptance[key] is True, f"observed pass lost: {key}")
    for key in ("graceful_shutdown_gate_passed", "load_health_gate_passed", "model_quality_conclusion_allowed"):
        expect(acceptance[key] is False, f"acceptance overclaim: {key}")

    security = record["security_and_research_boundary"]
    expect(security["maximum_runner_invocations"] == 1, "runner invocation count widened")
    expect(security["maximum_model_load_attempts"] == 1, "model-load count widened")
    for key in ("automatic_retry_count", "inference_request_count", "http_server_start_count", "cyxcode_invocation_count", "docker_container_count"):
        expect(security[key] == 0, f"operation or retry admitted: {key}")
    for key in ("synthetic_prompt_authorized", "benchmark_or_thesis_content_authorized"):
        expect(security[key] is False, f"research boundary widened: {key}")

    gate = record["decision_gate"]
    expect(gate["execution_authorization_consumed"] is True, "authorization consumption concealed")
    for key in ("automatic_retry_authorized", "synthetic_canary_authorized", "authenticated_http_server_authorized", "benchmark_input_authorized"):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(gate["next_action"] == "review_daemon_shutdown_exit_and_liveness_contract_before_any_new_decision", "next action drift")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, LoadHealthRunnerExecutionResultError) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: model load/resource gates observed; graceful shutdown failed; retry blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
