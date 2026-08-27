"""Validate the source-only Phase-6 runtime lifecycle selection decision."""

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


class RuntimeLifecycleSelectionDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeLifecycleSelectionDecisionError(message)


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
        == "standalone_llmster_selected_acquisition_review_pending_runtime_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "source_and_evidence_runtime_lifecycle_selection_no_download_installation_or_invocation",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    reviewed = record["reviewed_evidence"]
    implementation = expect_evidence(
        path.parent,
        reviewed["shutdown_implementation"],
        "phase6_shutdown_observation_implementation_result.json",
        "shutdown_observation_implemented_fixtures_passed_runtime_blocked",
    )
    result = expect_evidence(
        path.parent,
        reviewed["failed_load_health_result"],
        "phase6_load_health_runner_execution_result.json",
        "model_load_and_resource_gates_observed_shutdown_acceptance_failed",
    )
    expect_evidence(
        path.parent,
        reviewed["local_runtime_model_decision"],
        "phase6_local_runtime_model_decision.json",
        "runtime_model_selected_download_pending_synthetic_only",
    )
    expect(implementation["decision_gate"]["lm_studio_runtime_execution_authorized"] is False, "prior boundary widened")
    expect(result["acceptance"]["graceful_shutdown_gate_passed"] is False, "prior failure concealed")

    for key, value in record["required_lifecycle_invariants"].items():
        expect(value is True, f"required invariant weakened: {key}")

    sources = record["official_primary_sources"]
    expect(sources["reviewed_on"] == "2026-08-27", "source review date drift")
    expected_urls = {
        "headless_documentation": "https://lmstudio.ai/docs/developer/core/headless",
        "product_distinction_documentation": "https://lmstudio.ai/docs/app/basics/lmstudio-vs-llmster-vs-lms",
        "daemon_up_documentation": "https://lmstudio.ai/docs/cli/daemon/daemon-up",
        "daemon_down_documentation": "https://lmstudio.ai/docs/cli/daemon/daemon-down",
        "daemon_status_documentation": "https://lmstudio.ai/docs/cli/daemon/daemon-status",
        "windows_installer_source": "https://lmstudio.ai/install.ps1",
    }
    for key, expected in expected_urls.items():
        expect(sources[key] == expected, f"official source drift: {key}")
    for key, value in sources["source_observations"].items():
        expect(value is True, f"official behavior concealed: {key}")

    selection = record["selection"]
    expect(selection["decision_id"] == "phase6-runtime-lifecycle-001", "selection identity drift")
    expect(selection["selected_family"] == "standalone_llmster", "incompatible lifecycle selected")
    expect(selection["selected_process_root"] == "llmster.exe", "selected root drift")
    expect(selection["selected_control_surface"] == "pinned_lms_cli_daemon_json_commands", "control surface drift")
    expect(selection["existing_mode_aware_runner_compatible"] is True, "runner compatibility concealed")
    expect(selection["new_core_abstraction_required"] is False, "core expansion admitted")
    expect(selection["new_runtime_adapter_required"] is False, "parallel adapter admitted")
    expect(selection["model_or_quantization_change_required"] is False, "model drift admitted")
    expect(selection["installation_status"] == "not_established_by_this_decision", "installation overclaim")
    expect(selection["runtime_health_status"] == "not_tested", "runtime health overclaim")

    alternatives = {item["family"]: item for item in record["rejected_alternatives"]}
    expect(set(alternatives) == {
        "lm_studio_desktop_headless_service",
        "forced_desktop_process_termination",
        "direct_llama_cpp_server",
    }, "alternative set drift")
    expect(alternatives["lm_studio_desktop_headless_service"]["decision"] == "rejected_for_bounded_experiment_lifecycle", "desktop mode admitted")
    expect(alternatives["forced_desktop_process_termination"]["decision"] == "retained_only_as_failed_safety_fallback", "forced cleanup accepted")
    expect(alternatives["direct_llama_cpp_server"]["decision"] == "not_selected", "parallel runtime admitted")

    installer = record["windows_installer_review"]
    expect(installer["reviewed_reported_version"] == "0.0.21-2", "installer version drift")
    expect(installer["reviewed_x64_release_name"] == "0.0.21-2-win32-x64.full.zip", "archive identity drift")
    expect(installer["artifact_host"] == "https://llmster.lmstudio.ai/download", "artifact host drift")
    for key in (
        "installer_is_mutable_network_source",
        "installer_downloads_then_executes_llmster_bootstrap",
        "installer_can_modify_path",
        "missing_checksum_can_skip_verification",
        "hashing_error_can_skip_verification",
        "potential_existing_cli_home_collision_requires_preflight",
    ):
        expect(installer[key] is True, f"installer risk concealed: {key}")
    expect(installer["official_shell_pipeline_authorized"] is False, "mutable shell pipeline authorized")
    expect(installer["installer_checksum_algorithm"] == "sha512", "checksum algorithm drift")
    expect(installer["installer_checksum_is_mandatory"] is False, "checksum behavior overclaim")
    expect(installer["automatic_daemon_update_allowed"] is False, "automatic update admitted")

    for key, value in record["required_acquisition_preflight"].items():
        expect(value is True, f"acquisition preflight weakened: {key}")

    boundary = record["security_and_research_boundary"]
    for key, value in boundary.items():
        if key.endswith("_count"):
            expect(value == 0, f"operation admitted: {key}")
        else:
            expect(value is False, f"research boundary widened: {key}")

    gate = record["decision_gate"]
    expect(gate["runtime_lifecycle_selected"] is True, "lifecycle selection missing")
    expect(gate["selected_lifecycle"] == "standalone_llmster", "gate lifecycle drift")
    for key in (
        "desktop_service_retry_authorized",
        "installer_or_archive_download_authorized",
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
        == "make_a_separate_pinned_llmster_acquisition_preflight_decision_before_downloading_or_installing_any_artifact",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, RuntimeLifecycleSelectionDecisionError) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: standalone llmster selected; acquisition and runtime remain blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
