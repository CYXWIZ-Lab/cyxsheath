"""Validate the fixture-only Phase-6 extraction-staging implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN = {
    "hostname",
    "machine_id",
    "serial_number",
    "username",
    "credential",
    "api_token",
    "raw_member_name",
    "raw_member_names",
    "staging_path",
    "problem_statement",
    "raw_prompt",
    "raw_response",
    "patch",
    "test_patch",
}


class LlmsterExtractionStagingImplementationError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterExtractionStagingImplementationError(message)


def check_forbidden(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN & set(value)
        expect(not found, f"{where}: forbidden keys {sorted(found)}")
        for key, child in value.items():
            check_forbidden(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_forbidden(child, f"{where}[{index}]")


def file_identity(path: Path) -> dict[str, int | str]:
    content = path.read_bytes()
    return {
        "bytes": len(content),
        "lines": len(content.decode("utf-8").splitlines()),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"]
        == "llmster_owned_extraction_staging_implemented_generated_fixtures_passed_real_extraction_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "dependency_free_owned_staging_implementation_and_generated_zip_fixtures_only_without_real_archive_member_reads_or_extraction",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    reviewed = record["reviewed_decision"]
    expect(
        reviewed["record"] == "phase6_llmster_extraction_staging_design_decision.json",
        "design record drift",
    )
    decision_path = path.parent / reviewed["record"]
    expect(DIGEST.fullmatch(reviewed["sha256"]) is not None, "malformed design digest")
    expect(
        hashlib.sha256(decision_path.read_bytes()).hexdigest() == reviewed["sha256"],
        "design digest drift",
    )
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    expect(decision["status"] == reviewed["status"], "design status drift")
    gate = decision["execution_gate"]
    expect(gate["generated_fixture_extraction_authorized"] is True, "fixture authority missing")
    expect(gate["real_archive_extraction_authorized"] is False, "design boundary widened")

    sources = record["source_identity"]
    expected_paths = [
        "../llmster_archive_inventory.py",
        "../test_llmster_archive_inventory.py",
        "../llmster_archive_staging.py",
        "../test_llmster_archive_staging.py",
    ]
    expect([item["path"] for item in sources] == expected_paths, "source set drift")
    expected_changes = [
        "modified_public_path_and_kind_policy_surface",
        "modified_public_policy_surface_test",
        "new",
        "new",
    ]
    expect([item["change"] for item in sources] == expected_changes, "source classification drift")
    for item in sources:
        expect(DIGEST.fullmatch(item["sha256"]) is not None, f"malformed source digest: {item['path']}")
        target = (path.parent / item["path"]).resolve()
        expect(target.is_file(), f"source missing: {item['path']}")
        expect(
            {key: item[key] for key in ("bytes", "lines", "sha256")} == file_identity(target),
            f"source identity drift: {item['path']}",
        )

    boundary = record["module_boundary"]
    for key in (
        "inventory_module_owns_metadata_path_and_member_kind_policy",
        "staging_module_owns_exclusive_child_streamed_writes_content_evidence_and_owned_cleanup_only",
        "generic_generated_fixture_entrypoint_only",
    ):
        expect(boundary[key] is True, f"module ownership weakened: {key}")
    for key in (
        "real_archive_wrapper_added",
        "authenticode_tooling_added",
        "installation_or_runtime_entrypoint_added",
        "process_or_network_adapter_added",
        "sheath_core_changed",
        "cyxcode_changed",
    ):
        expect(boundary[key] is False, f"module expansion admitted: {key}")
    expect(boundary["new_dependency_count"] == 0, "dependency growth admitted")
    expect(boundary["new_thread_count"] == 0, "concurrency growth admitted")

    contract = record["frozen_contract"]
    expect(contract["staging_parent_relative_path"] == ".replay_cache/llmster_staging", "parent drift")
    expect(contract["child_name_pattern"] == "llmster-[0-9a-f]{32}", "child pattern drift")
    expect(contract["ownership_marker"] == ".cyxsheath-staging-owner.json", "marker drift")
    expect(contract["minimum_free_bytes_after"] == 4_294_967_296, "final reserve weakened")
    expect(contract["declared_real_expansion_bytes"] == 1_791_678_266, "expansion drift")
    expect(contract["minimum_free_bytes_before_real_staging"] == 6_086_645_562, "preflight reserve drift")
    expect(contract["stream_chunk_bytes_maximum"] == 8_388_608, "stream chunk widened")
    expect(contract["signature_candidate_suffixes"] == [".dll", ".exe", ".node", ".ps1"], "candidate suffix drift")
    expect(contract["automatic_retry_count_maximum"] == 0, "retry admitted")

    for key, value in record["verified_behaviors"].items():
        expect(value is True, f"verified behavior weakened: {key}")

    fixtures = record["fixture_evidence"]
    for version in ("python_3_12", "python_3_14"):
        expect(fixtures[version] == {"tests_run": 467, "tests_passed": 467}, f"full fixture drift: {version}")
    expect(fixtures["focused_inventory_and_staging_tests"] == 46, "focused fixture count drift")
    expect(fixtures["focused_staging_tests"] == 19, "staging fixture count drift")
    expect(fixtures["implementation_result_tests"] == 10, "result fixture count drift")
    expect(fixtures["generated_fixture_extraction_authorized"] is True, "fixture authority missing")
    for key, value in fixtures.items():
        if key.endswith("_count"):
            expect(value == 0, f"operation admitted: {key}")

    result_gate = record["decision_gate"]
    expect(result_gate["owned_staging_implementation_complete"] is True, "implementation gate missing")
    expect(result_gate["generated_fixture_gate_passed"] is True, "fixture gate missing")
    for key in (
        "real_archive_identity_or_member_read_authorized",
        "real_archive_extraction_authorized",
        "authenticode_tool_invocation_authorized",
        "installation_authorized",
        "binary_execution_authorized",
        "network_request_authorized",
        "benchmark_input_authorized",
    ):
        expect(result_gate[key] is False, f"premature authorization: {key}")
    expect(
        result_gate["next_action"]
        == "make_a_separate_validator_backed_real_staging_decision_before_any_real_archive_member_read_or_extraction",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (
        OSError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        LlmsterExtractionStagingImplementationError,
    ) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: owned staging implemented; generated fixtures passed; real extraction blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
