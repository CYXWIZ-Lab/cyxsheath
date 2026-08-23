"""Validate the Phase-6 local runtime/model decision without executing it."""

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


class RuntimeModelDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeModelDecisionError(message)


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


def expect_positive_int(value: object, name: str) -> None:
    expect(isinstance(value, int) and not isinstance(value, bool) and value > 0, f"invalid integer: {name}")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(record["status"] == "runtime_model_selected_download_pending_synthetic_only", "unsafe status")
    expect(
        record["decision_scope"] == "synthetic_local_feasibility_not_benchmark_admission",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    capacity = record["capacity_evidence"]
    expect(capacity["record"] == "phase6_host_capacity_and_connectivity.json", "capacity record drift")
    expect_digest(capacity["sha256"], "capacity evidence")
    capacity_path = path.parent / capacity["record"]
    expect(capacity_path.is_file(), "capacity evidence missing")
    expect(hashlib.sha256(capacity_path.read_bytes()).hexdigest() == capacity["sha256"], "capacity digest mismatch")

    seam = record["cyxcode_seam"]
    expect(seam["commit"] == "42676876b63ed5a18957e3318272eb0d875a95fc", "CyxCode revision drift")
    expect(seam["provider_package"] == "@ai-sdk/openai-compatible", "provider seam drift")
    expect(seam["provider_package_version"] == "1.0.32", "provider package drift")
    expect(seam["container_host_alias"] == "host.docker.internal", "container alias drift")
    expect(seam["new_core_abstraction_required"] is False, "unnecessary abstraction admitted")

    runtime = record["runtime"]
    expect(runtime["selected"] is True, "runtime not selected")
    expect(runtime["family"] == "LM Studio local server", "runtime family drift")
    expect(runtime["cli"]["version"] == "1.3.3", "CLI version drift")
    expect(runtime["cli"]["commit"] == "71bd99c", "CLI commit drift")
    expect_digest(runtime["cli"]["sha256"], "CLI")
    engine = runtime["engine"]
    expect(engine["package"] == "llama.cpp-win-x86_64-nvidia-cuda-avx2-2.28.2", "engine package drift")
    expect(engine["version"] == "2.28.2", "engine version drift")
    expect(engine["format"] == "gguf", "engine format drift")
    for key in ("inventory_sha256", "manifest_sha256", "server_sha256"):
        expect_digest(engine[key], key)
    expect(runtime["service_ready_at_decision"] is False, "runtime readiness overclaim")
    expect(runtime["installation_required"] is False, "runtime installation overclaim")

    api = record["api"]
    expect(api["protocol"] == "openai_compatible_chat_completions", "API protocol drift")
    expect(api["container_base_url"] == "http://host.docker.internal:1234/v1", "API route drift")
    expect(api["server_bind"] == "0.0.0.0", "container-inaccessible bind")
    expect(api["port"] == 1234, "port drift")
    expect(api["authentication_required"] is True, "authentication weakened")
    expect(api["cors_enabled"] is False, "CORS admitted")
    expect(api["credential_retention"] == "environment_only_not_evidence", "credential boundary drift")

    model = record["model"]
    expect(model["selected"] is True, "model not selected")
    expect(model["repository"] == "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", "model repository drift")
    expect(model["revision"] == MODEL_REVISION, "model revision drift")
    expect(model["file"] == "qwen2.5-coder-7b-instruct-q4_k_m.gguf", "weight file drift")
    expect(model["weight_sha256"] == WEIGHT_DIGEST, "weight digest drift")
    expect(model["format"] == "GGUF" and model["quantization"] == "Q4_K_M", "quantization drift")
    expect(model["license_spdx"] == "Apache-2.0", "model license drift")
    expect(model["gguf_context_limit_tokens"] == 32768, "published context drift")
    expect(model["tool_call_status"] == "runtime_family_supported_exact_coder_seam_unverified", "tool claim overreach")
    expect(model["selected_use"] == "single_generated_public_synthetic_canary_only", "model use widened")
    expect(model["benchmark_use"] == "blocked", "benchmark model use admitted")

    alternative = record["bounded_alternative"]
    expect(alternative["model"] == "Qwen/Qwen3-Coder-30B-A3B-Instruct", "alternative drift")
    expect(alternative["status"] == "deferred_not_selected", "alternative activated prematurely")
    expect(
        alternative["activation_rule"] == "consider_only_after_capability_specific_small_model_failure_and_new_decision",
        "alternative activation widened",
    )

    resources = record["resource_policy"]
    expect(resources["storage_root"] == "repository_root/.local_models", "storage root drift")
    expect(resources["storage_drive"] == "D:", "unsafe storage drive")
    expected = {
        "weight_download_ceiling_bytes": 6442450944,
        "local_model_storage_ceiling_bytes": 8589934592,
        "minimum_drive_free_after_bytes": 34359738368,
        "context_length_tokens": 8192,
        "maximum_output_tokens": 2048,
        "parallel_predictions": 1,
        "idle_ttl_seconds": 600,
        "estimated_total_memory_ceiling_bytes": 12884901888,
        "canary_wall_time_ceiling_seconds": 900,
    }
    for key, value in expected.items():
        expect_positive_int(resources[key], key)
        expect(resources[key] == value, f"resource ceiling drift: {key}")
    expect(resources["import_mode"] == "symbolic_link_no_second_weight_copy", "duplicate weight copy admitted")
    expect(resources["gpu_offload"] == "off", "GPU complexity admitted in first canary")
    expect(resources["estimate_only_required_before_load"] is True, "memory estimate gate removed")

    activation = record["download_and_activation_policy"]
    expect(MODEL_REVISION in activation["download_url"], "download revision not pinned")
    expect(activation["download_url"].endswith(model["file"] + "?download=true"), "download file drift")
    expect(activation["download_attempts"] == 1, "download attempts widened")
    expect(activation["verify_sha256_before_import"] is True, "pre-import digest gate removed")
    expect(activation["estimate_before_load"] is True, "pre-load estimate gate removed")
    expect(len(activation["post_run_requirements"]) == 5, "cleanup requirements drift")

    context = record["security_and_context"]
    expect(context["input_class"] == "generated_public_non_sensitive_non_benchmark", "unsafe input class")
    expect(context["api_token_per_run"] is True, "per-run authentication missing")
    for key in (
        "api_token_retained",
        "mcp_enabled",
        "cyxcode_resume_context_enabled",
        "benchmark_or_thesis_content_allowed",
        "raw_model_content_in_curated_evidence",
    ):
        expect(context[key] is False, f"unsafe context setting: {key}")

    contamination = record["contamination_treatment"]
    expect(contamination["training_corpus_membership_disclosed"] is False, "corpus disclosure overclaim")
    expect(contamination["benchmark_overlap_status"] == "uncertain", "contamination overclaim")
    expect(contamination["synthetic_canary_affected"] is False, "synthetic scope confused")
    expect(contamination["benchmark_admission"] == "blocked", "contaminated benchmark admitted")

    gate = record["execution_gate"]
    expect(gate["runtime_installation_authorized"] is False, "runtime installation admitted")
    expect(gate["exact_weight_download"] == "permitted_once_after_operator_approval", "download gate drift")
    expect(gate["different_weight_or_quantization_authorized"] is False, "alternate weight admitted")
    expect(gate["synthetic_canary_authorized_now"] is False, "canary admitted before activation checks")
    expect(gate["benchmark_input_authorized"] is False, "benchmark input admitted")
    expect(
        gate["next_action"] == "obtain_operator_approval_then_download_and_verify_exact_weight",
        "next action drift",
    )

    expect(len(record["sources"]) == 7, "source set drift")
    expect(all(source["accessed_at"] == "2026-08-23" for source in record["sources"]), "source date drift")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, RuntimeModelDecisionError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(
        f"VALID: runtime={record['runtime']['family']}; "
        f"model={record['model']['repository']}@{record['model']['revision'][:7]}; "
        "download=pending; synthetic_canary=blocked; benchmark=blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
