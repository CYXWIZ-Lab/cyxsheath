"""Validate the one-shot Phase-6 Python load-health runner decision."""

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


class LoadHealthRunnerExecutionDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LoadHealthRunnerExecutionDecisionError(message)


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


def expect_source(base: Path, item: dict, label: str) -> None:
    target = (base / item["path"]).resolve()
    expect(target.is_file(), f"{label}: source missing")
    expect(DIGEST.fullmatch(item["corrected_sha256"]) is not None, f"{label}: malformed digest")
    current = file_digest(target)
    if current != item["corrected_sha256"]:
        expect(
            historical_source_has_successor(
                item["path"], item["corrected_sha256"], current
            ),
            f"{label}: source digest drift",
        )
    expect(item["previous_sha256"] != item["corrected_sha256"], f"{label}: transition concealed")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(record["status"] == "python_load_health_runner_execution_authorized_once", "unsafe status")
    expect(
        record["decision_scope"] == "one_exact_load_health_execution_without_inference_or_http_server",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")
    expect(record["maximum_attempts"] == 1, "attempt count widened")

    base = path.parent
    integration = base / "phase6_load_health_transport_integration_decision.json"
    expect(file_digest(integration) == record["integration_decision_sha256"], "integration digest drift")
    sources = {
        "runner_sha256": (
            base.parent / "run_local_model_load_health.py",
            "../run_local_model_load_health.py",
        ),
        "monitored_process_sha256": (
            base.parent / "monitored_process.py",
            "../monitored_process.py",
        ),
        "windows_adapter_sha256": (
            base.parent / "lm_studio_windows.py",
            "../lm_studio_windows.py",
        ),
    }
    for key, (target, relative) in sources.items():
        expect(DIGEST.fullmatch(record[key]) is not None, f"{key}: malformed digest")
        current = file_digest(target)
        expect(
            current == record[key]
            or historical_source_has_successor(relative, record[key], current),
            f"{key}: source digest drift",
        )

    prior = record["prior_blocking_decision"]
    expect(prior["record"] == "phase6_load_health_runner_fresh_execution_decision.json", "prior record drift")
    prior_path = base / prior["record"]
    expect(file_digest(prior_path) == prior["sha256"], "prior decision digest drift")
    prior_record = json.loads(prior_path.read_text(encoding="utf-8"))
    expect(prior_record["status"] == prior["status"], "prior decision status drift")
    expect(prior["authorized_change"] == prior_record["decision_gate"]["next_action"], "authorized correction drift")

    correction = record["canonicalization_correction"]
    expect(correction["rule"] == "normalized_relative_posix_path_utf8_byte_ascending", "canonical rule drift")
    expect(correction["json_encoding"] == "utf8_compact_ensure_ascii_false", "JSON encoding drift")
    expect(correction["file_metadata"] == ["path", "bytes", "sha256"], "inventory fields drift")
    superseded = correction["superseded_digests"]
    expect(superseded["powershell_culture_aware"] == "389f3fc28e5ec80ec69a3b904ec844f51dadb789162000532c0b0db738c78561", "PowerShell digest drift")
    expect(superseded["python_windows_path_casefolded"] == "c016b534216f21f949ffa1ad3accae9227d4b14105aa1e8ed6c16893ee400d46", "Path digest drift")
    inventory = correction["corrected_inventory"]
    expect(inventory == {
        "engine_package": "llama.cpp-win-x86_64-nvidia-cuda-avx2-2.29.1",
        "file_count": 20,
        "total_bytes": 558082098,
        "sha256": "f40cc6918e6d17975cdcb3151f4953e8788d87bc7e565242d40bd292f7385fd0",
    }, "corrected engine identity drift")
    transition = correction["source_transition"]
    for label in ("windows_adapter", "runner", "runner_test"):
        expect_source(base, transition[label], label)
    expect(transition["runner"]["corrected_sha256"] == record["runner_sha256"], "runner linkage drift")
    expect(transition["windows_adapter"]["corrected_sha256"] == record["windows_adapter_sha256"], "adapter linkage drift")
    fixtures = correction["fixture_evidence"]
    for runtime in ("python_3_12", "python_3_14"):
        expect(fixtures[runtime] == {"tests_run": 9, "tests_passed": 9}, f"{runtime}: fixture drift")
    expect(fixtures["lm_studio_invocation_count"] == 0, "fixture runtime operation admitted")

    settings = record["settings"]
    expect(settings == {
        "model_key": "qwen2.5-coder-7b-instruct",
        "identifier": "cyxsheath-qwen25-coder-7b-q4km",
        "context_length_tokens": 8192,
        "gpu_offload": "off",
        "parallel_predictions": 1,
        "idle_ttl_seconds": 600,
        "load_timeout_seconds": 600,
        "sample_interval_seconds": 1,
        "post_load_observation_samples": 15,
        "inference_request_count": 0,
        "http_server_start_count": 0,
        "cyxcode_invocation_count": 0,
        "docker_container_count": 0,
    }, "execution settings drift")

    identity = record["identity_checkpoint"]
    expected_identity = {
        "canonical_cli_bytes": 120772792,
        "canonical_cli_sha256": "976d4389f97b2cf95b38a4eb673855d8a846f2db21a20eb4fe5e79f7179722f5",
        "preference_bytes": 116,
        "preference_sha256": "7448caf18fc92b7e0769924b6cdf1f437279765ff33d2ad7bebccaf22c9857c7",
        "weight_bytes": 4683073536,
        "weight_sha256": "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c",
    }
    for key, value in expected_identity.items():
        expect(identity[key] == value, f"{key}: identity drift")

    clean = record["clean_baseline"]
    expect(clean["matching_runtime_process_count"] == 0, "runtime process present")
    expect(clean["port_1234_listening"] is False, "port baseline unclean")
    expect(clean["available_memory_bytes"] >= clean["minimum_required_available_memory_bytes"], "memory floor failed")
    for key in ("runner_cache_present", "prior_result_present", "prior_claim_present"):
        expect(clean[key] is False, f"unclean baseline: {key}")

    one_shot = record["one_shot_contract"]
    for key in ("authorization_validated_before_claim", "exclusive_claim_required_before_host_access", "claim_retained_after_success_failure_or_crash"):
        expect(one_shot[key] is True, f"one-shot invariant weakened: {key}")
    expect(one_shot["maximum_runner_invocations"] == 1, "runner invocation count widened")
    expect(one_shot["maximum_model_load_attempts"] == 1, "model load count widened")
    expect(one_shot["automatic_retry_count"] == 0, "automatic retry admitted")

    security = record["security_and_research_boundary"]
    for key, value in security.items():
        if key.endswith("_count") or key.endswith("_count_at_review"):
            expect(value == 0, f"runtime or external operation admitted: {key}")
        else:
            expect(value is False, f"research boundary widened: {key}")

    gate = record["decision_gate"]
    for key in ("canonicalization_correction_complete", "fixture_gate_passed", "execution_authorization_record_creation_authorized", "load_health_execution_authorized"):
        expect(gate[key] is True, f"required authorization missing: {key}")
    for key in ("automatic_retry_authorized", "synthetic_canary_authorized", "authenticated_http_server_authorized", "benchmark_input_authorized"):
        expect(gate[key] is False, f"scope widened: {key}")
    expect(gate["next_action"] == "execute_the_digest_bound_python_load_health_runner_once_and_preserve_the_result", "next action drift")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, LoadHealthRunnerExecutionDecisionError) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: corrected digest-bound Python load-health execution authorized once")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
