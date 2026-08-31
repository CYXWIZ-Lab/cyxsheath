"""Validate the one-shot, metadata-only llmster archive inventory decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
SHA512 = re.compile(r"^[0-9a-f]{128}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN = {"credential", "api_token", "raw_prompt", "raw_response", "member_contents"}


class LlmsterArchiveInventoryDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterArchiveInventoryDecisionError(message)


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
        == "llmster_archive_metadata_inventory_authorized_once_extraction_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "one_read_only_identity_and_central_directory_inventory_of_the_exact_acquired_archive_without_member_content_reads_extraction_installation_or_execution",
        "scope drift",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed commit")
    expect(
        record["baseline_commit"] == "c38ff57aeba339a6c6b19b19b116ea512e288608",
        "baseline commit drift",
    )

    base = path.parent
    acquisition = record["acquisition_result"]
    expect(
        acquisition["path"] == "phase6_llmster_archive_acquisition_result.json",
        "acquisition path drift",
    )
    acquisition_path = base / acquisition["path"]
    expect(DIGEST.fullmatch(acquisition["sha256"]) is not None, "bad acquisition digest")
    expect(
        hashlib.sha256(acquisition_path.read_bytes()).hexdigest() == acquisition["sha256"],
        "acquisition digest drift",
    )
    expect(
        acquisition["status"] == "llmster_archive_acquired_verified_extraction_blocked",
        "acquisition status drift",
    )

    implementation = record["implementation"]
    expected_sources = {
        "module": {
            "path": "../llmster_archive_inventory.py",
            "bytes": 13831,
            "lines": 340,
            "sha256": "640bfa66adb9775dd670fda097a540555d8a7b2f32435859e829f83438510fc9",
        },
        "fixtures": {
            "path": "../test_llmster_archive_inventory.py",
            "bytes": 6014,
            "lines": 144,
            "sha256": "cbf350610f2c90ae9fe18b41f1aee9e0c48a4fac80fa1231ef2538e863711543",
        },
    }
    for key, expected in expected_sources.items():
        declared = implementation[key]
        expected_identity = (
            expected | {"tests_per_python": 15} if key == "fixtures" else expected
        )
        expect(declared == expected_identity, f"{key} identity drift")
    expect(implementation["fixtures"]["tests_per_python"] == 15, "fixture count drift")
    expect(
        implementation["predecision_complete_suite"]
        == {"python_3_12": "356_passed", "python_3_14": "356_passed"},
        "suite evidence drift",
    )

    identity = record["archive_identity"]
    expect(
        identity["repository_relative_path"]
        == ".replay_cache/llmster_acquisition/0.0.21-2-win32-x64.full.zip",
        "archive path drift",
    )
    expect(identity["bytes"] == 867394409, "archive size drift")
    expect(identity["sha256"] == "e6556e8edd7240c43da28aa555bac12197ba3e2199247bba773c81c6ae94170c", "archive sha256 drift")
    expect(SHA512.fullmatch(identity["sha512"]) is not None, "bad archive sha512")
    expect(
        identity["sha512"]
        == "ec13183ddc2f56d68b48fc13428e0cdca84c29bfc2b87a7aa2b9befeb7b79a8cdd3ea5a7c50d6e941fcf43545c8730f8b2bf2665b030b98e5ccfab6a3d43efff",
        "archive sha512 drift",
    )

    contract = record["metadata_contract"]
    expect(contract["member_content_read_count_maximum"] == 0, "member reads admitted")
    expect(contract["extraction_count_maximum"] == 0, "extraction admitted")
    expected_limits = {
        "maximum_entries": 50000,
        "maximum_central_directory_bytes": 33554432,
        "maximum_total_uncompressed_bytes": 4294967296,
        "maximum_entry_uncompressed_bytes": 2147483648,
        "maximum_compression_ratio_milli": 500000,
        "maximum_path_characters": 1024,
    }
    for key, value in expected_limits.items():
        expect(contract[key] == value, f"{key} drift")
    expect(contract["allowed_compression_methods"] == [0, 8], "compression scope drift")
    for key in (
        "reject_zip64", "reject_multi_disk", "reject_encrypted_members",
        "reject_symlinks_and_special_members",
        "reject_absolute_traversal_unsafe_or_case_colliding_paths",
    ):
        expect(contract[key] is True, f"guard disabled: {key}")

    one_shot = record["one_shot"]
    expect(one_shot["module"] == "Thesis.pilot_data.llmster_archive_inventory", "module drift")
    expect(one_shot["function"] == "inspect_exact_archive", "function drift")
    expect(one_shot["maximum_function_invocations"] == 1, "invocation count drift")
    expect(one_shot["authorization_consumed_at"] == "function_entry", "consumption drift")
    expect(one_shot["automatic_retry_count_maximum"] == 0, "retry admitted")
    expect(one_shot["fresh_decision_required_after_success_failure_or_interruption"] is True, "fresh decision not required")

    required = record["required_result"]
    expect(required["record_archive_unchanged"] is True, "archive preservation concealed")
    expect(required["member_paths_may_be_recorded_individually"] is False, "member paths exposed")
    expect(required["member_contents_may_be_recorded"] is False, "member contents exposed")
    expect(
        record["deferred_review"]["authenticode_verification"]
        == "not_possible_from_central_directory_metadata_and_requires_a_separate_extraction_staging_decision",
        "signature scope concealed",
    )

    gate = record["execution_gate"]
    expect(gate["metadata_inventory_authorized_once"] is True, "inventory not authorized")
    for key in (
        "member_content_reads_authorized", "archive_extraction_authorized",
        "installation_authorized", "binary_execution_authorized",
        "network_request_authorized", "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"scope widened: {key}")
    expect(
        record["next_action"]
        == "validate_and_commit_this_decision_then_invoke_the_exact_metadata_inventory_function_once_and_record_the_result",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    try:
        record = validate(arguments.path)
    except (KeyError, OSError, json.JSONDecodeError, LlmsterArchiveInventoryDecisionError) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
