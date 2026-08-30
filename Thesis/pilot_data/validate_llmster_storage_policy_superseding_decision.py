"""Validate the superseding llmster archive storage-policy decision."""

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


class LlmsterStoragePolicyDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterStoragePolicyDecisionError(message)


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


def reviewed_record(base: Path, item: dict, name: str, status: str) -> dict:
    expect(item["record"] == name, f"{name}: record drift")
    expect(DIGEST.fullmatch(item["sha256"]) is not None, f"{name}: malformed digest")
    target = base / name
    expect(target.is_file(), f"{name}: missing evidence")
    expect(file_digest(target) == item["sha256"], f"{name}: digest drift")
    evidence = json.loads(target.read_text(encoding="utf-8"))
    expect(evidence["status"] == item["status"] == status, f"{name}: status drift")
    return evidence


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"]
        == "llmster_archive_download_authorized_once_revised_storage_policy_extraction_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "supersede_only_the_archive_storage_reserve_and_authorize_one_exact_request_without_extraction_installation_or_runtime",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")
    expect(
        record["baseline_commit"] == "4cc551f7a1dbb1c51069ef32885c1bd1dce267f1",
        "baseline commit drift",
    )

    base = path.parent
    prior = reviewed_record(
        base,
        record["reviewed_prior_decision"],
        "phase6_llmster_download_execution_decision.json",
        "llmster_archive_download_authorized_once_extraction_blocked",
    )
    implementation = reviewed_record(
        base,
        record["reviewed_implementation"],
        "phase6_llmster_acquisition_implementation_result.json",
        "llmster_acquisition_module_implemented_fixtures_passed_download_blocked",
    )
    prior_review = record["reviewed_prior_decision"]
    expect(prior_review["request_was_invoked"] is False, "prior request consumption concealed")
    expect(
        prior_review["authorization_disposition"]
        == "unconsumed_and_superseded_not_executable",
        "prior authorization not superseded",
    )
    expect(prior["frozen_request"]["maximum_attempts"] == 1, "prior request widened")
    expect(
        implementation["acquisition_contract"]["maximum_archive_bytes"] == 1_073_741_824,
        "implementation archive ceiling drift",
    )

    for key in ("shared_implementation_identity", "revised_policy_module_identity"):
        identity = record[key]
        expect(DIGEST.fullmatch(identity["sha256"]) is not None, f"{key}: malformed digest")
        target = (base / identity["path"]).resolve()
        expect(target.is_file(), f"{key}: missing file")
        expect(
            {name: identity[name] for name in ("bytes", "lines", "sha256")}
            == file_identity(target),
            f"{key}: identity drift",
        )
    expect(
        record["shared_implementation_identity"]["path"]
        == "../llmster_archive_acquisition.py",
        "shared implementation path drift",
    )
    expect(
        record["revised_policy_module_identity"]["path"]
        == "../llmster_archive_acquisition_v2.py",
        "revised policy path drift",
    )

    policy = record["storage_policy_decision"]
    expect(policy["maximum_archive_bytes"] == 1_073_741_824, "archive ceiling drift")
    expect(policy["minimum_free_bytes_after"] == 8_589_934_592, "revised reserve drift")
    expect(
        policy["required_free_bytes_before_request"]
        == policy["maximum_archive_bytes"] + policy["minimum_free_bytes_after"]
        == 9_663_676_416,
        "storage arithmetic drift",
    )
    expect(policy["reserve_to_archive_ratio"] == 8, "reserve ratio drift")
    expect(policy["prior_minimum_free_bytes_after"] == 34_359_738_368, "prior reserve drift")
    for key in (
        "prior_policy_superseded",
        "archive_is_written_once_to_partial_then_renamed_on_same_volume",
        "atomic_rename_does_not_duplicate_archive_bytes",
        "existing_model_weight_is_already_present_and_not_duplicated",
    ):
        expect(policy[key] is True, f"storage rationale weakened: {key}")
    for key in (
        "archive_extraction_or_installation_is_authorized",
        "runtime_or_model_execution_is_authorized",
    ):
        expect(policy[key] is False, f"storage decision scope widened: {key}")
    expect(
        policy["rationale"]
        == "the_operation_can_add_at_most_one_gibibyte_and_cannot_extract_install_or_run;an_eight_gibibyte_final_reserve_is_eight_times_the_bounded_write_and_preserves_a_large_non_operation_buffer",
        "storage rationale drift",
    )

    storage = record["fresh_storage_baseline"]
    expect(
        storage["measurement_method"] == "python_3_12_shutil_disk_usage_repository_root",
        "measurement method drift",
    )
    expect(storage["observed_free_bytes"] == 21_203_013_632, "observed storage drift")
    expect(
        storage["required_free_bytes_before_request"]
        == policy["required_free_bytes_before_request"],
        "baseline requirement drift",
    )
    expect(
        storage["margin_bytes"]
        == storage["observed_free_bytes"] - storage["required_free_bytes_before_request"],
        "storage margin arithmetic drift",
    )
    expect(storage["margin_bytes"] > policy["maximum_archive_bytes"], "storage margin too small")
    for key in ("destination_present", "partial_present"):
        expect(storage[key] is False, f"unclean destination baseline: {key}")
    for key in (
        "replay_cache_exactly_git_ignored",
        "storage_gate_passed",
        "module_must_remeasure_before_and_after_stream",
    ):
        expect(storage[key] is True, f"storage invariant weakened: {key}")

    request = record["frozen_request"]
    expect(
        request["archive_url"]
        == "https://llmster.lmstudio.ai/download/0.0.21-2-win32-x64.full.zip",
        "archive URL drift",
    )
    expect(SHA512.fullmatch(request["expected_sha512"]) is not None, "malformed checksum")
    expect(
        request["expected_sha512"]
        == "ec13183ddc2f56d68b48fc13428e0cdca84c29bfc2b87a7aa2b9befeb7b79a8cdd3ea5a7c50d6e941fcf43545c8730f8b2bf2665b030b98e5ccfab6a3d43efff",
        "checksum drift",
    )
    expect(
        request["destination_relative_path"]
        == ".replay_cache/llmster_acquisition/0.0.21-2-win32-x64.full.zip",
        "destination drift",
    )
    for key in ("maximum_archive_bytes", "minimum_free_bytes_after"):
        expect(request[key] == policy[key], f"request policy drift: {key}")
    expect(request["maximum_attempts"] == 1, "attempt count widened")
    expect(request["redirects_allowed"] is False, "redirect admitted")

    one_shot = record["one_shot_contract"]
    expect(one_shot["authorization_must_validate_before_function_call"] is True, "validation order weakened")
    expect(one_shot["module"] == "Thesis.pilot_data.llmster_archive_acquisition_v2", "module drift")
    expect(one_shot["function"] == "acquire_exact_archive", "function drift")
    expect(one_shot["prior_module_maximum_invocations_after_supersession"] == 0, "prior authorization retained")
    expect(one_shot["current_module_maximum_invocations"] == 1, "current invocation widened")
    expect(one_shot["maximum_combined_archive_requests"] == 1, "combined request count widened")
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
        expect(fixtures[version] == {"tests_run": 331, "tests_passed": 331}, f"fixture drift: {version}")
    expect(fixtures["revised_policy_module_tests"] == 5, "policy fixture count drift")
    expect(fixtures["superseding_decision_tests"] == 10, "decision fixture count drift")
    expect(fixtures["fixture_network_request_count"] == 0, "fixture network activity admitted")

    security = record["security_and_research_boundary"]
    for key, value in security.items():
        if key.endswith("_count") or key.endswith("_count_at_decision"):
            expect(value == 0, f"operation admitted at decision: {key}")
        else:
            expect(value is False, f"research boundary widened: {key}")

    gate = record["decision_gate"]
    for key in (
        "prior_authorization_superseded",
        "shared_implementation_identity_verified",
        "revised_policy_module_identity_verified",
        "clean_destination_gate_passed",
        "revised_storage_gate_passed",
        "archive_download_authorized",
    ):
        expect(gate[key] is True, f"required authorization missing: {key}")
    expect(gate["maximum_authorized_archive_requests"] == 1, "authorization widened")
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
        == "validate_this_superseding_decision_then_invoke_the_revised_policy_acquisition_function_once_without_extraction",
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
        LlmsterStoragePolicyDecisionError,
    ) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: revised storage policy authorizes one exact archive request; extraction blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
