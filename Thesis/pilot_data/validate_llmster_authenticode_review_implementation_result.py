"""Validate the fixture-only LLMster Authenticode policy implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

try:
    from .validate_llmster_authenticode_review_design_decision import validate as validate_design
except ImportError:
    from validate_llmster_authenticode_review_design_decision import validate as validate_design


DIGEST = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN = {
    "absolute_path",
    "candidate_path",
    "candidate_paths",
    "classification_rows",
    "raw_status",
    "raw_status_message",
    "certificate",
    "certificate_subject",
    "thumbprint",
    "hostname",
    "username",
    "credential",
    "api_token",
}


class LlmsterAuthenticodeReviewImplementationError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterAuthenticodeReviewImplementationError(message)


def check_forbidden(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN & set(value)
        expect(not found, f"{where}: forbidden keys {sorted(found)}")
        for key, child in value.items():
            check_forbidden(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_forbidden(child, f"{where}[{index}]")


def file_identity(path: Path) -> dict[str, int | str]:
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
    expect(record["status"] == "llmster_authenticode_review_policy_implemented_generated_fixtures_passed_real_review_blocked", "unsafe status")
    expect(record["decision_scope"] == "dependency_free_platform_independent_authenticode_review_policy_and_generated_owned_tree_fixtures_only_without_retained_child_access_or_signature_tooling", "scope drift")
    expect(record["baseline_commit"] == "cc02e5999a507a1fe72ca8a1ad22b85bd5827b42", "baseline drift")

    reviewed = record["reviewed_decision"]
    expect(reviewed["record"] == "phase6_llmster_authenticode_review_design_decision.json", "design record drift")
    decision_path = path.parent / reviewed["record"]
    expect(DIGEST.fullmatch(reviewed["sha256"]) is not None, "malformed design digest")
    expect(hashlib.sha256(decision_path.read_bytes()).hexdigest() == reviewed["sha256"], "design digest drift")
    decision = validate_design(decision_path)
    expect(decision["status"] == reviewed["status"], "design status drift")
    expect(decision["execution_gate"]["policy_source_and_generated_fixture_edits_authorized"] is True, "fixture authority missing")
    expect(decision["execution_gate"]["retained_child_enumeration_or_content_read_authorized"] is False, "design boundary widened")

    sources = record["source_identity"]
    expect([item["path"] for item in sources] == ["../llmster_archive_staging.py", "../llmster_authenticode_review.py", "../test_llmster_authenticode_review.py"], "source set drift")
    expect([item["change"] for item in sources] == ["unchanged_reused_ownership_invariant", "new", "new"], "source classification drift")
    for item in sources:
        expect(DIGEST.fullmatch(item["sha256"]) is not None, f"malformed source digest: {item['path']}")
        target = (path.parent / item["path"]).resolve()
        expect(target.is_file(), f"source missing: {item['path']}")
        expect({key: item[key] for key in ("bytes", "lines", "sha256")} == file_identity(target), f"source identity drift: {item['path']}")

    boundary = record["module_boundary"]
    for key in ("staging_module_remains_marker_and_extraction_lifecycle_owner", "policy_module_owns_tree_admission_candidate_discovery_normalization_and_aggregate_evidence", "frozen_staging_ownership_verifier_reused_without_source_change", "inspector_is_injected_typed_and_fake_in_fixtures"):
        expect(boundary[key] is True, f"module ownership weakened: {key}")
    for key in ("windows_process_adapter_added", "signature_tool_reference_or_invocation_added_to_policy", "installation_or_runtime_entrypoint_added", "sheath_core_changed", "cyxcode_changed"):
        expect(boundary[key] is False, f"module expansion admitted: {key}")
    expect(boundary["new_dependency_count"] == 0, "dependency growth admitted")
    expect(boundary["new_thread_count"] == 0, "concurrency growth admitted")

    expect(record["design_refinement"] == {
        "aggregate_operation_ceilings_remain_required_for_later_execution_evidence": True,
        "policy_result_does_not_claim_adapter_network_launch_install_or_retry_counts": True,
        "reason": "an_injected_policy_callable_cannot_observe_or_attest_to_platform_adapter_internals",
    }, "design refinement drift")

    for key, value in record["verified_behaviors"].items():
        expect(value is True, f"verified behavior weakened: {key}")
    expect(record["normalization_contract"] == {
        "Valid": "signed_valid",
        "NotSigned": "unsigned",
        "HashMismatch": "invalid",
        "UnknownError": "invalid",
        "NotTrusted": "untrusted",
        "NotSupportedFileFormat": "unsupported",
        "Incompatible": "incompatible",
        "unrecognized_status": "unknown",
        "inspector_timeout": "timeout",
        "inspector_error": "tool_error",
    }, "normalization drift")

    fixtures = record["fixture_evidence"]
    for version in ("python_3_12", "python_3_14"):
        expect(fixtures[version] == {"tests_run": 525, "tests_passed": 525}, f"full fixture drift: {version}")
    expect(fixtures["focused_policy_tests"] == 14, "policy fixture count drift")
    expect(fixtures["implementation_result_tests"] == 10, "result fixture count drift")
    expect(fixtures["generated_owned_tree_fixture_authorized"] is True, "fixture authority missing")
    for key, value in fixtures.items():
        if key.endswith("_count"):
            expect(value == 0, f"operation admitted: {key}")

    gate = record["decision_gate"]
    for key in ("platform_independent_review_policy_complete", "generated_fixture_gate_passed"):
        expect(gate[key] is True, f"implementation gate missing: {key}")
    for key in ("retained_child_enumeration_or_content_read_authorized", "windows_adapter_implementation_authorized", "authenticode_tool_discovery_or_invocation_authorized", "installation_authorized", "binary_execution_authorized", "network_request_authorized", "retained_child_modification_or_removal_authorized", "benchmark_input_authorized"):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(gate["next_action"] == "separately_design_and_fixture_test_the_windows_literal_path_timeout_and_zero_egress_adapter_before_any_retained_child_access_or_signature_tool_invocation", "next action drift")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    arguments = parser.parse_args()
    try:
        record = validate(arguments.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, LlmsterAuthenticodeReviewImplementationError) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
