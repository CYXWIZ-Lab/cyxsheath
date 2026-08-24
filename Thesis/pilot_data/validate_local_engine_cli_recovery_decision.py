"""Validate the repinned engine and temporary-CLI load-health decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
CLI_DIGEST = "976d4389f97b2cf95b38a4eb673855d8a846f2db21a20eb4fe5e79f7179722f5"
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


class EngineCliRecoveryDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise EngineCliRecoveryDecisionError(message)


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
    expect(
        record["status"] == "engine_2_29_1_repinned_temporary_cli_copy_retry_authorized_once",
        "unsafe status",
    )
    expect(
        record["decision_scope"] == "one_load_health_retry_without_inference_or_http_server",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    failed = record["failed_result"]
    expect(failed["record"] == "phase6_local_model_load_health_result.json", "failed-result record drift")
    expect_digest(failed["sha256"], "failed result")
    failed_path = path.parent / failed["record"]
    expect(failed_path.is_file(), "failed result missing")
    expect(hashlib.sha256(failed_path.read_bytes()).hexdigest() == failed["sha256"], "failed-result digest mismatch")
    expect(failed["status"] == "model_activation_observed_protocol_acceptance_failed", "failed status drift")

    engine = record["engine_decision"]
    expect(
        engine["action"] == "adopt_already_installed_active_engine_without_install_or_update",
        "engine action widened",
    )
    expect(engine["package"] == "llama.cpp-win-x86_64-nvidia-cuda-avx2-2.29.1", "engine package drift")
    expect(engine["version"] == "2.29.1", "engine version drift")
    expect(engine["format"] == "gguf", "engine format drift")
    expect(engine["file_count"] == 20, "engine file-count drift")
    expect(engine["total_bytes"] == 558082098, "engine size drift")
    for key in ("inventory_sha256", "manifest_sha256", "server_sha256", "preference_file_sha256"):
        expect_digest(engine[key], key)
    expect(engine["restore_2_28_2"] is False, "unselected downgrade admitted")
    expect(engine["installation_or_download_authorized"] is False, "runtime mutation admitted")

    cli = record["cli_decision"]
    expect(cli["version"] == "1.3.3", "CLI version drift")
    expect(cli["canonical_relative_path"] == "lmstudio_home/bin/lms.exe", "canonical CLI path drift")
    expect(cli["exact_bytes"] == 120772792, "CLI size drift")
    expect(cli["sha256"] == CLI_DIGEST, "CLI digest drift")
    expect(
        cli["temporary_relative_path"] == ".replay_cache/local_model_load_health_repin/lms.exe",
        "temporary CLI path drift",
    )
    expect(cli["temporary_copy_count"] == 1, "temporary CLI copies widened")
    for key in (
        "copy_source_must_match_sha256",
        "copy_must_match_sha256_before_each_invocation",
        "temporary_copy_deleted_after",
        "canonical_copy_must_match_sha256_after",
    ):
        expect(cli[key] is True, f"CLI identity or cleanup weakened: {key}")
    for key in ("invoke_canonical_copy_after_staging", "update_or_install_command_authorized"):
        expect(cli[key] is False, f"unsafe CLI behavior admitted: {key}")
    expect(
        cli["mechanism"]
        == "invoke_hash_verified_temporary_copy_so_canonical_extraction_target_is_not_the_running_executable",
        "CLI mechanism drift",
    )

    model = record["unchanged_model_contract"]
    expect(model["model_key"] == "qwen2.5-coder-7b-instruct", "model key drift")
    expect(model["load_identifier"] == "cyxsheath-qwen25-coder-7b-q4km", "model identifier drift")
    expect(model["weight_bytes"] == 4683073536, "weight size drift")
    expect(model["weight_sha256"] == WEIGHT_DIGEST, "weight digest drift")
    expect(model["context_length_tokens"] == 8192, "context drift")
    expect(model["gpu_offload"] == "off", "GPU offload admitted")
    expect(model["parallel_predictions"] == 1, "parallelism widened")
    expect(model["idle_ttl_seconds"] == 600, "TTL drift")
    expect(model["speculative_decoding"] is False, "speculative decoding admitted")

    execution = record["execution_contract"]
    expected = {
        "maximum_attempts": 1,
        "daemon_start_timeout_seconds": 180,
        "load_timeout_seconds": 600,
        "post_load_observation_samples": 15,
        "sample_interval_seconds": 1,
        "minimum_preload_available_memory_bytes": 21474836480,
        "minimum_observed_available_memory_bytes": 17179869184,
        "maximum_available_memory_drop_bytes": 12884901888,
        "maximum_activation_tree_private_bytes": 12884901888,
        "maximum_activation_tree_working_set_bytes": 12884901888,
        "maximum_gpu_used_memory_delta_mib": 512,
        "inference_request_count": 0,
        "cyxcode_invocation_count": 0,
        "docker_container_count": 0,
    }
    for key, value in expected.items():
        expect(execution[key] == value, f"execution contract drift: {key}")
    for key in (
        "all_cli_clients_must_exit_zero",
        "exact_post_load_inventory_required",
        "fail_closed_on_missing_measurement",
    ):
        expect(execution[key] is True, f"acceptance gate weakened: {key}")
    expect(execution["http_listener_allowed"] is False, "HTTP listener admitted")

    cleanup = record["rollback_and_cleanup"]
    for key, value in cleanup.items():
        expect(value is True, f"cleanup weakened: {key}")

    boundary = record["security_and_research_boundary"]
    for key in (
        "synthetic_prompt_authorized",
        "authenticated_http_server_authorized",
        "benchmark_or_thesis_content_authorized",
        "mcp_authorized",
        "raw_cli_output_in_curated_evidence",
    ):
        expect(boundary[key] is False, f"research boundary widened: {key}")
    expect(boundary["engine_repin_is_not_model_quality_evidence"] is True, "quality overclaim admitted")

    gate = record["execution_gate"]
    expect(gate["fresh_load_health_execution_authorized_once"] is True, "load-health retry not authorized")
    for key in (
        "different_engine_model_or_settings_authorized",
        "synthetic_canary_authorized",
        "authenticated_http_server_authorized",
        "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"] == "execute_exact_temporary_cli_load_health_contract_once_and_record_result",
        "next action drift",
    )

    expect(len(record["sources"]) == 4, "source set drift")
    expect(all(source["accessed_at"] == "2026-08-24" for source in record["sources"]), "source date drift")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, EngineCliRecoveryDecisionError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(
        "VALID: engine=2.29.1; cli=temporary-pinned-copy; attempts=1; "
        "inference=blocked; server=blocked; canary=blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
