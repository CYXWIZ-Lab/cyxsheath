"""Validate the metadata-only Phase-6 llmster acquisition preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
SHA512 = re.compile(r"^[0-9a-f]{128}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN = {
    "hostname",
    "machine_id",
    "serial_number",
    "username",
    "resolved_ip",
    "credential",
    "api_token",
    "problem_statement",
    "raw_prompt",
    "raw_response",
    "patch",
    "test_patch",
    "eval_script",
}


class LlmsterAcquisitionPreflightDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterAcquisitionPreflightDecisionError(message)


def check_forbidden(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN & set(value)
        expect(not found, f"{where}: forbidden keys {sorted(found)}")
        for key, child in value.items():
            check_forbidden(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_forbidden(child, f"{where}[{index}]")


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect_evidence(base: Path, item: dict, name: str, status: str) -> dict:
    expect(item["record"] == name, f"{name}: record drift")
    expect(DIGEST.fullmatch(item["sha256"]) is not None, f"{name}: malformed digest")
    target = base / name
    expect(target.is_file(), f"{name}: missing evidence")
    expect(file_digest(target) == item["sha256"], f"{name}: digest drift")
    evidence = json.loads(target.read_text(encoding="utf-8"))
    expect(item["status"] == status == evidence["status"], f"{name}: status drift")
    return evidence


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"]
        == "direct_archive_acquisition_contract_frozen_runner_fixtures_authorized_download_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "official_metadata_and_existing_evidence_preflight_no_installer_archive_or_runtime_execution",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    reviewed = record["reviewed_evidence"]
    selection = expect_evidence(
        path.parent,
        reviewed["lifecycle_selection"],
        "phase6_runtime_lifecycle_selection_decision.json",
        "standalone_llmster_selected_acquisition_review_pending_runtime_blocked",
    )
    engine = expect_evidence(
        path.parent,
        reviewed["corrected_engine_and_cli_identity"],
        "phase6_load_health_runner_execution_decision.json",
        "python_load_health_runner_execution_authorized_once",
    )
    model = expect_evidence(
        path.parent,
        reviewed["model_activation_preflight"],
        "phase6_local_model_activation_preflight.json",
        "activation_preflight_complete_load_health_gate_pending",
    )
    expect(selection["selection"]["selected_family"] == "standalone_llmster", "selection linkage drift")
    expect(selection["decision_gate"]["installer_or_archive_download_authorized"] is False, "prior boundary widened")

    metadata = record["official_release_metadata"]
    expect(metadata["reviewed_on"] == "2026-08-27", "metadata review date drift")
    expect(metadata["installer_source"] == "https://lmstudio.ai/install.ps1", "installer source drift")
    expect(metadata["release_version"] == "0.0.21-2", "release version drift")
    expect(metadata["platform"] == "win32-x64", "platform drift")
    expect(metadata["variant"] == "full", "variant drift")
    name = "0.0.21-2-win32-x64.full.zip"
    url = f"https://llmster.lmstudio.ai/download/{name}"
    expect(metadata["archive_name"] == name, "archive name drift")
    expect(metadata["archive_url"] == url, "archive URL drift")
    expect(metadata["checksum_url"] == f"{url}.sha512", "checksum URL drift")
    expect(SHA512.fullmatch(metadata["published_sha512"]) is not None, "malformed published checksum")
    expect(metadata["checksum_algorithm"] == "sha512", "checksum algorithm drift")
    expect(metadata["checksum_format_valid"] is True, "checksum format concealed")
    expect(metadata["archive_head_result"] == "method_not_allowed_405_size_not_claimed", "size overclaim")
    expect(metadata["archive_bytes_downloaded"] == 0, "archive download concealed")
    expect(metadata["checksum_metadata_get_count"] == 1, "metadata request drift")

    acquisition = record["acquisition_strategy"]
    expect(acquisition["strategy"] == "direct_pinned_archive_without_installer_script", "strategy drift")
    expect(acquisition["mutable_installer_used"] is False, "mutable installer admitted")
    expect(acquisition["installer_identity_requirement"] == "not_applicable_because_installer_execution_is_rejected", "installer execution ambiguity")
    expect(acquisition["transport"] == "dependency_free_https_stream_to_partial_then_atomic_rename", "transport drift")
    expect(acquisition["allowed_scheme"] == "https", "transport weakened")
    expect(acquisition["allowed_origin_host"] == "llmster.lmstudio.ai", "origin widened")
    expect(acquisition["redirects_allowed"] is False, "redirect admitted")
    expect(acquisition["maximum_attempts"] == 1, "attempt count widened")
    expect(acquisition["maximum_archive_bytes"] == 1073741824, "archive ceiling drift")
    expect(acquisition["minimum_free_bytes_after"] == 34359738368, "storage reserve weakened")
    expect(acquisition["destination_relative_path"] == f".replay_cache/llmster_acquisition/{name}", "destination drift")
    expect(acquisition["partial_suffix"] == ".partial", "partial path drift")
    expect(acquisition["git_ignored_required"] is True, "ignored-storage requirement removed")
    expect(acquisition["expected_sha512"] == metadata["published_sha512"], "checksum linkage drift")
    for key in (
        "compute_sha256_and_exact_bytes",
        "delete_partial_on_any_failure",
        "reject_unexpected_existing_destination",
    ):
        expect(acquisition[key] is True, f"acquisition invariant weakened: {key}")
    expect(acquisition["archive_extraction_authorized"] is False, "archive extraction admitted")
    expect(acquisition["archive_execution_authorized"] is False, "archive execution admitted")

    preserved = record["existing_state_to_preserve"]
    checkpoint = engine["identity_checkpoint"]
    expect(preserved["canonical_cli"]["bytes"] == checkpoint["canonical_cli_bytes"], "CLI size drift")
    expect(preserved["canonical_cli"]["sha256"] == checkpoint["canonical_cli_sha256"], "CLI identity drift")
    corrected = engine["canonicalization_correction"]["corrected_inventory"]
    expect(preserved["engine"]["canonical_inventory_sha256"] == corrected["sha256"], "engine identity drift")
    expect(preserved["engine"]["file_count"] == corrected["file_count"], "engine file count drift")
    expect(preserved["engine"]["total_bytes"] == corrected["total_bytes"], "engine size drift")
    download = model["download"]
    expect(preserved["weight"]["bytes"] == download["exact_bytes"], "weight size drift")
    expect(preserved["weight"]["sha256"] == download["actual_sha256"], "weight identity drift")
    expect(preserved["weight"]["symbolic_import_must_remain_unchanged"] is True, "symbolic import weakened")
    for key in (
        "acquisition_may_modify_lmstudio_home",
        "acquisition_may_modify_path",
        "acquisition_may_change_engine_preferences",
    ):
        expect(preserved[key] is False, f"acquisition side effect admitted: {key}")

    for key, value in record["future_acquisition_result_requirements"].items():
        if key in ("retain_raw_archive_in_repository", "runtime_or_model_health_conclusion_allowed"):
            expect(value is False, f"result boundary widened: {key}")
        else:
            expect(value is True, f"result requirement weakened: {key}")

    rollback = record["rollback_and_next_gate"]
    expect(rollback["acquisition_failure_action"] == "delete_only_exact_partial_file_and_record_failure", "failure scope widened")
    expect(rollback["verified_archive_retention"] == "ignored_local_until_separate_installation_decision", "archive retention drift")
    for key in (
        "installation_preflight_requires_archive_inventory",
        "installation_preflight_requires_path_traversal_rejection",
        "installation_preflight_requires_authenticode_review",
        "installation_preflight_requires_exact_overwrite_and_rollback_plan",
    ):
        expect(rollback[key] is True, f"installation preflight weakened: {key}")
    expect(rollback["automatic_retry_allowed"] is False, "automatic retry admitted")

    boundary = record["module_boundary"]
    expect(boundary["new_module_role"] == "exact_archive_acquisition_only", "module role drift")
    for key in (
        "existing_lifecycle_module_change_required",
        "existing_load_health_runner_change_required",
        "sheath_core_change_required",
    ):
        expect(boundary[key] is False, f"module expansion admitted: {key}")
    expect(boundary["new_dependency_count"] == 0, "dependency growth admitted")
    expect(boundary["new_thread_count"] == 0, "thread growth admitted")

    security = record["security_and_research_boundary"]
    for key, value in security.items():
        if key.endswith("_count"):
            expect(value == 0, f"operation admitted: {key}")
        else:
            expect(value is False, f"research boundary widened: {key}")

    gate = record["decision_gate"]
    expect(gate["acquisition_contract_frozen"] is True, "acquisition contract missing")
    expect(gate["acquisition_runner_implementation_and_fixtures_authorized"] is True, "runner implementation not authorized")
    for key in (
        "installer_download_or_execution_authorized",
        "archive_download_authorized",
        "archive_extraction_authorized",
        "standalone_llmster_installation_authorized",
        "lm_studio_runtime_execution_authorized",
        "automatic_retry_authorized",
        "synthetic_canary_authorized",
        "authenticated_http_server_authorized",
        "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"]
        == "implement_and_fixture_test_the_exact_archive_acquisition_module_then_make_a_separate_download_execution_decision",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, LlmsterAcquisitionPreflightDecisionError) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: exact archive contract frozen; runner fixtures authorized; download blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
