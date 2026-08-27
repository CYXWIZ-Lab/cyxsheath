"""Validate the Phase-6 LM Studio shutdown-contract review decision."""

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


class ShutdownContractReviewDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise ShutdownContractReviewDecisionError(message)


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
        == "shutdown_contract_review_complete_correction_implementation_authorized_runtime_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "retained_evidence_and_primary_source_review_no_lm_studio_runtime_authorization",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    reviewed = record["reviewed_evidence"]
    result = expect_evidence(
        path.parent,
        reviewed["load_health_result"],
        "phase6_load_health_runner_execution_result.json",
        "model_load_and_resource_gates_observed_shutdown_acceptance_failed",
    )
    preflight = expect_evidence(
        path.parent,
        reviewed["activation_preflight"],
        "phase6_local_model_activation_preflight.json",
        "activation_preflight_complete_load_health_gate_pending",
    )
    expect(result["acceptance"]["graceful_shutdown_gate_passed"] is False, "prior failure concealed")
    deviations = {item["event"] for item in preflight["protocol_deviations"]}
    expect("daemon_down_refused_while_hosted_by_desktop_service" in deviations, "preflight linkage drift")
    for value in reviewed["reviewed_source"].values():
        expect(DIGEST.fullmatch(value) is not None, "malformed reviewed-source digest")
    log = reviewed["local_server_log"]
    expect(log["retention"] == "user_local_not_committed", "local-log retention drift")
    expect(log["bytes"] == 4698, "local-log size drift")
    expect(DIGEST.fullmatch(log["sha256"]) is not None, "malformed local-log digest")
    expect(log["raw_cli_stdout_stderr_available"] is False, "missing CLI output overclaim")

    sources = record["official_primary_sources"]
    expect(sources["reviewed_on"] == "2026-08-27", "source-review date drift")
    expected_urls = {
        "daemon_down_documentation": "https://lmstudio.ai/docs/cli/daemon/daemon-down",
        "daemon_status_documentation": "https://lmstudio.ai/docs/cli/daemon/daemon-status",
        "headless_documentation": "https://lmstudio.ai/docs/developer/core/headless",
        "daemon_up_source": "https://github.com/lmstudio-ai/lms/blob/main/src/subcommands/daemon/up.ts",
        "daemon_down_source": "https://github.com/lmstudio-ai/lms/blob/main/src/subcommands/daemon/down.ts",
        "daemon_status_source": "https://github.com/lmstudio-ai/lms/blob/main/src/subcommands/daemon/status.ts",
    }
    for key, expected in expected_urls.items():
        expect(sources[key] == expected, f"official source drift: {key}")
    for key, value in sources["source_observations"].items():
        expect(value is True, f"official behavior concealed: {key}")

    finding = record["finding"]
    expect(finding["finding_id"] == "phase6-shutdown-review-001", "finding identity drift")
    expect(finding["severity"] == "protocol_blocking", "finding severity weakened")
    expect(
        finding["classification"]
        == "lifecycle_mode_mismatch_with_unresolved_exact_exit_branch",
        "finding classification drift",
    )
    expect(
        finding["confidence"] == "high_for_contract_mismatch_not_proven_for_exact_cli_message",
        "finding confidence overclaim",
    )
    expect(finding["exact_daemon_down_message_observed"] is False, "exact-message overclaim")
    expect(finding["runner_timing_is_primary_cause"] is False, "timing-only misclassification")
    expect(finding["longer_root_wait_alone_is_an_authorized_correction"] is False, "unsafe timing correction")
    expect(finding["prior_graceful_shutdown_result_remains_failed"] is True, "prior result reinterpreted")
    expect(finding["prior_forced_cleanup_remains_a_protocol_failure"] is True, "forced cleanup reinterpreted")

    correction = record["approved_correction_contract"]
    expect(correction["startup_control"] == "temporary_lms_exe daemon up --json", "startup control drift")
    expect(correction["required_startup_fields"] == ["status", "pid", "isDaemon", "version"], "startup fields drift")
    preload = correction["preload_gate"]
    expect(preload["required_status"] == "running", "startup status weakened")
    expect(preload["required_is_daemon"] is True, "daemon-mode gate weakened")
    expect(
        preload["desktop_service_mode_action"]
        == "fail_before_model_load_as_incompatible_with_graceful_daemon_protocol",
        "desktop-service action drift",
    )
    expect(preload["pid_must_match_owned_root"] is True, "ownership gate weakened")
    observation = correction["control_observation"]
    for key in (
        "retain_numeric_exit",
        "retain_stdout_stderr_byte_lengths_and_sha256",
        "retain_allowlisted_diagnostic_code",
    ):
        expect(observation[key] is True, f"control evidence removed: {key}")
    expect(observation["retain_unbounded_raw_output_in_curated_evidence"] is False, "raw output widened")
    expect(
        correction["shutdown_sequence"]
        == [
            "unload_exact_identifier",
            "require_empty_loaded_inventory",
            "record_daemon_status_json_before_down",
            "run_daemon_down_once",
            "poll_daemon_status_json_until_not_running_or_timeout",
            "verify_owned_root_exit_and_zero_runtime_artifacts",
            "use_bounded_owned_tree_cleanup_only_as_failed_safety_fallback",
        ],
        "shutdown sequence drift",
    )
    acceptance = correction["acceptance"]
    for key in (
        "daemon_down_exit_must_be_zero",
        "final_daemon_status_must_be_not_running",
        "owned_root_must_exit",
        "loaded_inventory_must_be_empty",
        "port_1234_listener_count_must_be_zero",
    ):
        expect(acceptance[key] is True, f"acceptance weakened: {key}")
    expect(acceptance["forced_cleanup_allowed_as_success"] is False, "forced cleanup accepted")

    boundary = record["security_and_research_boundary"]
    for key, value in boundary.items():
        if key.endswith("_count") or key.endswith("_count_at_review"):
            expect(value == 0, f"runtime operation admitted: {key}")
        else:
            expect(value is False, f"research boundary widened: {key}")

    gate = record["decision_gate"]
    expect(gate["shutdown_observation_implementation_and_fixtures_authorized"] is True, "implementation not authorized")
    for key in (
        "lm_studio_runtime_execution_authorized",
        "standalone_llmster_installation_authorized",
        "automatic_retry_authorized",
        "synthetic_canary_authorized",
        "authenticated_http_server_authorized",
        "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"]
        == "implement_and_fixture_test_mode_aware_shutdown_observation_then_make_a_separate_runtime_selection_decision",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, ShutdownContractReviewDecisionError) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: shutdown contract reviewed; fixture-only correction authorized; runtime blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
