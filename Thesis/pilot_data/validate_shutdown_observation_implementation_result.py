"""Validate the fixture-only Phase-6 shutdown-observation implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
SUCCESSOR_RECORD = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_shutdown_observation_implementation_result.json"
)
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


class ShutdownObservationImplementationError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise ShutdownObservationImplementationError(message)


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
        == "shutdown_observation_implemented_fixtures_passed_runtime_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "mode_aware_lifecycle_implementation_and_python_fixtures_only_no_lm_studio_runtime_authorization",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    decision = record["reviewed_decision"]
    expect(decision["record"] == "phase6_shutdown_contract_review_decision.json", "decision record drift")
    decision_path = path.parent / decision["record"]
    expect(hashlib.sha256(decision_path.read_bytes()).hexdigest() == decision["sha256"], "decision digest drift")
    decision_record = json.loads(decision_path.read_text(encoding="utf-8"))
    expect(decision_record["status"] == decision["status"], "decision status drift")
    expect(
        decision_record["decision_gate"]["shutdown_observation_implementation_and_fixtures_authorized"]
        is True,
        "implementation authority missing",
    )
    expect(
        decision_record["decision_gate"]["lm_studio_runtime_execution_authorized"] is False,
        "prior runtime boundary widened",
    )

    transitions = record["source_transition"]
    expected = {
        "../cli_transport.py": ("9e892ff200c22f5b1c50716cbd6aa3a4dfb74cac4238dd18d9ff6e222e5bc0b5", "unchanged"),
        "../lm_studio_lifecycle.py": (None, "new"),
        "../lm_studio_windows.py": ("957dea4b298fe18f7016f804008bbca27704b900cc3337d283408d340697bcfb", "corrected"),
        "../run_local_model_load_health.py": ("014dc055b573f7ce19f53825c9fba1c0a0281c210973d82177d1090cec2b25f2", "corrected"),
        "../test_lm_studio_lifecycle.py": (None, "new"),
        "../test_run_local_model_load_health.py": ("694153f4a25561cf86a4f8228f308a8cf47921fc402628707976cc5e1a249779", "corrected"),
    }
    expect([item["path"] for item in transitions] == list(expected), "source set drift")
    for item in transitions:
        previous, change = expected[item["path"]]
        expect(item["previous_sha256"] == previous, f"previous source drift: {item['path']}")
        expect(item["change"] == change, f"change classification drift: {item['path']}")
        target = (path.parent / item["path"]).resolve()
        expect(target.is_file(), f"source missing: {item['path']}")
        current = file_identity(target)
        expect(
            {key: item[key] for key in ("bytes", "lines", "sha256")} == current,
            f"source identity drift: {item['path']}",
        )
        expect(DIGEST.fullmatch(item["sha256"]) is not None, f"malformed digest: {item['path']}")
        if change == "unchanged":
            expect(item["sha256"] == previous, f"unchanged source modified: {item['path']}")
        elif change == "corrected":
            expect(item["sha256"] != previous, f"source correction concealed: {item['path']}")
    boundary = record["module_boundary"]
    expect(boundary["transport_owns_process_execution_only"] is True, "transport boundary weakened")
    expect(boundary["lifecycle_module_owns_vendor_json_mode_diagnostics_and_polling"] is True, "lifecycle boundary weakened")
    expect(boundary["windows_adapter_owns_pid_creation_time_and_force_scope"] is True, "host boundary weakened")
    expect(boundary["runner_owns_protocol_orchestration_only"] is True, "runner boundary weakened")
    expect(boundary["new_dependency_count"] == 0, "dependency growth admitted")
    expect(boundary["new_thread_count"] == 0, "concurrency growth admitted")
    expect(boundary["core_sheath_change_required"] is False, "core expansion admitted")

    startup = record["startup_contract"]
    expect(startup["command"] == "temporary_lms_exe daemon up --json", "startup command drift")
    expect(startup["required_fields"] == ["status", "pid", "isDaemon", "version"], "startup fields drift")
    expect(startup["required_status"] == "running", "startup status weakened")
    expect(startup["required_is_daemon"] is True, "daemon mode weakened")
    expect(startup["owned_root_source"] == "vendor_reported_pid_plus_allowed_service_root_name", "ownership source drift")
    expect(startup["desktop_service_action"] == "fail_before_model_load", "desktop mode widened")

    control = record["control_evidence_contract"]
    for key in (
        "numeric_exit_retained",
        "stdout_stderr_lengths_retained",
        "stdout_stderr_sha256_retained",
        "allowlisted_diagnostic_code_retained",
    ):
        expect(control[key] is True, f"control evidence removed: {key}")
    expect(control["raw_control_output_retained"] is False, "raw control output retained")

    shutdown = record["shutdown_contract"]
    expect(
        shutdown["sequence"]
        == [
            "unload_exact_identifier_if_load_started",
            "require_empty_loaded_inventory",
            "require_running_standalone_status_with_owned_pid",
            "run_daemon_down_once",
            "poll_daemon_status_until_not_running_or_timeout",
            "require_owned_root_exit_and_zero_runtime_artifacts",
            "use_exact_owned_tree_force_only_as_failed_safety_fallback",
        ],
        "shutdown sequence drift",
    )
    for key in (
        "daemon_down_exit_zero_required",
        "final_status_not_running_required",
        "owned_root_exit_required",
        "empty_inventory_required",
        "port_1234_absent_required",
    ):
        expect(shutdown[key] is True, f"shutdown acceptance weakened: {key}")
    expect(shutdown["forced_cleanup_accepted"] is False, "forced cleanup accepted")

    fixture = record["fixture_evidence"]
    for version in ("python_3_12", "python_3_14"):
        expect(fixture[version] == {"tests_run": 252, "tests_passed": 252}, f"full fixture drift: {version}")
    expect(fixture["focused_lifecycle_tests"] == 10, "lifecycle fixture count drift")
    expect(fixture["focused_runner_tests"] == 11, "runner fixture count drift")
    expect(fixture["implementation_decision_mutation_tests"] == 8, "mutation fixture count drift")
    for key in (
        "lm_studio_invocation_count",
        "model_load_command_count",
        "inference_request_count",
        "http_server_start_count",
        "cyxcode_invocation_count",
        "docker_container_count",
    ):
        expect(fixture[key] == 0, f"runtime operation admitted: {key}")

    gate = record["decision_gate"]
    for key in ("shutdown_observation_implementation_complete", "fixture_gate_passed"):
        expect(gate[key] is True, f"implementation gate missing: {key}")
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
        == "make_a_separate_validator_backed_runtime_selection_decision_before_any_lm_studio_operation",
        "next action drift",
    )
    return record


def historical_source_has_successor(
    relative_path: str, historical_sha256: str, current_sha256: str
) -> bool:
    try:
        record = validate(SUCCESSOR_RECORD)
        transitions = {item["path"]: item for item in record["source_transition"]}
        item = transitions.get(relative_path)
        return bool(
            item is not None
            and item["previous_sha256"] == historical_sha256
            and item["sha256"] == current_sha256
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError, ShutdownObservationImplementationError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, ShutdownObservationImplementationError) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: mode-aware shutdown observation implemented; fixtures passed; runtime blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
