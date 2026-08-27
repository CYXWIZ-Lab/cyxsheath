"""Validate the fixture-only Phase-6 llmster acquisition implementation."""

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


class LlmsterAcquisitionImplementationError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterAcquisitionImplementationError(message)


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
        == "llmster_acquisition_module_implemented_fixtures_passed_download_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "dependency_free_acquisition_module_and_in_memory_fixtures_only_no_network_archive_or_runtime_execution",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    reviewed = record["reviewed_decision"]
    expect(
        reviewed["record"] == "phase6_llmster_acquisition_preflight_decision.json",
        "decision record drift",
    )
    decision_path = path.parent / reviewed["record"]
    expect(DIGEST.fullmatch(reviewed["sha256"]) is not None, "malformed decision digest")
    expect(
        hashlib.sha256(decision_path.read_bytes()).hexdigest() == reviewed["sha256"],
        "decision digest drift",
    )
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    expect(decision["status"] == reviewed["status"], "decision status drift")
    expect(
        decision["decision_gate"]["acquisition_runner_implementation_and_fixtures_authorized"]
        is True,
        "implementation authority missing",
    )
    expect(
        decision["decision_gate"]["archive_download_authorized"] is False,
        "prior download boundary widened",
    )

    sources = record["source_identity"]
    expected_paths = [
        "../llmster_archive_acquisition.py",
        "../test_llmster_archive_acquisition.py",
    ]
    expect([item["path"] for item in sources] == expected_paths, "source set drift")
    for item in sources:
        expect(item["change"] == "new", f"source classification drift: {item['path']}")
        expect(DIGEST.fullmatch(item["sha256"]) is not None, f"malformed source digest: {item['path']}")
        target = (path.parent / item["path"]).resolve()
        expect(target.is_file(), f"source missing: {item['path']}")
        expect(
            {key: item[key] for key in ("bytes", "lines", "sha256")}
            == file_identity(target),
            f"source identity drift: {item['path']}",
        )

    boundary = record["module_boundary"]
    expect(
        boundary["module_owns_exact_https_stream_bounds_hashes_partial_cleanup_and_atomic_placement_only"]
        is True,
        "module ownership widened",
    )
    expect(boundary["network_adapter_is_injected_for_fixtures"] is True, "network seam removed")
    for key in (
        "cli_entrypoint_added",
        "archive_extraction_added",
        "process_execution_added",
        "existing_lifecycle_module_changed",
        "existing_load_health_runner_changed",
        "sheath_core_changed",
        "cyxcode_changed",
    ):
        expect(boundary[key] is False, f"module expansion admitted: {key}")
    expect(boundary["new_dependency_count"] == 0, "dependency growth admitted")
    expect(boundary["new_thread_count"] == 0, "concurrency growth admitted")

    contract = record["acquisition_contract"]
    name = "0.0.21-2-win32-x64.full.zip"
    expected_url = f"https://llmster.lmstudio.ai/download/{name}"
    preflight = decision["acquisition_strategy"]
    expect(contract["archive_url"] == expected_url, "archive URL drift")
    expect(
        contract["archive_url"]
        == decision["official_release_metadata"]["archive_url"],
        "archive URL linkage drift",
    )
    expect(SHA512.fullmatch(contract["expected_sha512"]) is not None, "malformed checksum")
    expect(contract["expected_sha512"] == preflight["expected_sha512"], "checksum linkage drift")
    expect(contract["destination_relative_path"] == preflight["destination_relative_path"], "destination drift")
    expect(contract["partial_suffix"] == ".partial", "partial suffix drift")
    expect(contract["maximum_attempts"] == 1, "attempt count widened")
    expect(contract["redirects_allowed"] is False, "redirect admitted")
    expect(contract["maximum_archive_bytes"] == 1073741824, "archive ceiling drift")
    expect(contract["minimum_free_bytes_after"] == 34359738368, "storage reserve weakened")
    expect(contract["windows_only"] is True, "platform widened")
    expect(contract["git_ignored_destination_required"] is True, "ignored storage removed")

    behaviors = record["verified_behaviors"]
    for key, value in behaviors.items():
        expect(value is True, f"verified behavior weakened: {key}")

    fixtures = record["fixture_evidence"]
    for version in ("python_3_12", "python_3_14"):
        expect(
            fixtures[version] == {"tests_run": 296, "tests_passed": 296},
            f"full fixture drift: {version}",
        )
    expect(fixtures["focused_acquisition_tests"] == 13, "acquisition fixture count drift")
    expect(fixtures["implementation_result_tests"] == 10, "result fixture count drift")
    for key, value in fixtures.items():
        if key.endswith("_count"):
            expect(value == 0, f"operation admitted: {key}")

    gate = record["decision_gate"]
    expect(gate["acquisition_module_implementation_complete"] is True, "implementation gate missing")
    expect(gate["fixture_gate_passed"] is True, "fixture gate missing")
    for key in (
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
        == "make_a_separate_validator_backed_one_download_execution_decision_before_any_archive_request",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, LlmsterAcquisitionImplementationError) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: acquisition module implemented; fixtures passed; archive download blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
