"""Validate the consumed, fail-closed llmster archive inventory result."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

try:
    from .validate_llmster_archive_inventory_decision import validate as validate_decision
except ImportError:
    from validate_llmster_archive_inventory_decision import validate as validate_decision


DIGEST = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN = {"credential", "api_token", "raw_prompt", "raw_response", "member_path", "member_contents"}


class LlmsterArchiveInventoryResultError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterArchiveInventoryResultError(message)


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
        record["status"] == "llmster_archive_metadata_inventory_rejected_extraction_blocked",
        "unsafe status",
    )
    expect(
        record["result_scope"]
        == "one_consumed_metadata_inventory_invocation_rejected_on_member_path_safety_without_member_content_reads_extraction_installation_or_execution",
        "scope drift",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed commit")
    expect(
        record["baseline_commit"] == "f77eff72d5b21d13908d3b2d59e07fe5cdd6f68b",
        "baseline commit drift",
    )

    authorization = record["authorization"]
    expect(
        authorization["record"] == "phase6_llmster_archive_inventory_decision.json",
        "authorization path drift",
    )
    decision_path = path.parent / authorization["record"]
    expect(DIGEST.fullmatch(authorization["sha256"]) is not None, "bad authorization digest")
    expect(
        hashlib.sha256(decision_path.read_bytes()).hexdigest() == authorization["sha256"],
        "authorization digest drift",
    )
    decision = validate_decision(decision_path)
    expect(authorization["status"] == decision["status"], "authorization status drift")
    for key in ("validated_immediately_before_function_call", "consumed"):
        expect(authorization[key] is True, f"authorization state concealed: {key}")
    expect(authorization["function_invocation_count"] == 1, "invocation count drift")
    expect(authorization["automatic_retry_count"] == 0, "retry admitted")

    archive = record["archive"]
    identity = decision["archive_identity"]
    expect(archive["repository_relative_path"] == identity["repository_relative_path"], "archive path drift")
    for key in ("bytes", "sha256", "sha512"):
        expect(archive[key] == identity[key], f"archive {key} drift")
    expect(archive["identity_verified_by_function_before_rejection"] is True, "identity verification concealed")
    expect(archive["exists_after"] is True, "archive loss concealed")
    expect(archive["bytes_after"] == archive["bytes"], "archive size changed")
    expect(archive["last_write_time_utc_after"].endswith("Z"), "archive timestamp malformed")
    expect(archive["unchanged_by_inventory_function"] is True, "archive mutation concealed")

    observation = record["inventory_observation"]
    expect(observation["accepted"] is False, "rejection concealed")
    expect(observation["error_type"] == "ArchiveInventoryError", "error type drift")
    expect(observation["error_code"] == "member_backslash_rejected", "error code drift")
    expect(observation["rejection_phase"] == "central_directory_member_path_safety_validation", "rejection phase drift")
    expect(observation["end_of_central_directory_preflight_passed"] is True, "EOCD outcome concealed")
    expect(observation["central_directory_parsed"] is True, "central-directory outcome concealed")
    expect(observation["aggregate_inventory_completed"] is False, "completion overclaimed")
    expect(observation["entry_counts_or_member_paths_claimed"] is False, "path evidence overclaimed")

    counts = record["operation_counts"]
    for key in (
        "member_content_reads", "extractions", "files_written_by_inventory",
        "installations", "binary_executions", "network_requests", "benchmark_submissions",
    ):
        expect(counts[key] == 0, f"operation count widened: {key}")

    conclusion = record["security_and_research_conclusion"]
    expect(conclusion["fail_closed_behavior_confirmed"] is True, "fail-closed outcome concealed")
    for key in (
        "archive_safe_to_extract_claimed", "authenticode_verified_claimed",
        "overwrite_scope_known_claimed", "runtime_health_claimed",
        "model_quality_claimed", "backslash_normalization_accepted_claimed",
    ):
        expect(conclusion[key] is False, f"conclusion overclaimed: {key}")

    gate = record["result_gate"]
    expect(gate["inventory_accepted"] is False, "inventory accepted")
    expect(gate["fresh_path_normalization_design_decision_required"] is True, "fresh design gate concealed")
    for key in (
        "same_authorization_reusable", "automatic_retry_authorized",
        "archive_extraction_authorized", "installation_authorized",
        "binary_execution_authorized", "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"scope widened: {key}")
    expect(
        record["next_action"]
        == "preserve_this_rejection_then_design_and_fixture_review_a_separate_fail_closed_windows_separator_canonicalization_contract_before_any_fresh_inventory_decision",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    try:
        record = validate(arguments.path)
    except (KeyError, OSError, json.JSONDecodeError, LlmsterArchiveInventoryResultError) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
