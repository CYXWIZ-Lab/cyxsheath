"""Validate the Phase-6 load-health transport-integration design."""

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
LOAD_COMMAND = (
    "temporary_lms_exe load qwen2.5-coder-7b-instruct --gpu off --context-length 8192 "
    "--parallel 1 --ttl 600 --no-speculative-draft-mtp --identifier "
    "cyxsheath-qwen25-coder-7b-q4km --yes"
)


class LoadHealthTransportIntegrationDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LoadHealthTransportIntegrationDecisionError(message)


def check_forbidden(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN & set(value)
        expect(not found, f"{where}: forbidden keys {sorted(found)}")
        for key, child in value.items():
            check_forbidden(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_forbidden(child, f"{where}[{index}]")


def expect_digest(value: object, label: str) -> None:
    expect(isinstance(value, str) and DIGEST.fullmatch(value) is not None, f"malformed digest: {label}")


def expect_file_digest(base: Path, relative: str, expected: str, label: str) -> None:
    expect_digest(expected, label)
    target = (base / relative).resolve()
    expect(target.is_file(), f"{label} file missing")
    expect(hashlib.sha256(target.read_bytes()).hexdigest() == expected, f"{label} digest mismatch")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"] == "load_health_transport_integration_designed_runner_implementation_authorized",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "design_and_fixture_implementation_only_no_lm_studio_runtime_authorization",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")
    expect(
        record["essential_capability"]
        == "observe_numeric_cli_exits_while_sampling_one_owned_activation_tree_and_failing_closed",
        "essential capability drift",
    )

    prior = record["passed_cli_probe_result"]
    expect(prior["record"] == "phase6_cli_exit_transport_result.json", "prior result drift")
    expect_file_digest(path.parent, prior["record"], prior["sha256"], "prior result")
    expect(prior["status"] == "cli_help_probe_passed_numeric_exit_observed", "prior status drift")

    structure = record["structural_decision"]
    expect_file_digest(path.parent, structure["short_command_module"], structure["short_command_module_sha256"], "transport")
    expect(structure["planned_activation_runner"] == "../run_local_model_load_health.py", "runner path drift")
    expect(structure["new_dependency_count"] == 0, "dependency growth admitted")
    expect(structure["core_sheath_change_required"] is False, "core expansion admitted")
    expect(structure["thread_count"] == 0, "concurrency surface widened")
    expect(structure["general_purpose_process_framework"] is False, "generality overclaim")

    commands = record["command_mapping"]
    expect(
        commands["synchronous_transport"]
        == [
            "temporary_lms_exe daemon up --json",
            "temporary_lms_exe ps --json",
            "temporary_lms_exe unload cyxsheath-qwen25-coder-7b-q4km",
            "temporary_lms_exe daemon down",
        ],
        "control command mapping drift",
    )
    expect(commands["monitored_transport"] == LOAD_COMMAND, "load command drift")
    expect(commands["control_timeout_seconds"] == {"daemon_up": 180, "inventory": 120, "unload": 120, "daemon_down": 120}, "control timeout drift")
    expect(commands["load_timeout_seconds"] == 600, "load timeout drift")
    expect(commands["maximum_control_combined_output_bytes"] == 1048576, "control output bound drift")
    expect(commands["automatic_retry_count"] == 0, "automatic retry admitted")

    monitored = record["monitored_load_contract"]
    expect(monitored["implementation"] == "python_standard_library_subprocess_popen", "load transport drift")
    expect(monitored["shell"] is False and monitored["stdin"] == "null_device", "process boundary widened")
    expect(monitored["stdout_and_stderr"] == "separate_git_ignored_temporary_binary_files", "output location drift")
    expect(monitored["single_same_thread_monitor_loop"] is True, "monitoring design widened")
    expect(monitored["sample_interval_seconds"] == 1, "sample interval drift")
    expect(monitored["maximum_each_temporary_output_file_bytes"] == 1048576, "load output bound drift")
    expect(monitored["output_limit_kind"] == "sampled_file_size_abort_threshold_not_zero_overshoot_guarantee", "output-bound overclaim")
    for key in (
        "output_size_checked_each_monitor_iteration",
        "numeric_returncode_required_after_wait",
        "fail_closed_on_timeout_output_breach_measurement_gap_or_nonzero_exit",
    ):
        expect(monitored[key] is True, f"monitored load gate weakened: {key}")
    expect(monitored["post_load_observation_samples"] == 15, "observation window weakened")

    ownership = record["service_ownership_contract"]
    for key in (
        "clean_baseline_requires_zero_lm_studio_or_lms_processes",
        "clean_baseline_requires_port_1234_absent",
        "capture_after_daemon_command_on_every_exit_path",
        "monitor_only_owned_root_descendants_plus_direct_load_child",
    ):
        expect(ownership[key] is True, f"ownership gate weakened: {key}")
    expect(ownership["readiness_requires_exact_service_root_count"] == 1, "service-root count widened")
    expect(
        ownership["service_root_match"] == "LM Studio.exe_with_run_as_service_command_line",
        "service-root match drift",
    )
    expect(ownership["owned_root_identity"] == "process_id_and_creation_timestamp", "root identity weakened")
    expect(ownership["ambient_process_adoption_allowed"] is False, "ambient process adoption admitted")
    expect(ownership["force_cleanup_scope"] == "captured_owned_process_tree_only", "cleanup scope widened")

    resources = record["resource_and_inventory_contract"]
    expected_limits = {
        "minimum_preload_available_memory_bytes": 21474836480,
        "minimum_observed_available_memory_bytes": 17179869184,
        "maximum_available_memory_drop_bytes": 12884901888,
        "maximum_activation_tree_private_bytes": 12884901888,
        "maximum_activation_tree_working_set_bytes": 12884901888,
        "maximum_gpu_used_memory_delta_mib": 512,
    }
    for key, expected in expected_limits.items():
        expect(resources[key] == expected, f"resource limit drift: {key}")
    expect(resources["gpu_sample_attempts"] == 3, "GPU read attempts widened")
    expect(resources["gpu_sample_retry_interval_seconds"] == 1, "GPU retry interval drift")
    expect(resources["http_listener_allowed"] is False, "HTTP listener admitted")
    expect(resources["inventory_before_load"] == "empty", "preload inventory weakened")
    expect(resources["inventory_after_load"] == "exactly_one_expected_identifier_model_key_and_context", "loaded inventory weakened")
    expect(resources["inventory_after_unload"] == "empty", "cleanup inventory weakened")
    expect(resources["missing_measurement_or_inventory"] == "fail_closed", "missing evidence admitted")

    identity = record["identity_contract"]
    expect(identity["cli_version"] == "1.3.3", "CLI version drift")
    expect(identity["cli_bytes"] == 120772792, "CLI size drift")
    expect_digest(identity["cli_sha256"], "CLI")
    expect(identity["cli_sha256"] == "976d4389f97b2cf95b38a4eb673855d8a846f2db21a20eb4fe5e79f7179722f5", "CLI digest drift")
    expect(identity["verify_temporary_cli_before_each_command"] is True, "CLI identity gate weakened")
    expect(identity["engine_package"] == "llama.cpp-win-x86_64-nvidia-cuda-avx2-2.29.1", "engine package drift")
    expect_digest(identity["engine_inventory_sha256"], "engine inventory")
    expect(identity["engine_inventory_sha256"] == "389f3fc28e5ec80ec69a3b904ec844f51dadb789162000532c0b0db738c78561", "engine digest drift")
    expect_digest(identity["engine_preference_sha256"], "engine preference")
    expect(identity["engine_preference_sha256"] == "7448caf18fc92b7e0769924b6cdf1f437279765ff33d2ad7bebccaf22c9857c7", "engine preference drift")
    expect(identity["weight_bytes"] == 4683073536, "weight size drift")
    expect_digest(identity["weight_sha256"], "weight")
    expect(identity["weight_sha256"] == "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c", "weight digest drift")

    cleanup = record["cleanup_contract"]
    for key, value in cleanup.items():
        expect(value is True, f"cleanup gate weakened: {key}")

    fixture = record["fixture_plan"]
    expect(fixture["lm_studio_invocation_count"] == 0, "LM Studio fixture invocation admitted")
    expect(fixture["use_only_temporary_python_child_processes"] is True, "fixture boundary widened")
    expect(
        fixture["required_behaviors"]
        == [
            "numeric_zero_and_nonzero_exit_observation",
            "timeout_terminates_owned_direct_child",
            "sampled_output_threshold_aborts_child",
            "monitor_callback_runs_while_child_is_live",
            "measurement_failure_aborts_child",
            "literal_arguments_do_not_use_a_shell",
            "temporary_output_is_removed",
            "unowned_process_is_never_terminated",
        ],
        "fixture coverage drift",
    )

    boundary = record["security_and_research_boundary"]
    for key, value in boundary.items():
        if key.endswith("_count"):
            expect(value == 0, f"runtime operation admitted: {key}")
        elif key in {"raw_cli_output_in_curated_evidence", "model_health_conclusion_allowed", "model_quality_conclusion_allowed"}:
            expect(value is False, f"evidence overclaim: {key}")
        else:
            expect(value is False, f"research boundary widened: {key}")

    gate = record["execution_gate"]
    expect(gate["activation_runner_implementation_authorized"] is True, "runner implementation not authorized")
    expect(gate["fixture_test_execution_authorized"] is True, "fixture tests not authorized")
    for key in (
        "lm_studio_runtime_execution_authorized",
        "load_health_retry_authorized",
        "synthetic_canary_authorized",
        "authenticated_http_server_authorized",
        "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"] == "implement_and_fixture_test_exact_activation_runner_without_invoking_lm_studio",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, LoadHealthTransportIntegrationDecisionError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print("VALID: load-health transport integration designed; implementation/fixtures allowed; runtime blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
