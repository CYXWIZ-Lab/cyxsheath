"""Validate the runtime-blocked Phase-6 one-shot runner correction result."""

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


class LoadHealthRunnerOneShotCorrectionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LoadHealthRunnerOneShotCorrectionError(message)


def check_forbidden(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN & set(value)
        expect(not found, f"{where}: forbidden keys {sorted(found)}")
        for key, child in value.items():
            check_forbidden(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_forbidden(child, f"{where}[{index}]")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect_evidence(base: Path, item: dict, name: str, status: str) -> dict:
    expect(item["record"] == name, f"{name}: record drift")
    expect(DIGEST.fullmatch(item["sha256"]) is not None, f"{name}: malformed digest")
    target = base / name
    expect(target.is_file(), f"{name}: missing evidence")
    expect(digest(target) == item["sha256"], f"{name}: digest drift")
    evidence = json.loads(target.read_text(encoding="utf-8"))
    expect(item["status"] == status == evidence["status"], f"{name}: status drift")
    return evidence


def identity(path: Path) -> dict:
    content = path.read_bytes()
    return {
        "bytes": len(content),
        "lines": len(content.decode("utf-8").splitlines()),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"] == "one_shot_claim_gate_corrected_fixtures_passed_runtime_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "correction_and_python_fixtures_only_no_lm_studio_runtime_authorization",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    review = expect_evidence(
        path.parent,
        record["blocking_review"],
        "phase6_load_health_runner_execution_review.json",
        "runner_execution_not_authorized_one_shot_gate_invalid",
    )
    expect(record["blocking_review"]["finding_id"] == "phase6-runner-review-001", "finding drift")
    expect(review["blocking_finding"]["one_shot_contract_satisfied"] is False, "prior block concealed")
    historical = expect_evidence(
        path.parent,
        record["historical_implementation"],
        "phase6_load_health_runner_implementation_result.json",
        "activation_runner_implemented_fixtures_passed_runtime_blocked",
    )
    historical_files = {
        item["path"]: {key: item[key] for key in ("bytes", "lines", "sha256")}
        for item in (
            historical["implementation_identity"]["modules"]
            + historical["implementation_identity"]["tests"]
        )
    }
    expected_roles = {
        "../run_local_model_load_health.py": "frozen_protocol_with_fail_closed_atomic_one_shot_claim",
        "../test_run_local_model_load_health.py": "runner_boundary_and_one_shot_preservation_fixtures",
    }
    transitions = record["code_transition"]
    expect([item["path"] for item in transitions] == list(expected_roles), "transition set drift")
    for item in transitions:
        relative = item["path"]
        expect(item["role"] == expected_roles[relative], f"role drift: {relative}")
        expect(item["previous"] == historical_files[relative], f"historical linkage drift: {relative}")
        target = (path.parent / relative).resolve()
        expect(target.is_file(), f"corrected file missing: {relative}")
        expect(item["corrected"] == identity(target), f"corrected identity drift: {relative}")
        for state in ("previous", "corrected"):
            expect(DIGEST.fullmatch(item[state]["sha256"]) is not None, f"malformed {state} digest")

    unchanged = record["unchanged_boundaries"]
    pilot = path.parent.parent
    expect(
        unchanged["monitored_process_sha256"] == digest(pilot / "monitored_process.py"),
        "monitored-process boundary drift",
    )
    expect(
        unchanged["windows_adapter_sha256"] == digest(pilot / "lm_studio_windows.py"),
        "Windows-adapter boundary drift",
    )
    expect(unchanged["new_dependency_count"] == 0, "dependency growth admitted")
    expect(unchanged["new_thread_count"] == 0, "concurrency growth admitted")
    expect(unchanged["core_sheath_change_required"] is False, "core expansion admitted")

    contract = record["corrected_one_shot_contract"]
    for key in (
        "authorization_validated_before_cache_or_claim",
        "prior_result_rejected_before_attempt_handling",
        "prior_result_bytes_preserved",
        "existing_claim_rejected_before_attempt_handling",
        "unexpected_existing_cache_rejected_without_mutation",
        "claim_retained_after_success_failure_or_crash",
        "claim_binds_authorization_and_runner_digests",
        "result_binds_claim_digest",
    ):
        expect(contract[key] is True, f"one-shot gate weakened: {key}")
    expect(
        contract["claim_primitive"]
        == "exclusive_creation_of_dedicated_cache_directory_then_exclusive_claim_file",
        "claim primitive weakened",
    )
    expect(contract["host_access_before_claim_count"] == 0, "pre-claim host access admitted")
    expect(contract["automatic_retry_count"] == 0, "automatic retry admitted")

    fixture = record["fixture_evidence"]
    for version in ("python_3_12", "python_3_14"):
        expect(fixture[version] == {"tests_run": 9, "tests_passed": 9}, f"fixture drift: {version}")
    expect(
        fixture["new_behaviors"]
        == [
            "prior_result_blocks_before_host_access_and_preserves_bytes",
            "retained_execution_claim_blocks_second_invocation",
            "unexpected_existing_cache_blocks_without_mutation",
        ],
        "fixture behavior drift",
    )
    for key in (
        "lm_studio_invocation_count",
        "model_load_command_count",
        "host_snapshot_invocation_count_in_new_fixtures",
    ):
        expect(fixture[key] == 0, f"runtime fixture operation admitted: {key}")

    security = record["security_and_research_boundary"]
    for key, value in security.items():
        if key.endswith("_count"):
            expect(value == 0, f"runtime or external operation admitted: {key}")
        else:
            expect(value is False, f"security or research boundary widened: {key}")

    runtime = record["runtime_gate"]
    expect(
        runtime["required_execution_authorization_record"]
        == "phase6_load_health_runner_execution_decision.json",
        "authorization record drift",
    )
    expect(runtime["execution_authorization_present_at_checkpoint"] is False, "authorization overclaim")
    expect(runtime["runner_cache_present_at_checkpoint"] is False, "cache checkpoint overclaim")
    expect(runtime["runtime_execution_authorized"] is False, "runtime prematurely authorized")
    expect(
        runtime["future_authorization_must_pin_corrected_runner_sha256"]
        == transitions[0]["corrected"]["sha256"],
        "future runner pin drift",
    )

    for key, value in record["known_limits"].items():
        expect(value is False, f"correction overclaim: {key}")

    gate = record["execution_gate"]
    expect(gate["one_shot_gate_correction_complete"] is True, "correction not complete")
    expect(gate["fixture_gate_passed"] is True, "fixture gate not passed")
    for key in (
        "load_health_execution_authorized",
        "execution_authorization_record_creation_authorized",
        "synthetic_canary_authorized",
        "authenticated_http_server_authorized",
        "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"]
        == "make_fresh_validator_backed_execution_decision_for_corrected_runner_or_stop",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, LoadHealthRunnerOneShotCorrectionError) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: one-shot claim gate corrected; fixtures passed; LM Studio runtime blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
