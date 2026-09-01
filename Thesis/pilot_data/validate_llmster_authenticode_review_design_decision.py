"""Validate the fixture-only LLMster Authenticode review design."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


class LlmsterAuthenticodeReviewDesignError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterAuthenticodeReviewDesignError(message)


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"]
        == "llmster_authenticode_review_fixture_implementation_authorized_real_review_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "design_and_generated_fixture_implementation_of_candidate_discovery_and_authenticode_result_normalization_without_inspecting_the_retained_llmster_child_or_invoking_signature_tooling",
        "scope drift",
    )
    expect(record["baseline_commit"] == "4d1b72669280198c31c20594b18668d1f21a8390", "baseline drift")

    staged = record["accepted_staging_result"]
    expect(staged["path"] == "phase6_llmster_real_staging_execution_result.json", "staging result path drift")
    expect(hashlib.sha256((path.parent / staged["path"]).read_bytes()).hexdigest() == staged["sha256"], "staging result digest drift")
    expect(staged["content_manifest_sha256"] == "9c6600dc9a72b265d3d37abf5d499c1cd760561ac026ace2629ea452cc3b4a45", "manifest binding drift")
    expect(staged["signature_candidate_count"] == 91, "candidate count drift")
    expect(staged["signature_candidate_paths_sha256"] == "d2cfc905e98305006a5f80b65951cb1927be48a7f308ae22c10d077366faa90e", "candidate digest drift")

    boundary = record["module_boundary"]
    expect(boundary["new_policy_module"] == "Thesis.pilot_data.llmster_authenticode_review", "module drift")
    expect(boundary["role"] == "platform_independent_owned_tree_admission_candidate_discovery_result_normalization_and_aggregate_evidence", "role drift")
    for key in ("staging_module_remains_ownership_and_extraction_lifecycle_owner", "platform_adapter_deferred", "inspector_is_injected_and_fixture_fake_only_at_this_gate"):
        expect(boundary[key] is True, f"module guard disabled: {key}")
    expect(boundary["new_dependencies_allowed"] is False, "dependency admitted")

    owned = record["owned_tree_admission"]
    expect(owned["parent_repository_relative_path"] == ".replay_cache/llmster_staging", "parent drift")
    expect(owned["child_name"] == "llmster-f3895cbd1a6e421fa754386f2d144803", "child drift")
    expect(owned["expected_payload_file_count"] == 3595, "payload count drift")
    expect(owned["expected_payload_bytes"] == 1791678266, "payload bytes drift")
    expect(owned["expected_content_manifest_sha256"] == staged["content_manifest_sha256"], "owned manifest drift")
    for key in (
        "exact_parent_child_marker_and_archive_binding_required",
        "owned_root_and_payload_must_be_regular_non_links",
        "canonical_relative_paths_must_remain_under_owned_root",
        "full_payload_manifest_must_match_before_any_inspector_call",
        "candidate_file_identity_must_be_stable_across_each_inspector_call",
    ):
        expect(owned[key] is True, f"owned-tree guard disabled: {key}")

    candidates = record["candidate_contract"]
    expect(candidates["suffixes_case_insensitive"] == [".dll", ".exe", ".node", ".ps1"], "suffix drift")
    expect(candidates["canonical_order"] == "relative_posix_path_raw_utf8_bytes_ascending", "order drift")
    expect(candidates["path_digest_encoding"] == "utf8_newline_join_without_trailing_newline", "encoding drift")
    expect(candidates["expected_count"] == 91, "candidate count drift")
    expect(candidates["expected_paths_sha256"] == staged["signature_candidate_paths_sha256"], "candidate binding drift")
    expect(candidates["candidate_paths_remain_local"] is True, "candidate paths admitted")

    normalized = record["normalization_contract"]
    expect(
        {key: normalized[key] for key in ("Valid", "NotSigned", "HashMismatch", "UnknownError", "NotTrusted", "NotSupportedFileFormat", "Incompatible")}
        == {
            "Valid": "signed_valid",
            "NotSigned": "unsigned",
            "HashMismatch": "invalid",
            "UnknownError": "invalid",
            "NotTrusted": "untrusted",
            "NotSupportedFileFormat": "unsupported",
            "Incompatible": "incompatible",
        },
        "status normalization drift",
    )
    expect(normalized["unrecognized_status"] == "unknown", "unknown outcome drift")
    expect(normalized["inspector_timeout"] == "timeout", "timeout outcome drift")
    expect(normalized["inspector_error"] == "tool_error", "tool-error outcome drift")
    expect(normalized["valid_means_syntactically_valid_not_publisher_trusted"] is True, "validity overclaim")
    expect(normalized["raw_status_messages_certificate_details_and_paths_not_curated"] is True, "raw material admitted")

    aggregate = record["aggregate_result_contract"]
    for key in ("one_normalized_outcome_per_candidate_required", "outcome_counts_sum_to_candidate_count", "classification_manifest_sha256_required", "classification_manifest_rows_include_local_relative_path_and_normalized_outcome_before_hashing", "classification_manifest_rows_are_not_retained"):
        expect(aggregate[key] is True, f"aggregate guard disabled: {key}")
    for key in ("automatic_retry_count_maximum", "target_binary_launch_count_maximum", "installer_invocation_count_maximum"):
        expect(aggregate[key] == 0, f"operation admitted: {key}")

    adapter = record["future_windows_adapter_contract"]
    expect(adapter["planned_tool"] == "Get-AuthenticodeSignature", "tool drift")
    expect(adapter["planned_parameter"] == "LiteralPath", "path semantics drift")
    for key in ("windows_only", "catalog_signature_precedes_embedded_signature_when_both_exist", "tool_may_read_but_may_not_execute_candidate_files", "zero_egress_must_be_established_outside_the_cmdlet_before_real_execution", "real_tool_process_and_timeout_limits_require_separate_decision"):
        expect(adapter[key] is True, f"adapter guard disabled: {key}")
    expect(adapter["official_cmdlet_reference"].startswith("https://learn.microsoft.com/"), "cmdlet source drift")
    expect(adapter["official_status_reference"].startswith("https://learn.microsoft.com/"), "status source drift")

    for key, value in record["fixture_requirements"].items():
        expect(value is True, f"fixture requirement disabled: {key}")
    gate = record["execution_gate"]
    for key in ("policy_source_and_generated_fixture_edits_authorized", "generated_fixture_candidate_inspection_with_fake_inspector_authorized"):
        expect(gate[key] is True, f"fixture work not authorized: {key}")
    for key in ("retained_child_enumeration_or_content_read_authorized", "authenticode_tool_discovery_or_invocation_authorized", "platform_adapter_implementation_authorized", "network_request_authorized", "installation_authorized", "binary_execution_authorized", "retained_child_modification_or_removal_authorized", "benchmark_input_authorized"):
        expect(gate[key] is False, f"scope widened: {key}")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    try:
        record = validate(arguments.path)
    except (KeyError, OSError, TypeError, json.JSONDecodeError, LlmsterAuthenticodeReviewDesignError) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
