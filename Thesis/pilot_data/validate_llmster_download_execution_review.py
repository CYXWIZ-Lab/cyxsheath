"""Validate the blocked Phase-6 llmster archive-download execution review."""

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


class LlmsterDownloadExecutionReviewError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterDownloadExecutionReviewError(message)


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
        == "llmster_archive_download_not_authorized_storage_preflight_failed",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "one_download_execution_review_without_archive_request_extraction_installation_or_runtime",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")
    expect(
        record["baseline_commit"] == "ea97ff2169e85e9764a118e528e3d6082df0607c",
        "baseline commit drift",
    )

    reviewed = record["reviewed_implementation"]
    expect(
        reviewed["record"] == "phase6_llmster_acquisition_implementation_result.json",
        "implementation record drift",
    )
    implementation_path = path.parent / reviewed["record"]
    expect(DIGEST.fullmatch(reviewed["sha256"]) is not None, "malformed implementation digest")
    expect(
        hashlib.sha256(implementation_path.read_bytes()).hexdigest()
        == reviewed["sha256"],
        "implementation digest drift",
    )
    implementation = json.loads(implementation_path.read_text(encoding="utf-8"))
    expect(implementation["status"] == reviewed["status"], "implementation status drift")
    expect(
        implementation["decision_gate"]["archive_download_authorized"] is False,
        "prior download boundary widened",
    )
    expect(
        implementation["decision_gate"]["next_action"]
        == "make_a_separate_validator_backed_one_download_execution_decision_before_any_archive_request",
        "implementation handoff drift",
    )

    module = record["module_identity"]
    expect(module["path"] == "../llmster_archive_acquisition.py", "module path drift")
    expect(DIGEST.fullmatch(module["sha256"]) is not None, "malformed module digest")
    target = (path.parent / module["path"]).resolve()
    expect(target.is_file(), "module missing")
    expect(
        {key: module[key] for key in ("bytes", "lines", "sha256")}
        == file_identity(target),
        "module identity drift",
    )

    request = record["frozen_request"]
    contract = implementation["acquisition_contract"]
    for key in (
        "archive_url",
        "expected_sha512",
        "destination_relative_path",
        "maximum_attempts",
        "redirects_allowed",
        "maximum_archive_bytes",
        "minimum_free_bytes_after",
    ):
        expect(request[key] == contract[key], f"request contract drift: {key}")
    expect(SHA512.fullmatch(request["expected_sha512"]) is not None, "malformed checksum")
    expect(request["maximum_attempts"] == 1, "attempt count widened")
    expect(request["redirects_allowed"] is False, "redirect admitted")

    storage = record["storage_observation"]
    expect(
        storage["measurement_method"]
        == "python_3_12_shutil_disk_usage_repository_root",
        "measurement method drift",
    )
    required = request["minimum_free_bytes_after"] + request["maximum_archive_bytes"]
    expect(
        storage["required_free_bytes_before_request"] == required == 35433480192,
        "required storage arithmetic drift",
    )
    expect(storage["observed_free_bytes"] == 28902416384, "observed storage drift")
    expect(
        storage["deficit_bytes"] == required - storage["observed_free_bytes"],
        "storage deficit arithmetic drift",
    )
    expect(storage["observed_free_bytes"] < required, "storage failure concealed")
    for key in ("destination_present", "partial_present", "storage_gate_passed"):
        expect(storage[key] is False, f"unclean or passing storage baseline: {key}")
    for key in (
        "replay_cache_exactly_git_ignored",
        "fresh_measurement_required_before_later_authorization",
    ):
        expect(storage[key] is True, f"storage invariant weakened: {key}")

    failure = record["failure_boundary"]
    expect(
        failure["module_rejects_storage_failure_before_opening_response"] is True,
        "pre-network failure boundary weakened",
    )
    for key in (
        "archive_request_performed",
        "automatic_cleanup_authorized",
        "automatic_relocation_authorized",
        "model_or_research_evidence_deletion_authorized",
        "destination_contract_change_authorized",
    ):
        expect(failure[key] is False, f"failure response widened: {key}")

    fixtures = record["fixture_evidence"]
    for version in ("python_3_12", "python_3_14"):
        expect(
            fixtures[version] == {"tests_run": 306, "tests_passed": 306},
            f"full fixture drift: {version}",
        )
    expect(fixtures["download_execution_review_tests"] == 10, "review fixture count drift")
    expect(fixtures["fixture_network_request_count"] == 0, "fixture network activity admitted")

    security = record["security_and_research_boundary"]
    for key, value in security.items():
        if key.endswith("_count"):
            expect(value == 0, f"operation admitted: {key}")
        else:
            expect(value is False, f"research boundary widened: {key}")

    gate = record["decision_gate"]
    for key in ("implementation_identity_verified", "clean_destination_gate_passed"):
        expect(gate[key] is True, f"review gate missing: {key}")
    for key in (
        "storage_gate_passed",
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
        == "make_at_least_35433480192_free_bytes_available_on_the_repository_volume_then_make_a_fresh_execution_decision",
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
        LlmsterDownloadExecutionReviewError,
    ) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: archive download blocked by storage preflight; no request authorized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
