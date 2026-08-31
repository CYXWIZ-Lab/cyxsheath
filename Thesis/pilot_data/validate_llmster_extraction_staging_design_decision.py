"""Validate the fixture-only LLMster extraction-staging design."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


class LlmsterExtractionStagingDesignError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterExtractionStagingDesignError(message)


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(record["status"] == "llmster_owned_extraction_staging_fixture_implementation_authorized_real_extraction_blocked", "unsafe status")
    expect(record["baseline_commit"] == "2cf7719aa56153ab8eeba5594dfce80e5b50115d", "baseline commit drift")
    inventory = record["accepted_inventory"]
    expect(inventory["path"] == "phase6_llmster_archive_inventory_v2_result.json", "inventory path drift")
    expect(hashlib.sha256((path.parent / inventory["path"]).read_bytes()).hexdigest() == inventory["sha256"], "inventory digest drift")
    expect(inventory["entry_count"] == 3614, "entry count drift")
    expect(inventory["total_uncompressed_bytes"] == 1791678266, "uncompressed total drift")
    expect(inventory["canonical_inventory_sha256"] == "bea264bc3b7f2368f485a40591ad9e4ef831690aeb0f55482df5ccf15ddac3cd", "inventory identity drift")

    boundary = record["module_boundary"]
    expect(boundary["new_module"] == "Thesis.pilot_data.llmster_archive_staging", "module drift")
    expect(boundary["role"] == "exclusive_owned_staging_lifecycle_and_streamed_extraction_only", "role drift")
    expect(boundary["inventory_module_remains_metadata_policy_owner"] is True, "metadata ownership drift")
    expect(boundary["installation_or_runtime_responsibility_added"] is False, "runtime responsibility admitted")
    expect(boundary["new_dependencies_allowed"] is False, "dependency admitted")

    ownership = record["ownership_contract"]
    expect(ownership["parent_repository_relative_path"] == ".replay_cache/llmster_staging", "parent drift")
    expect(ownership["child_name_pattern"] == "llmster-[0-9a-f]{32}", "child pattern drift")
    expect(ownership["ownership_marker"] == ".cyxsheath-staging-owner.json", "marker drift")
    for key in (
        "parent_must_exist_be_absolute_and_not_be_symlink", "child_must_not_exist",
        "child_created_exclusively", "ownership_marker_created_exclusively_before_member_writes",
        "rollback_requires_exact_parent_child_pattern_and_matching_marker",
        "rollback_may_remove_only_the_owned_child", "archive_and_parent_must_be_retained",
    ):
        expect(ownership[key] is True, f"ownership guard disabled: {key}")

    storage = record["storage_and_write_contract"]
    expect(storage["declared_uncompressed_bytes"] == 1791678266, "declared bytes drift")
    expect(storage["minimum_free_bytes_after"] == 4294967296, "final reserve drift")
    expect(storage["minimum_free_bytes_before"] == 6086645562, "preflight reserve drift")
    expect(storage["stream_chunk_bytes_maximum"] == 8388608, "chunk ceiling drift")
    expect(storage["existing_destination_overwrite_count_maximum"] == 0, "overwrite admitted")
    for key in (
        "canonical_destination_must_remain_under_owned_child", "links_and_special_members_rejected",
        "written_file_size_must_match_declared_size", "total_written_bytes_must_match_inventory_total",
        "per_file_sha256_and_canonical_content_manifest_digest_required",
    ):
        expect(storage[key] is True, f"write guard disabled: {key}")
    expect(storage["raw_member_names_retained_in_curated_result"] is False, "raw names retained")

    outcome = record["success_and_failure_contract"]
    expect(outcome["success_retains_owned_staging_for_separate_signature_review"] is True, "success lifecycle drift")
    expect(outcome["failure_removes_owned_staging_after_marker_verification"] is True, "failure cleanup disabled")
    expect(outcome["cleanup_failure_must_be_reported_and_cannot_be_concealed"] is True, "cleanup failure concealed")
    for key in ("automatic_retry_count_maximum", "binary_launch_count_maximum", "installer_invocation_count_maximum", "network_request_count_maximum"):
        expect(outcome[key] == 0, f"operation admitted: {key}")

    signature = record["signature_review_boundary"]
    expect(signature["candidate_suffixes"] == [".dll", ".exe", ".node", ".ps1"], "signature suffix drift")
    for key in ("signature_verification_occurs_only_after_separate_real_staging_decision", "signature_tool_may_not_execute_target_binaries", "unsigned_invalid_unknown_and_tool_error_are_distinct_results", "metadata_inventory_does_not_claim_authenticode"):
        expect(signature[key] is True, f"signature guard disabled: {key}")

    for key, value in record["fixture_requirements"].items():
        expect(value is True, f"fixture requirement disabled: {key}")
    gate = record["execution_gate"]
    expect(gate["source_and_generated_fixture_edits_authorized"] is True, "source edits not authorized")
    expect(gate["generated_fixture_extraction_authorized"] is True, "fixtures not authorized")
    for key in ("real_archive_identity_or_member_read_authorized", "real_archive_extraction_authorized", "authenticode_tool_invocation_authorized", "installation_authorized", "binary_execution_authorized", "network_request_authorized", "benchmark_input_authorized"):
        expect(gate[key] is False, f"scope widened: {key}")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("path", type=Path); arguments = parser.parse_args()
    try:
        record = validate(arguments.path)
    except (KeyError, OSError, json.JSONDecodeError, LlmsterExtractionStagingDesignError) as error:
        print(f"INVALID: {error}"); return 1
    print(f"VALID: {record['status']}"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
