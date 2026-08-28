"""Validate the one-shot Phase-6 llmster archive-download decision."""

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


class LlmsterDownloadExecutionDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterDownloadExecutionDecisionError(message)


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


def file_identity(path: Path) -> dict[str, int | str]:
    content = path.read_bytes()
    return {
        "bytes": len(content),
        "lines": len(content.decode("utf-8").splitlines()),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def expect_reviewed(base: Path, item: dict, name: str, status: str) -> dict:
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
        record["status"] == "llmster_archive_download_authorized_once_extraction_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "one_exact_archive_request_through_pinned_module_without_extraction_installation_or_runtime",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")
    expect(
        record["baseline_commit"] == "90aaf6ab8c9a4ec916de9995b7a198c2145bf446",
        "baseline commit drift",
    )

    base = path.parent
    blocked = expect_reviewed(
        base,
        record["reviewed_blocking_decision"],
        "phase6_llmster_download_execution_review.json",
        "llmster_archive_download_not_authorized_storage_preflight_failed",
    )
    implementation = expect_reviewed(
        base,
        record["reviewed_implementation"],
        "phase6_llmster_acquisition_implementation_result.json",
        "llmster_acquisition_module_implemented_fixtures_passed_download_blocked",
    )
    expect(blocked["decision_gate"]["archive_download_authorized"] is False, "blocked decision widened")
    expect(implementation["decision_gate"]["archive_download_authorized"] is False, "prior implementation widened")

    module = record["module_identity"]
    expect(module["path"] == "../llmster_archive_acquisition.py", "module path drift")
    target = (base / module["path"]).resolve()
    expect(target.is_file(), "module missing")
    expect(
        {key: module[key] for key in ("bytes", "lines", "sha256")}
        == file_identity(target),
        "module identity drift",
    )

    remediation = record["storage_remediation"]
    expect(
        remediation["approved_target_relative_path"]
        == "integrations/cyxcode/node_modules",
        "remediation target drift",
    )
    expect(
        remediation["classification"] == "git_ignored_rebuildable_dependency_tree",
        "remediation classification drift",
    )
    expect(remediation["logical_bytes_before"] == 7007221349, "remediation size drift")
    expect(remediation["target_present_after"] is False, "remediation completion concealed")
    expect(
        remediation["rebuild_command"]
        == "bun install --frozen-lockfile --ignore-scripts --no-progress",
        "rebuild command drift",
    )
    for key in (
        "cyxcode_source_or_git_history_removed",
        "project_model_or_research_evidence_removed",
    ):
        expect(remediation[key] is False, f"destructive remediation admitted: {key}")

    storage = record["fresh_storage_baseline"]
    expect(
        storage["measurement_method"]
        == "python_3_12_shutil_disk_usage_repository_root",
        "measurement method drift",
    )
    expect(storage["observed_free_bytes"] == 36168814592, "observed storage drift")
    expect(storage["maximum_archive_bytes"] == 1073741824, "archive ceiling drift")
    expect(storage["minimum_free_bytes_after"] == 34359738368, "storage reserve drift")
    required = storage["minimum_free_bytes_after"] + storage["maximum_archive_bytes"]
    expect(
        storage["required_free_bytes_before_request"] == required == 35433480192,
        "required storage arithmetic drift",
    )
    expect(
        storage["margin_bytes"] == storage["observed_free_bytes"] - required,
        "storage margin arithmetic drift",
    )
    expect(storage["margin_bytes"] > 0, "storage margin not positive")
    for key in ("destination_present", "partial_present"):
        expect(storage[key] is False, f"unclean destination baseline: {key}")
    for key in (
        "replay_cache_exactly_git_ignored",
        "storage_gate_passed",
        "module_must_remeasure_before_and_after_stream",
    ):
        expect(storage[key] is True, f"storage invariant weakened: {key}")

    request = record["frozen_request"]
    contract = implementation["acquisition_contract"]
    for key in (
        "archive_url",
        "expected_sha512",
        "destination_relative_path",
        "maximum_attempts",
        "redirects_allowed",
    ):
        expect(request[key] == contract[key], f"request contract drift: {key}")
    expect(SHA512.fullmatch(request["expected_sha512"]) is not None, "malformed checksum")
    expect(request["maximum_attempts"] == 1, "attempt count widened")
    expect(request["redirects_allowed"] is False, "redirect admitted")

    one_shot = record["one_shot_contract"]
    expect(one_shot["authorization_must_validate_before_function_call"] is True, "validation order weakened")
    expect(one_shot["module"] == "Thesis.pilot_data.llmster_archive_acquisition", "execution module drift")
    expect(one_shot["function"] == "acquire_exact_archive", "execution function drift")
    expect(one_shot["maximum_function_invocations"] == 1, "function invocation count widened")
    expect(one_shot["automatic_retry_count"] == 0, "automatic retry admitted")
    for key in (
        "decision_consumed_at_function_entry",
        "fresh_decision_required_after_success_failure_or_interruption",
    ):
        expect(one_shot[key] is True, f"one-shot invariant weakened: {key}")

    result = record["future_result_requirements"]
    for key, value in result.items():
        if key in (
            "archive_inventory_or_extraction_allowed",
            "runtime_or_model_health_conclusion_allowed",
        ):
            expect(value is False, f"result boundary widened: {key}")
        else:
            expect(value is True, f"result requirement weakened: {key}")

    fixtures = record["fixture_evidence"]
    for version in ("python_3_12", "python_3_14"):
        expect(
            fixtures[version] == {"tests_run": 316, "tests_passed": 316},
            f"full fixture drift: {version}",
        )
    expect(fixtures["download_execution_decision_tests"] == 10, "decision fixture count drift")
    expect(fixtures["fixture_network_request_count"] == 0, "fixture network activity admitted")

    security = record["security_and_research_boundary"]
    for key, value in security.items():
        if key.endswith("_count") or key.endswith("_count_at_decision"):
            expect(value == 0, f"operation admitted at decision: {key}")
        else:
            expect(value is False, f"research boundary widened: {key}")

    gate = record["decision_gate"]
    for key in (
        "implementation_identity_verified",
        "storage_remediation_verified",
        "clean_destination_gate_passed",
        "storage_gate_passed",
        "archive_download_authorized",
    ):
        expect(gate[key] is True, f"required authorization missing: {key}")
    expect(gate["maximum_authorized_archive_requests"] == 1, "request authorization widened")
    for key in (
        "archive_extraction_authorized",
        "standalone_llmster_installation_authorized",
        "lm_studio_runtime_execution_authorized",
        "automatic_retry_authorized",
        "synthetic_canary_authorized",
        "authenticated_http_server_authorized",
        "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"scope widened: {key}")
    expect(
        gate["next_action"]
        == "invoke_the_pinned_acquisition_function_once_and_preserve_the_result_without_extraction",
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
        LlmsterDownloadExecutionDecisionError,
    ) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: exact llmster archive request authorized once; extraction blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
