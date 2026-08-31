"""Validate the fresh one-shot llmster archive inventory-v2 decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


COMMIT = re.compile(r"^[0-9a-f]{40}$")


class LlmsterArchiveInventoryV2DecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterArchiveInventoryV2DecisionError(message)


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(record["status"] == "llmster_archive_metadata_inventory_v2_authorized_once_extraction_blocked", "unsafe status")
    expect(
        record["decision_scope"]
        == "one_fresh_identity_and_central_directory_inventory_using_fixture_verified_separator_canonicalization_without_member_content_reads_extraction_installation_or_execution",
        "scope drift",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed commit")
    expect(record["baseline_commit"] == "c57643930627817935791c00198bd481c98ebcbb", "baseline commit drift")

    base = path.parent
    prior = record["prior_consumed_result"]
    expect(prior["path"] == "phase6_llmster_archive_inventory_result.json", "prior path drift")
    expect(hashlib.sha256((base / prior["path"]).read_bytes()).hexdigest() == prior["sha256"], "prior digest drift")
    expect(prior["status"] == "llmster_archive_metadata_inventory_rejected_extraction_blocked", "prior status drift")
    expect(prior["prior_function_invocation_count"] == 1, "prior invocation drift")
    expect(prior["reusable"] is False, "prior authorization reused")

    correction = record["canonicalization_result"]
    expect(correction["path"] == "phase6_llmster_separator_canonicalization_result.json", "correction path drift")
    expect(hashlib.sha256((base / correction["path"]).read_bytes()).hexdigest() == correction["sha256"], "correction digest drift")
    expect(correction["status"] == "llmster_archive_separator_canonicalization_fixture_verified_real_inventory_blocked", "correction status drift")
    expect(correction["implementation_commit"] == "c99f5cdaf0706df2fe16aca4b4212ff6989fca87", "correction commit drift")

    expected_implementation = {
        "module": {
            "path": "../llmster_archive_inventory.py", "bytes": 13980, "lines": 342,
            "sha256": "b039b81b1f6229b015f68e741d41fbf51e979de8da04b3b1e4090d78cb6e134c",
        },
        "fixtures": {
            "path": "../test_llmster_archive_inventory.py", "bytes": 9111, "lines": 208,
            "sha256": "7d8d5e8055bceca22a73f6c9e2cb2b2b1b12eb5e3d22838f0e62bc45dcda6f91",
            "tests_per_python": 27,
        },
        "predecision_complete_suite": {"python_3_12": "408_passed", "python_3_14": "408_passed"},
    }
    expect(record["implementation"] == expected_implementation, "implementation identity drift")

    identity = record["archive_identity"]
    expect(identity["repository_relative_path"] == ".replay_cache/llmster_acquisition/0.0.21-2-win32-x64.full.zip", "archive path drift")
    expect(identity["bytes"] == 867394409, "archive size drift")
    expect(identity["sha256"] == "e6556e8edd7240c43da28aa555bac12197ba3e2199247bba773c81c6ae94170c", "archive sha256 drift")
    expect(identity["sha512"] == "ec13183ddc2f56d68b48fc13428e0cdca84c29bfc2b87a7aa2b9befeb7b79a8cdd3ea5a7c50d6e941fcf43545c8730f8b2bf2665b030b98e5ccfab6a3d43efff", "archive sha512 drift")

    contract = record["metadata_contract"]
    expect(contract["separator_policy"] == "safe_forward_and_backslash_separators_canonicalize_to_forward_slash_before_segment_and_collision_checks", "separator policy drift")
    expect(contract["raw_member_names_retained"] is False, "raw names retained")
    expect(contract["member_content_read_count_maximum"] == 0, "member reads admitted")
    expect(contract["extraction_count_maximum"] == 0, "extraction admitted")
    expected_limits = {
        "maximum_entries": 50000, "maximum_central_directory_bytes": 33554432,
        "maximum_total_uncompressed_bytes": 4294967296,
        "maximum_entry_uncompressed_bytes": 2147483648,
        "maximum_compression_ratio_milli": 500000, "maximum_path_characters": 1024,
    }
    for key, value in expected_limits.items():
        expect(contract[key] == value, f"limit drift: {key}")
    expect(contract["allowed_compression_methods"] == [0, 8], "compression scope drift")
    expect(contract["reject_zip64_multi_disk_encryption_links_special_members"] is True, "archive guards disabled")
    expect(contract["reject_absolute_traversal_empty_unsafe_non_nfc_or_colliding_paths"] is True, "path guards disabled")

    one_shot = record["one_shot"]
    expect(one_shot["module"] == "Thesis.pilot_data.llmster_archive_inventory", "module drift")
    expect(one_shot["function"] == "inspect_exact_archive", "function drift")
    expect(one_shot["fresh_function_invocation_count_maximum"] == 1, "fresh invocation drift")
    expect(one_shot["total_historical_function_invocation_count_after_maximum"] == 2, "total invocation drift")
    expect(one_shot["authorization_consumed_at"] == "function_entry", "consumption drift")
    expect(one_shot["automatic_retry_count_maximum"] == 0, "retry admitted")
    expect(one_shot["fresh_decision_required_after_success_failure_or_interruption"] is True, "fresh decision not required")

    required = record["required_result"]
    expect(required["record_archive_unchanged"] is True, "archive preservation concealed")
    expect(required["individual_raw_or_canonical_member_paths_may_be_recorded"] is False, "member paths exposed")
    expect(required["member_contents_may_be_recorded"] is False, "member contents exposed")

    gate = record["execution_gate"]
    expect(gate["metadata_inventory_v2_authorized_once"] is True, "inventory not authorized")
    for key in (
        "member_content_reads_authorized", "archive_extraction_authorized", "installation_authorized",
        "binary_execution_authorized", "network_request_authorized", "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"scope widened: {key}")
    expect(record["next_action"] == "validate_commit_and_revalidate_this_decision_then_invoke_inspect_exact_archive_once_and_record_the_result_without_retry", "next action drift")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    try:
        record = validate(arguments.path)
    except (KeyError, OSError, json.JSONDecodeError, LlmsterArchiveInventoryV2DecisionError) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
