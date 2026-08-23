"""Validate the one-shot local-model load-health decision without executing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_COMMAND = (
    "lms load qwen2.5-coder-7b-instruct --gpu off --context-length 8192 --parallel 1 "
    "--ttl 600 --no-speculative-draft-mtp --identifier cyxsheath-qwen25-coder-7b-q4km --yes"
)
WEIGHT_DIGEST = "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c"
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


class LoadHealthDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LoadHealthDecisionError(message)


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
    expect(record["status"] == "load_only_health_check_authorized_once", "unsafe status")
    expect(
        record["decision_scope"] == "one_shot_local_model_load_health_without_inference_or_http_server",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    preflight = record["activation_preflight"]
    expect(preflight["record"] == "phase6_local_model_activation_preflight.json", "preflight record drift")
    expect(DIGEST.fullmatch(preflight["sha256"]) is not None, "malformed preflight digest")
    preflight_path = path.parent / preflight["record"]
    expect(preflight_path.is_file(), "activation preflight missing")
    expect(hashlib.sha256(preflight_path.read_bytes()).hexdigest() == preflight["sha256"], "preflight digest mismatch")
    expect(preflight["status"] == "activation_preflight_complete_load_health_gate_pending", "preflight status drift")

    authorization = record["authorization"]
    expect(authorization["operator_proceed_recorded"] is True, "operator authorization missing")
    expect(authorization["maximum_attempts"] == 1, "attempt count widened")
    expect(authorization["executed_attempts_at_decision"] == 0, "decision claims prior execution")
    expect(authorization["different_model_or_settings_authorized"] is False, "alternate settings admitted")

    model = record["model"]
    expect(model["model_key"] == "qwen2.5-coder-7b-instruct", "model key drift")
    expect(model["load_identifier"] == "cyxsheath-qwen25-coder-7b-q4km", "load identifier drift")
    expect(model["file"] == "qwen2.5-coder-7b-instruct-q4_k_m.gguf", "weight file drift")
    expect(model["relative_path"] == f".local_models/{model['file']}", "weight path drift")
    expect(model["exact_bytes"] == 4683073536, "weight size drift")
    expect(model["sha256"] == WEIGHT_DIGEST, "weight digest drift")

    load = record["load_contract"]
    expect(load["runtime"] == "LM Studio", "runtime drift")
    expect(load["command"] == EXPECTED_COMMAND, "load command drift")
    expected_load = {
        "context_length_tokens": 8192,
        "parallel_predictions": 1,
        "idle_ttl_seconds": 600,
        "load_timeout_seconds": 600,
        "daemon_start_timeout_seconds": 180,
        "post_load_observation_seconds": 15,
        "sample_interval_seconds": 1,
    }
    for key, expected in expected_load.items():
        expect(load[key] == expected, f"load setting drift: {key}")
    expect(load["gpu_offload"] == "off", "GPU offload admitted")
    expect(load["speculative_decoding"] is False, "speculative decoding admitted")

    baseline = record["host_baseline_at_decision"]
    expect(baseline["total_physical_memory_bytes"] == 51387342848, "host memory identity drift")
    expect(baseline["available_physical_memory_bytes"] >= 21474836480, "insufficient decision baseline")
    expect(baseline["gpu_total_memory_mib"] == 4096, "GPU memory identity drift")
    expect(baseline["activation_process_count"] == 0, "unclean decision baseline")
    expect(baseline["port_1234_listener_present"] is False, "HTTP listener present at decision")

    observation = record["observation_contract"]
    expected_limits = {
        "minimum_preload_available_memory_bytes": 21474836480,
        "minimum_observed_available_memory_bytes": 17179869184,
        "maximum_available_memory_drop_bytes": 12884901888,
        "maximum_activation_tree_private_bytes": 12884901888,
        "maximum_activation_tree_working_set_bytes": 12884901888,
        "maximum_gpu_used_memory_delta_mib": 512,
        "http_port": 1234,
        "inference_request_count": 0,
        "cyxcode_invocation_count": 0,
        "docker_container_count": 0,
    }
    for key, expected in expected_limits.items():
        expect(observation[key] == expected, f"observation limit drift: {key}")
    expect(observation["http_listener_allowed_during_check"] is False, "HTTP listener admitted")
    expect(
        observation["model_inventory_after_load"] == "exactly_one_expected_identifier_and_model_key",
        "loaded identity weakened",
    )

    acceptance = record["acceptance_contract"]
    expect(all(acceptance.values()), "acceptance contract weakened")

    cleanup = record["cleanup_contract"]
    expect(cleanup["unload_command"] == "lms unload cyxsheath-qwen25-coder-7b-q4km", "unload drift")
    expect(cleanup["unload_timeout_seconds"] == 120, "unload timeout drift")
    expect(cleanup["loaded_model_inventory_after_unload"] == "empty", "unload proof weakened")
    for key in (
        "stop_only_activation_process_tree",
        "graceful_stop_before_force",
        "activation_process_tree_absent_after",
        "port_1234_listener_absent_after",
        "partial_weight_absent_after",
    ):
        expect(cleanup[key] is True, f"cleanup weakened: {key}")

    security = record["security_and_retention"]
    for key in (
        "http_server_start_authorized",
        "inference_request_authorized",
        "synthetic_prompt_authorized",
        "benchmark_or_thesis_content_authorized",
        "mcp_authorized",
        "raw_cli_output_in_curated_evidence",
    ):
        expect(security[key] is False, f"security boundary widened: {key}")
    expect(security["temporary_output_git_ignored"] is True, "temporary output not ignored")

    gate = record["execution_gate"]
    expect(gate["load_health_check_authorized_once"] is True, "load-health execution not authorized")
    for key in ("synthetic_canary_authorized", "authenticated_http_server_authorized", "benchmark_input_authorized"):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"] == "execute_exact_load_only_contract_once_and_record_result",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, LoadHealthDecisionError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(
        f"VALID: model={record['model']['model_key']}; attempts=1; "
        "load-only=authorized; inference=blocked; server=blocked; benchmark=blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
