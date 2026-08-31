"""Validate the fixture-verified ZIP separator canonicalization result."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

try:
    from .validate_llmster_separator_canonicalization_decision import validate as validate_decision
except ImportError:
    from validate_llmster_separator_canonicalization_decision import validate as validate_decision


COMMIT = re.compile(r"^[0-9a-f]{40}$")


class LlmsterSeparatorCanonicalizationResultError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterSeparatorCanonicalizationResultError(message)


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"]
        == "llmster_archive_separator_canonicalization_fixture_verified_real_inventory_blocked",
        "unsafe status",
    )
    expect(
        record["result_scope"]
        == "fixture_verified_separator_canonicalization_and_historical_validator_correction_without_real_archive_reads_extraction_installation_or_execution",
        "scope drift",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["implementation_commit"]) is not None, "malformed commit")
    expect(
        record["implementation_commit"] == "c99f5cdaf0706df2fe16aca4b4212ff6989fca87",
        "implementation commit drift",
    )

    decision = record["decision"]
    expect(decision["path"] == "phase6_llmster_separator_canonicalization_decision.json", "decision path drift")
    decision_path = path.parent / decision["path"]
    expect(hashlib.sha256(decision_path.read_bytes()).hexdigest() == decision["sha256"], "decision digest drift")
    validated_decision = validate_decision(decision_path)
    expect(decision["status"] == validated_decision["status"], "decision status drift")

    expected_sources = {
        "inventory_module": {
            "path": "../llmster_archive_inventory.py", "bytes": 13980, "lines": 342,
            "sha256": "b039b81b1f6229b015f68e741d41fbf51e979de8da04b3b1e4090d78cb6e134c",
        },
        "inventory_fixtures": {
            "path": "../test_llmster_archive_inventory.py", "bytes": 9111, "lines": 208,
            "sha256": "7d8d5e8055bceca22a73f6c9e2cb2b2b1b12eb5e3d22838f0e62bc45dcda6f91",
        },
        "historical_inventory_decision_validator": {
            "path": "../validate_llmster_archive_inventory_decision.py", "bytes": 7579, "lines": 188,
            "sha256": "73f549c1e1152458b2308be57012112a6b84a0169943b6906a6d52a3af020f38",
        },
    }
    expect(record["corrected_sources"] == expected_sources, "corrected source identity drift")

    contract = record["implemented_contract"]
    for key in (
        "safe_forward_and_backslash_separators_canonicalize_to_forward_slash",
        "forward_and_backslash_spellings_produce_same_canonical_inventory_digest",
        "backslash_directory_marker_supported",
        "leading_separator_drive_traversal_empty_segment_and_unsafe_windows_names_rejected",
        "mixed_separator_casefold_and_canonical_collisions_rejected",
        "non_nfc_raw_names_rejected_without_silent_normalization",
    ):
        expect(contract[key] is True, f"contract outcome concealed: {key}")
    expect(contract["raw_member_names_retained_in_result"] is False, "raw names retained")
    for key in ("member_content_open_count", "new_dependencies", "new_runtime_modules"):
        expect(contract[key] == 0, f"implementation scope widened: {key}")

    validation = record["validation"]
    expect(validation["inventory_fixture_tests_per_python"] == 27, "fixture count drift")
    expect(validation["decision_mutation_tests_per_python"] == 10, "mutation count drift")
    expect(validation["pre_result_complete_suite_python_3_12"] == "398_passed", "Python 3.12 suite drift")
    expect(validation["pre_result_complete_suite_python_3_14"] == "398_passed", "Python 3.14 suite drift")
    expect(validation["historical_inventory_decision_valid"] is True, "historical decision invalid")
    expect(validation["historical_inventory_result_valid"] is True, "historical result invalid")

    for key, count in record["real_archive_operations"].items():
        expect(count == 0, f"real archive operation admitted: {key}")

    gate = record["result_gate"]
    expect(gate["fixture_implementation_accepted"] is True, "fixture result not accepted")
    expect(gate["fresh_validator_backed_inventory_decision_required"] is True, "fresh decision not required")
    for key in (
        "fresh_real_inventory_authorized", "archive_extraction_authorized",
        "installation_authorized", "binary_execution_authorized", "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"scope widened: {key}")
    expect(
        record["next_action"]
        == "review_this_corrected_checkpoint_then_make_a_separate_one_shot_real_metadata_inventory_decision_if_the_boundary_is_accepted",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    try:
        record = validate(arguments.path)
    except (KeyError, OSError, json.JSONDecodeError, LlmsterSeparatorCanonicalizationResultError) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
