"""Validate the Phase-6 free synthetic-canary gate without raw content."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN = {"problem_statement", "raw_request", "prompt", "patch", "test_patch", "eval_script"}


class SyntheticCanaryGateError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise SyntheticCanaryGateError(message)


def check_no_raw(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN & set(value)
        expect(not found, f"{where}: forbidden raw-content keys {sorted(found)}")
        for key, child in value.items():
            check_no_raw(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_no_raw(child, f"{where}[{index}]")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_no_raw(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"] == "free_synthetic_canary_completed_benchmark_blocked",
        "unsafe status",
    )
    expect(record["decision_scope"] == "project_research_policy_not_legal_advice", "invalid scope")

    historical = record["historical_gate"]
    expect(historical["record"] == "phase6_provider_replacement_gate.json", "historical gate drift")
    expect(historical["superseded_scope"] == "synthetic_infrastructure_canary_only", "correction too broad")
    expect(historical["preserved_scope"] == "benchmark_provider_admission", "benchmark gate not preserved")
    expect(record["correction"]["benchmark_rule_unchanged"] is True, "benchmark rule weakened")

    classification = record["input_classification"]
    expect(classification["class"] == "synthetic_public_non_sensitive_non_benchmark", "unsafe input class")
    expect(classification["authored_for_canary"] is True, "fixture authorship unknown")
    for key in (
        "contains_user_or_thesis_data",
        "contains_benchmark_data",
        "contains_repository_history",
    ):
        expect(classification[key] is False, f"unsafe classification: {key}")
    expect(classification["permitted_source"] == "generated_local_fixture_only", "source boundary drift")
    prohibited = set(classification["prohibited_sources"])
    expect("candidate_events.jsonl" in prohibited and "SWE-bench rows" in prohibited, "benchmark source missing")

    provider = record["provider"]
    expect(provider["candidate_id"] == "zen-mimo-v2.5-free", "candidate drift")
    expect(provider["route"] == "opencode/mimo-v2.5-free", "route drift")
    expect(provider["cost_class"] == "free", "paid route admitted")
    expect(provider["provider_data_use"] == "may_be_used_to_improve_model", "data-use disclosure drift")
    expect(provider["data_use_accepted_for_classification"] is True, "synthetic data-use decision missing")
    expect(provider["credential_mode"] == "cyxcode_public_token_path", "credential mode drift")
    expect(provider["paid_credential_required"] is False, "paid credential overclaim")
    expect(provider["benchmark_submission"] == "blocked", "unsafe benchmark admission")

    configuration = record["configuration"]
    expect(configuration["cyxcode_commit"] == "42676876b63ed5a18957e3318272eb0d875a95fc", "CyxCode revision drift")
    expect(configuration["zen_document_commit"] == "bcf1103a8c8653acd7afdd5fc2ebd9f6e5486b3c", "Zen revision drift")
    for key in ("catalog_sha256", "provider_source_sha256", "zen_document_sha256"):
        expect(DIGEST.fullmatch(configuration[key]) is not None, f"malformed digest: {key}")
    expect(configuration["route_requires_explicit_config"] is True, "catalog drift hidden")
    expect(configuration["network_target"] == "https://opencode.ai/zen/v1", "network target drift")

    gate = record["execution_gate"]
    expect(gate["decision"] == "completed_single_attempt", "execution outcome drift")
    expect(gate["maximum_attempts"] == 1, "attempt limit weakened")
    expect(gate["paid_spend_authorized"] is False, "paid spending overclaim")
    expect(gate["benchmark_input_authorized"] is False, "benchmark input admitted")
    expect(gate["raw_artifacts"] == ".replay_cache only", "artifact boundary drift")

    outcome = record["outcome"]
    expect(outcome["synthetic_canary_executed"] is True, "completed execution missing")
    expect(outcome["completed_at"] == "2026-08-23T08:45:00Z", "completion time drift")
    expect(outcome["result"] == "proposal_captured", "canary result drift")
    expect(
        outcome["result_record"] == "../proposal_evidence/phase6_synthetic_free_canary.json",
        "result record drift",
    )
    expect(DIGEST.fullmatch(outcome["result_record_sha256"]) is not None, "malformed result digest")
    result_path = (path.parent / outcome["result_record"]).resolve()
    expect(result_path.is_file(), "result record missing")
    expect(
        hashlib.sha256(result_path.read_bytes()).hexdigest() == outcome["result_record_sha256"],
        "result record digest mismatch",
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    check_no_raw(result, "result")
    expect(result["status"] == "proposal_captured", "result status mismatch")
    expect(result["recorded_at"] == outcome["completed_at"], "result time mismatch")
    expect(result["model"] == provider["route"], "result model mismatch")
    expect(result["cost_class"] == "free", "result cost mismatch")
    expect(result["attempt"] == 1, "result attempt mismatch")
    expect(result["input_class"] == classification["class"], "result input class mismatch")
    expect(result["benchmark_input_used"] is False, "benchmark input used")
    expect(result["paid_credential_used"] is False, "paid credential used")
    expect(result["source_preserved"] is True, "source preservation failed")
    expect(outcome["benchmark_candidate_approved"] is False, "unsafe benchmark outcome")
    expect(
        outcome["next_action"] == "resolve_benchmark_provider_exposure_and_case_rights",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, SyntheticCanaryGateError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(
        f"VALID: route={record['provider']['route']}; "
        "attempts=1; synthetic_executed=1; benchmark_approved=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
