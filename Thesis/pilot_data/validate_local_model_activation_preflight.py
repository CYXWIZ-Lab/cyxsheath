"""Validate the Phase-6 local-model activation preflight without loading it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
MODEL_REVISION = "13fb94bfda8c8cf22497dc57b78f391a9acb426a"
WEIGHT_DIGEST = "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c"
WEIGHT_BYTES = 4683073536
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


class ActivationPreflightError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise ActivationPreflightError(message)


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
    expect(record["status"] == "activation_preflight_complete_load_health_gate_pending", "unsafe status")
    expect(
        record["decision_scope"] == "local_activation_preflight_not_inference_or_benchmark_admission",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    decision = record["decision_evidence"]
    expect(decision["record"] == "phase6_local_runtime_model_decision.json", "decision record drift")
    expect(DIGEST.fullmatch(decision["sha256"]) is not None, "malformed decision digest")
    decision_path = path.parent / decision["record"]
    expect(decision_path.is_file(), "decision evidence missing")
    expect(hashlib.sha256(decision_path.read_bytes()).hexdigest() == decision["sha256"], "decision digest mismatch")
    expect(decision["status"] == "runtime_model_selected_download_pending_synthetic_only", "decision status drift")

    download = record["download"]
    expect(download["attempts"] == 1, "download attempts widened")
    expect(download["transport"] == "https_resumable_partial_then_atomic_rename", "download transport drift")
    expect(download["source_revision"] == MODEL_REVISION, "model revision drift")
    expect(download["file"] == "qwen2.5-coder-7b-instruct-q4_k_m.gguf", "weight file drift")
    expect(download["final_relative_path"] == f".local_models/{download['file']}", "local path drift")
    expect(download["exact_bytes"] == WEIGHT_BYTES, "weight size drift")
    expect(download["expected_sha256"] == WEIGHT_DIGEST, "expected weight digest drift")
    expect(download["actual_sha256"] == WEIGHT_DIGEST, "actual weight digest drift")
    expect(download["digest_verified_before_import"] is True, "pre-import digest gate failed")
    expect(download["partial_absent_after"] is True, "partial download retained")
    expect(download["exact_bytes"] < download["download_ceiling_bytes"], "download ceiling failed")
    expect(download["final_free_bytes"] >= download["minimum_free_after_bytes"], "storage reserve failed")
    expect(download["git_ignored"] is True, "weight is not ignored")

    imported = record["import"]
    expect(imported["mode"] == "symbolic_link", "import mode drift")
    expect(imported["configured_model_root"] == "D:/Open_models", "model root drift")
    expect(imported["imported_relative_path"].endswith(download["file"]), "import identity drift")
    expect(imported["link_target"] == f"repository_root/{download['final_relative_path']}", "link target drift")
    expect(imported["duplicate_weight_copy_created"] is False, "duplicate weight copy created")
    expect(imported["source_and_import_digest_match"] is True, "import digest mismatch")

    runtime = record["runtime_activation"]
    expect(runtime["runtime"] == "LM Studio", "runtime drift")
    expect(runtime["daemon_version"] == "0.4.21+2", "daemon version drift")
    expect(runtime["existing_installation_only"] is True, "new runtime admitted")
    expect(runtime["installation_or_update_performed"] is False, "installation overclaim")
    expect(runtime["daemon_started_for_inventory"] is True, "inventory runtime missing")
    for key in ("http_server_started", "model_loaded"):
        expect(runtime[key] is False, f"unexpected activation: {key}")
    expect(runtime["daemon_stopped_after"] is True, "daemon cleanup failed")
    expect(runtime["activation_process_tree_absent_after"] is True, "activation process retained")
    expect(runtime["port_1234_listener_absent_after"] is True, "HTTP listener retained")

    inventory = record["inventory"]
    expect(inventory["model_key"] == "qwen2.5-coder-7b-instruct", "model key drift")
    expect(inventory["format"] == "gguf" and inventory["architecture"] == "qwen2", "model format drift")
    expect(inventory["quantization"] == "Q4_K_M", "quantization drift")
    expect(inventory["size_bytes"] == WEIGHT_BYTES, "inventory size drift")
    expect(inventory["trained_for_tool_use"] is False, "tool-use capability overclaim")
    expect(inventory["authoritative_gguf_card_limit_tokens"] == 32768, "published context drift")
    expect(inventory["effective_canary_ceiling_tokens"] == 8192, "context ceiling widened")
    expect(inventory["runtime_reported_max_context_tokens"] != 32768, "context discrepancy lost")
    expect(inventory["max_context_discrepancy_retained"] is True, "context discrepancy concealed")
    expect(inventory["exact_tool_seam_status"] == "unverified_default_tool_path", "tool seam overclaim")

    estimate = record["estimate"]
    expect(estimate["command_mode"] == "estimate_only", "estimate mode drift")
    expect(estimate["context_length_tokens"] == 8192, "estimate context drift")
    expect(estimate["gpu_offload_percent"] == 0, "GPU offload admitted")
    expect(estimate["parallel_predictions"] == 1, "parallelism widened")
    expect(estimate["reported_total_memory_gib"] == 4.36, "total-memory estimate drift")
    expect(estimate["total_memory_ceiling_gib"] == 12, "memory ceiling drift")
    expect(estimate["total_memory_ceiling_passed"] is True, "memory estimate gate failed")
    expect(estimate["confidence"] == "LOW", "estimator confidence overclaim")
    expect(estimate["reported_gpu_memory_gib"] == 4.36, "GPU-label anomaly drift")
    expect(estimate["gpu_label_conflict_retained"] is True, "GPU-label anomaly concealed")
    expect(
        estimate["interpretation"] == "low_confidence_estimator_label_requires_observed_load_health_gate",
        "estimate interpretation drift",
    )
    expect(estimate["host_context_repeat_clean"] is True, "clean estimate repeat missing")
    expect(estimate["model_loaded"] is False, "estimate loaded model")

    expect(len(record["protocol_deviations"]) == 3, "protocol-deviation inventory drift")
    gate = record["execution_gate"]
    for key in ("exact_weight_download_complete", "symbolic_import_complete", "estimate_gate_passed"):
        expect(gate[key] is True, f"incomplete preflight: {key}")
    for key in ("load_health_check_authorized", "synthetic_canary_authorized", "benchmark_input_authorized"):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"] == "record_bounded_load_only_health_and_authenticated_server_gate",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, ActivationPreflightError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(
        f"VALID: weight={record['download']['actual_sha256'][:12]}; "
        "import=symbolic-link; estimate=passed-low-confidence; load=blocked; canary=blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
