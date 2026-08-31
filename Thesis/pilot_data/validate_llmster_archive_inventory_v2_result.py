"""Validate the accepted metadata-only llmster inventory-v2 result."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


class LlmsterArchiveInventoryV2ResultError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterArchiveInventoryV2ResultError(message)


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(record["status"] == "llmster_archive_metadata_inventory_v2_accepted_extraction_blocked", "unsafe status")
    expect(record["baseline_commit"] == "c956a3f55c4b94986aa53f0134913206660370b2", "baseline commit drift")
    authorization = record["authorization"]
    expect(authorization["record"] == "phase6_llmster_archive_inventory_v2_decision.json", "authorization path drift")
    expect(hashlib.sha256((path.parent / authorization["record"]).read_bytes()).hexdigest() == authorization["sha256"], "authorization digest drift")
    expect(authorization["validated_immediately_before_function_call"] is True, "prevalidation concealed")
    expect(authorization["consumed"] is True, "consumption concealed")
    expect(authorization["fresh_function_invocation_count"] == 1, "invocation drift")
    expect(authorization["automatic_retry_count"] == 0, "retry admitted")

    archive = record["archive"]
    expect(archive["bytes"] == 867394409, "archive size drift")
    expect(archive["sha256"] == "e6556e8edd7240c43da28aa555bac12197ba3e2199247bba773c81c6ae94170c", "archive identity drift")
    expect(archive["unchanged_by_inventory"] is True, "archive mutation concealed")

    aggregate = record["aggregate_inventory"]
    expect(aggregate["entry_count"] == 3614, "entry count drift")
    expect(aggregate["file_count"] == 3595, "file count drift")
    expect(aggregate["directory_count"] == 19, "directory count drift")
    expect(aggregate["file_count"] + aggregate["directory_count"] == aggregate["entry_count"], "entry partition drift")
    expect(aggregate["central_directory_bytes"] == 548019, "central directory drift")
    expect(aggregate["total_compressed_bytes"] == 866356173, "compressed total drift")
    expect(aggregate["total_uncompressed_bytes"] == 1791678266, "uncompressed total drift")
    expect(aggregate["maximum_entry_uncompressed_bytes"] == 533257912, "maximum entry drift")
    expect(aggregate["maximum_compression_ratio_milli"] == 16075, "ratio drift")
    expect(aggregate["compression_methods"] == [0, 8], "compression method drift")
    expect(aggregate["top_level_components"] == [".bundle", "llmster.exe"], "top-level scope drift")
    expect(
        aggregate["sensitive_suffix_counts"]
        == [
            {"suffix": ".bat", "count": 4}, {"suffix": ".cmd", "count": 2},
            {"suffix": ".dll", "count": 64}, {"suffix": ".exe", "count": 15},
            {"suffix": ".js", "count": 15}, {"suffix": ".node", "count": 11},
            {"suffix": ".ps1", "count": 1}, {"suffix": ".sh", "count": 2},
        ],
        "sensitive suffix counts drift",
    )
    expect(aggregate["canonical_inventory_sha256"] == "bea264bc3b7f2368f485a40591ad9e4ef831690aeb0f55482df5ccf15ddac3cd", "inventory digest drift")
    expect(aggregate["sensitive_paths_sha256"] == "76f060349072b4f5eee98f1fb8b7779a5b5a689f4d0aa40cf8313f67b07c6a43", "sensitive digest drift")

    for key, count in record["operation_counts"].items():
        expect(count == 0, f"operation admitted: {key}")
    interpretation = record["interpretation"]
    expect(interpretation["metadata_contract_passed"] is True, "acceptance concealed")
    for key in (
        "archive_safe_to_extract_claimed", "authenticode_verified_claimed",
        "individual_member_paths_retained", "installation_overwrite_scope_claimed",
        "runtime_health_claimed", "model_quality_claimed",
    ):
        expect(interpretation[key] is False, f"overclaim: {key}")
    gate = record["result_gate"]
    expect(gate["inventory_v2_accepted"] is True, "result not accepted")
    expect(gate["separate_owned_extraction_staging_decision_required"] is True, "staging decision not required")
    for key in ("same_authorization_reusable", "archive_extraction_authorized", "installation_authorized", "binary_execution_authorized", "benchmark_input_authorized"):
        expect(gate[key] is False, f"scope widened: {key}")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    try:
        record = validate(arguments.path)
    except (KeyError, OSError, json.JSONDecodeError, LlmsterArchiveInventoryV2ResultError) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
