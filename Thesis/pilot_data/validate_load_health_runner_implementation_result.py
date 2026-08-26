"""Validate the runtime-blocked Phase-6 activation-runner implementation result."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from validate_load_health_runner_one_shot_correction_result import (
    LoadHealthRunnerOneShotCorrectionError,
    validate as validate_one_shot_correction,
)
from validate_load_health_runner_execution_decision import (
    LoadHealthRunnerExecutionDecisionError,
    validate as validate_execution_decision,
)


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
CORRECTION_RESULT = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_load_health_runner_one_shot_correction_result.json"
)
EXECUTION_DECISION = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_load_health_runner_execution_decision.json"
)


class LoadHealthRunnerImplementationResultError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LoadHealthRunnerImplementationResultError(message)


def check_forbidden(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN & set(value)
        expect(not found, f"{where}: forbidden keys {sorted(found)}")
        for key, child in value.items():
            check_forbidden(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_forbidden(child, f"{where}[{index}]")


def expect_file(base: Path, record: dict, *, role: str | None = None) -> None:
    path = (base / record["path"]).resolve()
    expect(path.is_file(), f"implementation file missing: {record['path']}")
    content = path.read_bytes()
    expect(DIGEST.fullmatch(record["sha256"]) is not None, f"malformed digest: {record['path']}")
    actual = {
        "bytes": len(content),
        "lines": len(content.decode("utf-8").splitlines()),
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    historical = {key: record[key] for key in ("bytes", "lines", "sha256")}
    if actual != historical:
        try:
            correction = validate_one_shot_correction(CORRECTION_RESULT)
        except (OSError, KeyError, TypeError, json.JSONDecodeError, LoadHealthRunnerOneShotCorrectionError) as error:
            raise LoadHealthRunnerImplementationResultError(
                f"validated correction unavailable: {record['path']}"
            ) from error
        transitions = {item["path"]: item for item in correction["code_transition"]}
        transition = transitions.get(record["path"])
        needs_successor = False
        if transition is not None and transition["previous"] == historical:
            if transition["corrected"] == actual:
                transition = None
            else:
                historical = transition["corrected"]
                needs_successor = True
        elif record["path"] == "../lm_studio_windows.py":
            needs_successor = True
        else:
            expect(False, f"file digest drift without validated correction: {record['path']}")
        if needs_successor:
            try:
                execution = validate_execution_decision(EXECUTION_DECISION)
            except (
                OSError,
                KeyError,
                TypeError,
                json.JSONDecodeError,
                LoadHealthRunnerExecutionDecisionError,
            ) as error:
                raise LoadHealthRunnerImplementationResultError(
                    f"validated execution correction unavailable: {record['path']}"
                ) from error
            labels = {
                "../lm_studio_windows.py": "windows_adapter",
                "../run_local_model_load_health.py": "runner",
                "../test_run_local_model_load_health.py": "runner_test",
            }
            successor = execution["canonicalization_correction"]["source_transition"].get(
                labels.get(record["path"], "")
            )
            expect(
                successor is not None
                and successor["previous_sha256"] == historical["sha256"]
                and successor["corrected_sha256"] == actual["sha256"],
                f"file digest drift without validated correction: {record['path']}",
            )
    if role is not None:
        expect(record["role"] == role, f"module role drift: {record['path']}")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"] == "activation_runner_implemented_fixtures_passed_runtime_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "implementation_and_python_child_fixtures_only_no_lm_studio_runtime_authorization",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    decision = record["integration_decision"]
    expect(decision["record"] == "phase6_load_health_transport_integration_decision.json", "decision record drift")
    decision_path = path.parent / decision["record"]
    expect(hashlib.sha256(decision_path.read_bytes()).hexdigest() == decision["sha256"], "decision digest drift")
    expect(
        decision["status"]
        == "load_health_transport_integration_designed_runner_implementation_authorized",
        "decision status drift",
    )

    identity = record["implementation_identity"]
    modules = identity["modules"]
    expected_modules = [
        ("../monitored_process.py", "one_owned_child_lifecycle_sampling_timeout_output_and_direct_child_cleanup"),
        ("../lm_studio_windows.py", "windows_host_inventory_identity_resource_and_exact_process_adapter"),
        ("../run_local_model_load_health.py", "frozen_lm_studio_load_health_protocol_and_privacy_minimized_local_result"),
    ]
    expect([item["path"] for item in modules] == [item[0] for item in expected_modules], "module set drift")
    for item, (_, role) in zip(modules, expected_modules, strict=True):
        expect_file(path.parent, item, role=role)
    tests = identity["tests"]
    expect([item["path"] for item in tests] == ["../test_monitored_process.py", "../test_run_local_model_load_health.py"], "test set drift")
    for item in tests:
        expect_file(path.parent, item)
    expect(identity["existing_short_command_module"] == "../cli_transport.py", "CLI module drift")
    cli_path = (path.parent / identity["existing_short_command_module"]).resolve()
    expect(hashlib.sha256(cli_path.read_bytes()).hexdigest() == identity["existing_short_command_module_sha256"], "CLI module digest drift")
    expect(identity["new_dependency_count"] == 0, "dependency growth admitted")
    expect(identity["core_sheath_change_required"] is False, "core expansion admitted")
    expect(identity["thread_count"] == 0, "concurrency surface widened")

    boundary = record["module_boundary"]
    expect(boundary["duplicate_transport_implementation_added"] is False, "duplicate transport admitted")
    expect(boundary["general_purpose_framework_added"] is False, "framework growth admitted")

    runtime = record["frozen_runtime_contract"]
    expect(runtime["daemon_up"] == "temporary_lms_exe daemon up --json", "daemon command drift")
    expect(runtime["inventory"] == "temporary_lms_exe ps --json", "inventory command drift")
    expect("--gpu off" in runtime["load"] and "--context-length 8192" in runtime["load"], "load command drift")
    expect(runtime["unload"] == "temporary_lms_exe unload cyxsheath-qwen25-coder-7b-q4km", "unload drift")
    expect(runtime["daemon_down"] == "temporary_lms_exe daemon down", "daemon-down drift")
    for key in ("short_commands_use_synchronous_transport", "load_uses_one_popen_child", "single_same_thread_monitor_loop"):
        expect(runtime[key] is True, f"transport contract weakened: {key}")
    expect(runtime["load_timeout_seconds"] == 600, "load timeout drift")
    expect(runtime["sample_interval_seconds"] == 1, "sample interval drift")
    expect(runtime["maximum_each_load_output_file_bytes"] == 1048576, "output limit drift")
    expect(runtime["post_load_observation_samples"] == 15, "observation window drift")
    expect(runtime["automatic_retry_count"] == 0, "automatic retry admitted")

    ownership = record["ownership_and_cleanup"]
    for key, value in ownership.items():
        if key == "ambient_process_adoption_allowed":
            expect(value is False, "ambient process adoption admitted")
        elif key == "force_scope":
            expect(value == "captured_pid_and_creation_time_identities_only", "force scope widened")
        else:
            expect(value is True, f"ownership or cleanup gate weakened: {key}")

    fixture = record["fixture_evidence"]
    for version in ("python_3_12", "python_3_14"):
        expect(fixture[version] == {"tests_run": 14, "tests_passed": 14}, f"fixture evidence drift: {version}")
    expect(len(fixture["monitored_process_behaviors"]) == 8, "monitor fixture coverage drift")
    expect(len(fixture["runner_behaviors"]) == 6, "runner fixture coverage drift")
    for key in ("lm_studio_invocation_count", "model_load_command_count", "host_snapshot_invocation_count_in_blocked_runner_test"):
        expect(fixture[key] == 0, f"fixture runtime operation admitted: {key}")

    gate = record["runtime_gate"]
    expect(gate["required_execution_authorization_record"] == "phase6_load_health_runner_execution_decision.json", "authorization record drift")
    expect(gate["execution_authorization_present_at_checkpoint"] is False, "unrecorded authorization admitted")
    expect(gate["missing_authorization_exit_code"] == 2, "blocked exit drift")
    expect(gate["cache_created_when_authorization_missing"] is False, "blocked path side effect admitted")
    expect(gate["runner_monitor_and_windows_adapter_digests_must_match_future_authorization"] is True, "code identity gate weakened")
    expect(gate["one_existing_result_blocks_another_attempt"] is True, "one-shot gate weakened")
    expect(gate["runtime_execution_authorized"] is False, "runtime prematurely authorized")

    limits = record["known_limits"]
    for key, value in limits.items():
        expect(value is False, f"implementation overclaim: {key}")

    security = record["security_and_research_boundary"]
    for key, value in security.items():
        if key.endswith("_count"):
            expect(value == 0, f"runtime operation admitted: {key}")
        else:
            expect(value is False, f"research boundary widened: {key}")

    execution = record["execution_gate"]
    expect(execution["runner_implementation_complete"] is True, "implementation not complete")
    expect(execution["fixture_gate_passed"] is True, "fixture gate not passed")
    for key in ("load_health_execution_authorized", "synthetic_canary_authorized", "authenticated_http_server_authorized", "benchmark_input_authorized"):
        expect(execution[key] is False, f"premature authorization: {key}")
    expect(
        execution["next_action"]
        == "make_separate_validator_backed_one_shot_execution_decision_for_exact_pinned_runner_or_stop",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, LoadHealthRunnerImplementationResultError) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: activation runner implemented; fixtures=28/28; LM Studio runtime blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
