"""Validate the accepted one-shot real LLMster staging result."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from .validate_llmster_real_staging_execution_decision import (
        validate as validate_decision,
    )
except ImportError:
    from validate_llmster_real_staging_execution_decision import (
        validate as validate_decision,
    )


FORBIDDEN = {
    "hostname",
    "machine_id",
    "serial_number",
    "username",
    "credential",
    "api_token",
    "absolute_path",
    "raw_member_name",
    "raw_member_names",
    "member_path",
    "member_paths",
    "member_content",
    "member_contents",
}


class LlmsterRealStagingExecutionResultError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterRealStagingExecutionResultError(message)


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
    expect(
        record["status"]
        == "llmster_real_archive_owned_staging_accepted_signature_installation_execution_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "result_of_one_consumed_exact_stage_archive_invocation_with_aggregate_content_evidence_and_retained_owned_child_without_signature_tooling_installation_or_execution",
        "scope drift",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(
        record["baseline_commit"] == "fc03ec30c3da366a011d8ea0d89a46dafd0094b7",
        "baseline commit drift",
    )

    authorization = record["authorization"]
    expect(
        authorization["record"] == "phase6_llmster_real_staging_execution_decision.json",
        "authorization record drift",
    )
    decision_path = path.parent / authorization["record"]
    expect(
        hashlib.sha256(decision_path.read_bytes()).hexdigest() == authorization["sha256"],
        "authorization digest drift",
    )
    decision = validate_decision(decision_path, enforce_live_preconditions=False)
    expect(decision["status"] == authorization["status"], "authorization status drift")
    for key in ("validated_immediately_before_consumed_call", "consumed"):
        expect(authorization[key] is True, f"authorization state concealed: {key}")
    expect(authorization["stage_archive_function_invocation_count"] == 1, "invocation count drift")
    expect(authorization["automatic_retry_count"] == 0, "retry admitted")
    expect(authorization["further_staging_authorized"] is False, "further staging admitted")

    deviation = record["pre_function_command_deviation"]
    expect(deviation["occurred"] is True, "pre-function deviation concealed")
    expect(deviation["code"] == "python_capture_command_quote_parse_error", "deviation code drift")
    for key in ("stage_archive_function_entry_reached", "authorization_consumed", "owned_child_created"):
        expect(deviation[key] is False, f"pre-function side effect concealed: {key}")
    expect(deviation["impact"] == "none_on_archive_or_staging_state", "deviation impact drift")

    execution = record["execution"]
    expect(execution["python_version"] == "3.12", "Python version drift")
    expect(execution["started_at"] == "2026-09-01T06:27:52Z", "start time drift")
    expect(execution["completed_at"] == "2026-09-01T06:28:22Z", "completion time drift")
    expect(execution["elapsed_seconds_rounded"] == 30, "elapsed time drift")
    expect(execution["outcome"] == "accepted", "accepted outcome concealed")
    expect(execution["normalised_error_code"] is None, "unexpected error retained")
    expect(execution["archive_source_stability_verified"] is True, "source stability concealed")
    expect(execution["ownership_marker_matches"] is True, "marker mismatch concealed")

    call = decision["one_shot_call"]
    archive = record["archive"]
    for key in ("repository_relative_path", "bytes", "sha256", "sha512"):
        decision_key = "archive_path" if key == "repository_relative_path" else f"expected_{key}"
        expect(archive[key] == call[decision_key], f"archive linkage drift: {key}")
    expect(archive["exact_identity_verified_inside_stage_archive"] is True, "identity check concealed")
    expect(archive["unchanged_by_staging"] is True, "archive mutation concealed")

    owned = record["owned_staging"]
    target = decision["owned_target"]
    expect(owned["parent_repository_relative_path"] == target["parent_repository_relative_path"], "parent drift")
    expect(owned["child_name"] == target["child_name"], "child drift")
    expect(owned["ownership_marker"] == target["ownership_marker"], "marker path drift")
    for key in ("owned_child_present", "ownership_marker_present", "ownership_marker_matches", "successful_child_retained"):
        expect(owned[key] is True, f"owned state concealed: {key}")
    expect(owned["owned_child_is_symlink"] is False, "owned child symlink admitted")
    expect(owned["ownership_marker_bytes"] == 190, "marker size drift")
    expect(owned["parent_child_count"] == 1, "parent child count drift")

    staged = record["staging_result"]
    inventory = decision["accepted_inventory"]
    expect(staged["entry_count"] == inventory["entry_count"] == 3614, "entry count drift")
    expect(staged["file_count"] == inventory["file_count"] == 3595, "file count drift")
    expect(staged["explicit_directory_count"] == inventory["directory_count"] == 19, "directory count drift")
    expect(staged["total_written_bytes"] == inventory["total_uncompressed_bytes"] == 1_791_678_266, "written total drift")
    expect(staged["content_manifest_sha256"] == "9c6600dc9a72b265d3d37abf5d499c1cd760561ac026ace2629ea452cc3b4a45", "manifest digest drift")
    expect(staged["signature_candidate_count"] == 91, "candidate count drift")
    expect(staged["signature_candidate_paths_sha256"] == "d2cfc905e98305006a5f80b65951cb1927be48a7f308ae22c10d077366faa90e", "candidate digest drift")
    expect(staged["existing_destination_overwrite_count"] == 0, "overwrite admitted")

    audit = record["retained_child_metadata_audit"]
    expect(audit["observed_payload_file_count"] == staged["file_count"], "observed file count drift")
    expect(audit["observed_filesystem_directory_count"] == 256, "filesystem directory count drift")
    expect(audit["observed_payload_bytes"] == staged["total_written_bytes"], "observed payload drift")
    expect(audit["observed_link_count"] == 0, "link admitted")
    expect(audit["observed_other_special_count"] == 0, "special object admitted")
    expect(audit["member_paths_or_contents_retained_in_record"] is False, "member material retained")

    storage = record["storage_result"]
    expect(storage["free_bytes_before_call"] == 152_506_544_128, "pre-call storage drift")
    expect(storage["free_bytes_after_call"] == 150_707_167_232, "post-call storage drift")
    expect(storage["observed_volume_free_delta_bytes"] == storage["free_bytes_before_call"] - storage["free_bytes_after_call"], "storage delta drift")
    expect(storage["logical_payload_bytes"] == staged["total_written_bytes"], "logical payload drift")
    expect(storage["free_delta_minus_logical_payload_bytes"] == 7_698_630, "delta difference drift")
    expect(storage["delta_difference_attributed_exclusively_to_staging"] is False, "storage attribution overclaim")
    expect(storage["minimum_free_bytes_after"] == 4_294_967_296, "final reserve weakened")
    expect(storage["free_bytes_after_call"] >= storage["minimum_free_bytes_after"], "final storage gate failed")
    expect(storage["final_storage_gate_passed"] is True, "storage acceptance concealed")

    expected_operations = {
        "stage_archive_function_invocations": 1,
        "real_archive_member_file_streams": 3595,
        "payload_files_written": 3595,
        "ownership_markers_written": 1,
        "signature_tool_invocations": 0,
        "installations": 0,
        "binary_executions": 0,
        "network_requests": 0,
        "benchmark_inputs": 0,
        "automatic_retries": 0,
    }
    expect(record["operation_counts"] == expected_operations, "operation count drift")

    interpretation = record["interpretation"]
    expect(interpretation["exact_owned_staging_contract_passed"] is True, "staging acceptance concealed")
    expect(interpretation["aggregate_content_evidence_complete"] is True, "content evidence concealed")
    for key in (
        "authenticode_verified_claimed",
        "archive_safe_for_installation_claimed",
        "runtime_health_claimed",
        "model_quality_claimed",
        "individual_member_paths_or_contents_curated",
    ):
        expect(interpretation[key] is False, f"interpretation overclaim: {key}")

    fixtures = record["fixture_evidence"]
    expected_fixture = {
        "pre_result_tests_passed": 479,
        "result_tests_passed": 10,
        "post_result_tests_passed": 489,
    }
    for version in ("python_3_12", "python_3_14"):
        expect(fixtures[version] == expected_fixture, f"fixture evidence drift: {version}")
    expect(
        fixtures["validation_execution_deviation"]
        == {
            "initial_parallel_python_3_14_full_run_passed": False,
            "initial_parallel_python_3_14_existing_monitored_process_errors": 3,
            "focused_sequential_monitored_process_tests_passed": 8,
            "sequential_python_3_14_full_tests_passed": 489,
            "staging_function_reinvoked": False,
            "interpretation": "transient_parallel_host_contention_not_staging_or_result_regression",
        },
        "validation deviation drift",
    )

    expect(
        record["live_reuse_check"]
        == {
            "decision_live_validation_after_result_passed": False,
            "rejection_code": "live staging parent not empty",
            "historical_decision_validation_passed": True,
            "result_validation_passed": True,
        },
        "live reuse check drift",
    )

    gate = record["result_gate"]
    expect(gate["real_staging_accepted"] is True, "result gate concealed")
    expect(gate["authorization_consumed"] is True, "consumption gate concealed")
    expect(gate["separate_nonexecuting_signature_review_decision_required"] is True, "signature decision bypassed")
    for key in (
        "same_authorization_reusable",
        "successful_owned_child_may_be_removed",
        "authenticode_tool_invocation_authorized",
        "installation_authorized",
        "binary_execution_authorized",
        "network_request_authorized",
        "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"]
        == "design_and_fixture_test_a_separate_nonexecuting_authenticode_review_boundary_before_invoking_any_signature_tool",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.path)
    except (
        KeyError,
        OSError,
        TypeError,
        json.JSONDecodeError,
        LlmsterRealStagingExecutionResultError,
    ) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
