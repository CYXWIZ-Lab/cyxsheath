"""Validate the fixture-only ZIP separator canonicalization decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


class LlmsterSeparatorCanonicalizationDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterSeparatorCanonicalizationDecisionError(message)


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"]
        == "llmster_archive_separator_canonicalization_fixtures_authorized_real_inventory_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "fixture_only_correction_of_zip_member_separator_canonicalization_without_reading_the_real_archive_or_authorizing_extraction_installation_or_execution",
        "scope drift",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed commit")
    expect(
        record["baseline_commit"] == "58d6ff5e3cf2543e8092d46b5dd4d85bf4631869",
        "baseline commit drift",
    )

    base = path.parent
    prior = record["prior_result"]
    expect(prior["path"] == "phase6_llmster_archive_inventory_result.json", "prior path drift")
    expect(DIGEST.fullmatch(prior["sha256"]) is not None, "bad prior digest")
    expect(
        hashlib.sha256((base / prior["path"]).read_bytes()).hexdigest() == prior["sha256"],
        "prior result digest drift",
    )
    expect(prior["status"] == "llmster_archive_metadata_inventory_rejected_extraction_blocked", "prior status drift")
    expect(prior["error_code"] == "member_backslash_rejected", "prior error drift")

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
        declared = record["current_sources"][key]
        expect(declared == expected, f"{key} identity drift")

    boundary = record["boundary_decision"]
    expect(boundary["owner"] == "existing_llmster_archive_inventory_path_policy", "owner drift")
    expect(boundary["new_module_allowed"] is False, "new module admitted")
    expect(boundary["new_dependency_allowed"] is False, "dependency admitted")
    expect(boundary["backslash_meaning"] == "path_separator_equivalent_to_forward_slash", "separator meaning drift")
    expect(boundary["canonical_separator"] == "/", "canonical separator drift")
    expect(boundary["directory_marker_inputs"] == ["/", "\\"], "directory marker drift")
    expect(boundary["unicode_policy"] == "require_raw_nfc_and_do_not_silently_normalize_unicode", "unicode policy drift")
    expect(boundary["canonical_output_retains_raw_member_name"] is False, "raw name retention admitted")
    expect(len(boundary["required_rejections"]) == 7, "required rejection set drift")

    fixtures = record["fixture_requirements"]
    for key, value in fixtures.items():
        expect(value is True, f"fixture requirement disabled: {key}")

    gate = record["execution_gate"]
    expect(gate["source_and_fixture_edits_authorized"] is True, "source edits not authorized")
    expect(gate["generated_fixture_execution_authorized"] is True, "fixtures not authorized")
    for key in (
        "real_archive_identity_read_authorized", "real_archive_central_directory_read_authorized",
        "fresh_real_inventory_authorized", "archive_extraction_authorized",
        "installation_authorized", "binary_execution_authorized",
        "network_request_authorized", "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"scope widened: {key}")
    expect(
        record["next_action"]
        == "implement_and_fixture_test_only_then_record_the_corrected_source_identity_before_any_fresh_real_inventory_decision",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    try:
        record = validate(arguments.path)
    except (KeyError, OSError, json.JSONDecodeError, LlmsterSeparatorCanonicalizationDecisionError) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
