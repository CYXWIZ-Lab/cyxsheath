"""Validate the blocked Phase-6 activation-runner execution review."""

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


class LoadHealthRunnerExecutionReviewError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LoadHealthRunnerExecutionReviewError(message)


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


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"] == "runner_execution_not_authorized_one_shot_gate_invalid",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "source_and_evidence_review_only_no_lm_studio_runtime_authorization",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    reviewed = record["reviewed_evidence"]
    integration = expect_evidence(
        path.parent,
        reviewed["integration_decision"],
        "phase6_load_health_transport_integration_decision.json",
        "load_health_transport_integration_designed_runner_implementation_authorized",
    )
    implementation = expect_evidence(
        path.parent,
        reviewed["implementation_result"],
        "phase6_load_health_runner_implementation_result.json",
        "activation_runner_implemented_fixtures_passed_runtime_blocked",
    )
    expect(
        integration["execution_gate"]["lm_studio_runtime_execution_authorized"] is False,
        "prior integration runtime boundary widened",
    )
    modules = {item["path"]: item["sha256"] for item in implementation["implementation_identity"]["modules"]}
    for key, relative in (
        ("runner", "../run_local_model_load_health.py"),
        ("monitored_process", "../monitored_process.py"),
        ("windows_adapter", "../lm_studio_windows.py"),
    ):
        item = reviewed[key]
        expect(item["path"] == relative, f"{key}: path drift")
        expect(DIGEST.fullmatch(item["sha256"]) is not None, f"{key}: malformed digest")
        expect(item["sha256"] == modules[relative], f"{key}: implementation linkage drift")

    expect(
        record["essential_invariant"]
        == "one_authorization_can_produce_at_most_one_immutable_attempt_result",
        "one-shot invariant drift",
    )
    finding = record["blocking_finding"]
    expect(finding["finding_id"] == "phase6-runner-review-001", "finding identity drift")
    expect(finding["severity"] == "protocol_blocking", "finding severity weakened")
    expect(
        finding["expected_behavior"]
        == "a_prior_result_blocks_before_host_access_and_preserves_the_prior_result_bytes",
        "expected behavior weakened",
    )
    flow = finding["observed_control_flow"]
    expect(flow["prior_result_check_location"] == "inside_run_attempt_try_block", "check location drift")
    expect(flow["raised_error"] == "ActivationError_prior_load_health_result_present", "raised error drift")
    expect(
        flow["caught_by_existing_handler"]
        == "WindowsHostError_handler_catches_ActivationError_subclass",
        "catch relationship concealed",
    )
    expect(flow["finally_writes_result_after_catch"] is True, "result overwrite path concealed")
    expect(flow["existing_result_preservation_fixture_present"] is False, "fixture overclaim")
    expect(
        finding["consequence"]
        == "a_second_invocation_can_replace_prior_evidence_instead_of_failing_before_attempt_handling",
        "consequence drift",
    )
    expect(finding["one_shot_contract_satisfied"] is False, "one-shot overclaim")

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

    security = record["security_and_research_boundary"]
    for key, value in security.items():
        if key.endswith("_count") or key.endswith("_count_at_review"):
            expect(value == 0, f"runtime or external operation admitted: {key}")
        else:
            expect(value is False, f"security or research boundary widened: {key}")

    checkpoint = record["decision_checkpoint"]
    expect(
        checkpoint["required_authorization_record"]
        == "phase6_load_health_runner_execution_decision.json",
        "authorization record drift",
    )
    for key in ("authorization_record_present", "runner_cache_present"):
        expect(checkpoint[key] is False, f"unsafe decision checkpoint: {key}")
    for key in ("matching_runtime_process_count", "port_1234_listener_count"):
        expect(checkpoint[key] == 0, f"unclean decision checkpoint: {key}")

    gate = record["decision_gate"]
    expect(gate["narrow_one_shot_gate_correction_authorized"] is True, "correction not authorized")
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
        == (
            "correct_prior_result_fail_closed_behavior_add_preservation_fixture_"
            "and_repin_runner_before_new_execution_decision"
        ),
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, LoadHealthRunnerExecutionReviewError) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: runner execution blocked; one-shot result-preservation correction required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
