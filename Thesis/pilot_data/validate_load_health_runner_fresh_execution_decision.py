"""Validate the blocked fresh Phase-6 load-health execution decision."""

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


class LoadHealthRunnerFreshExecutionDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LoadHealthRunnerFreshExecutionDecisionError(message)


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


def expect_evidence(base: Path, item: dict, name: str, status: str) -> dict:
    expect(item["record"] == name, f"{name}: record drift")
    expect(DIGEST.fullmatch(item["sha256"]) is not None, f"{name}: malformed digest")
    target = base / name
    expect(target.is_file(), f"{name}: missing evidence")
    expect(file_digest(target) == item["sha256"], f"{name}: digest drift")
    evidence = json.loads(target.read_text(encoding="utf-8"))
    expect(item["status"] == status == evidence["status"], f"{name}: status drift")
    return evidence


def expect_superseded_source(base: Path, item: dict, key: str, target: Path) -> None:
    current = file_digest(target)
    if current == item["sha256"]:
        return
    canonical_path = base / "phase6_load_health_runner_fresh_execution_decision.json"
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    expect(item == canonical["reviewed_evidence"][key], f"{key}: source digest drift")
    successor_path = base / "phase6_load_health_runner_execution_decision.json"
    successor = json.loads(successor_path.read_text(encoding="utf-8"))
    prior = successor["prior_blocking_decision"]
    expect(prior["record"] == canonical_path.name, f"{key}: supersession record drift")
    expect(prior["sha256"] == file_digest(canonical_path), f"{key}: supersession digest drift")
    transition = successor["canonicalization_correction"]["source_transition"][key]
    expect(transition["previous_sha256"] == item["sha256"], f"{key}: superseded source drift")
    expect(transition["corrected_sha256"] == current, f"{key}: successor source drift")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"]
        == "runner_execution_not_authorized_engine_inventory_canonicalization_mismatch",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "source_evidence_and_read_only_identity_review_no_lm_studio_runtime_authorization",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    reviewed = record["reviewed_evidence"]
    integration = expect_evidence(
        path.parent,
        reviewed["transport_integration"],
        "phase6_load_health_transport_integration_decision.json",
        "load_health_transport_integration_designed_runner_implementation_authorized",
    )
    correction = expect_evidence(
        path.parent,
        reviewed["one_shot_correction"],
        "phase6_load_health_runner_one_shot_correction_result.json",
        "one_shot_claim_gate_corrected_fixtures_passed_runtime_blocked",
    )
    expect(
        integration["execution_gate"]["lm_studio_runtime_execution_authorized"] is False,
        "integration runtime boundary widened",
    )
    expect(
        correction["execution_gate"]["load_health_execution_authorized"] is False,
        "correction runtime boundary widened",
    )
    code = {item["path"]: item["corrected"] for item in correction["code_transition"]}
    for key, relative in (
        ("runner", "../run_local_model_load_health.py"),
        ("windows_adapter", "../lm_studio_windows.py"),
    ):
        item = reviewed[key]
        expect(item["path"] == relative, f"{key}: path drift")
        expect(DIGEST.fullmatch(item["sha256"]) is not None, f"{key}: malformed digest")
        target = (path.parent / relative).resolve()
        expect(target.is_file(), f"{key}: source missing")
        expect_superseded_source(path.parent, item, key, target)
    expect(reviewed["runner"]["sha256"] == code["../run_local_model_load_health.py"]["sha256"], "runner correction linkage drift")
    expect(
        reviewed["windows_adapter"]["sha256"]
        == correction["unchanged_boundaries"]["windows_adapter_sha256"],
        "adapter correction linkage drift",
    )

    expect(
        record["essential_invariant"]
        == "one_shot_authorization_must_not_be_consumed_by_a_known_deterministic_pre_daemon_failure",
        "essential invariant drift",
    )
    identity = record["identity_checkpoint"]
    expect(identity["engine_package"] == "llama.cpp-win-x86_64-nvidia-cuda-avx2-2.29.1", "engine package drift")
    expect(identity["file_count"] == 20, "engine file count drift")
    expect(identity["total_bytes"] == 558082098, "engine byte count drift")
    for key in (
        "recorded_inventory_sha256",
        "runner_computed_inventory_sha256",
        "manifest_sha256",
        "server_sha256",
        "preference_sha256",
        "cli_sha256",
        "weight_sha256",
    ):
        expect(DIGEST.fullmatch(identity[key]) is not None, f"{key}: malformed digest")
    expect(
        identity["recorded_inventory_sha256"]
        == "389f3fc28e5ec80ec69a3b904ec844f51dadb789162000532c0b0db738c78561",
        "recorded engine digest drift",
    )
    expect(
        identity["runner_computed_inventory_sha256"]
        == "c016b534216f21f949ffa1ad3accae9227d4b14105aa1e8ed6c16893ee400d46",
        "runner engine digest drift",
    )
    expect(
        identity["recorded_inventory_sha256"] != identity["runner_computed_inventory_sha256"],
        "inventory mismatch concealed",
    )
    expect(identity["recorded_ordering"] == "powershell_sort_object_full_name_culture_aware", "recorded ordering drift")
    expect(identity["runner_ordering"] == "python_sorted_windows_path_objects", "runner ordering drift")
    witness = identity["ordering_witness"]
    expect(witness["recorded_prefix_after_metadata"][0] == "ggml_llamacpp.dll", "recorded ordering witness drift")
    expect(witness["runner_prefix_after_metadata"][0] == "ggml-base.dll", "runner ordering witness drift")
    expect(identity["same_directory_and_file_bytes_used_for_both_digests"] is True, "content basis concealed")
    expect(identity["cli_bytes"] == 120772792, "CLI size drift")
    expect(identity["weight_bytes"] == 4683073536, "weight size drift")

    finding = record["blocking_finding"]
    expect(finding["finding_id"] == "phase6-runner-review-002", "finding identity drift")
    expect(finding["severity"] == "protocol_blocking", "finding severity weakened")
    expect(
        finding["classification"]
        == "inventory_digest_canonicalization_mismatch_not_proven_engine_content_drift",
        "finding classification drift",
    )
    expect(finding["runner_expected_engine_sha256"] == identity["recorded_inventory_sha256"], "expected digest linkage drift")
    expect(finding["runner_actual_engine_sha256"] == identity["runner_computed_inventory_sha256"], "actual digest linkage drift")
    expect(finding["execution_claim_created_before_engine_identity_check"] is True, "claim ordering concealed")
    expect(finding["daemon_command_reached_if_executed_unchanged"] is False, "daemon reachability overclaim")
    expect(finding["predicted_failure"] == "engine_identity_mismatch", "predicted failure drift")
    expect(
        finding["consequence"]
        == "creating_authorization_now_would_consume_the_retained_one_shot_claim_on_a_known_pre_daemon_failure",
        "consequence drift",
    )
    expect(finding["execution_contract_satisfied"] is False, "execution contract overclaim")

    frozen = record["frozen_execution_contract"]
    expect(
        frozen
        == {
            "maximum_runner_invocations": 1,
            "maximum_model_load_attempts": 1,
            "automatic_retry_count": 0,
            "model_key": "qwen2.5-coder-7b-instruct",
            "identifier": "cyxsheath-qwen25-coder-7b-q4km",
            "context_length_tokens": 8192,
            "gpu_offload": "off",
            "parallel_predictions": 1,
            "idle_ttl_seconds": 600,
            "load_timeout_seconds": 600,
            "sample_interval_seconds": 1,
            "post_load_observation_samples": 15,
        },
        "execution contract drift",
    )

    checkpoint = record["decision_checkpoint"]
    expect(
        checkpoint["required_runtime_authorization_record"]
        == "phase6_load_health_runner_execution_decision.json",
        "runtime authorization record drift",
    )
    for key in ("runtime_authorization_record_present", "runner_cache_present"):
        expect(checkpoint[key] is False, f"unsafe checkpoint: {key}")
    for key in ("matching_runtime_process_count", "port_1234_listener_count", "gpu_used_memory_mib"):
        expect(checkpoint[key] == 0, f"unclean checkpoint: {key}")

    security = record["security_and_research_boundary"]
    for key, value in security.items():
        if key.endswith("_count") or key.endswith("_count_at_review"):
            expect(value == 0, f"runtime or external operation admitted: {key}")
        else:
            expect(value is False, f"security or research boundary widened: {key}")

    gate = record["decision_gate"]
    expect(gate["narrow_engine_identity_canonicalization_correction_authorized"] is True, "identity correction not authorized")
    for key in (
        "load_health_execution_authorized",
        "execution_authorization_record_creation_authorized",
        "automatic_retry_authorized",
        "synthetic_canary_authorized",
        "authenticated_http_server_authorized",
        "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"]
        == "select_one_locale_independent_inventory_order_repin_runner_and_fixtures_then_make_a_new_execution_decision",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (
        OSError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        LoadHealthRunnerFreshExecutionDecisionError,
    ) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: execution blocked; engine inventory canonicalization correction required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
