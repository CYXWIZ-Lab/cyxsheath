"""Validate the fixture-only Windows Authenticode adapter design."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


class LlmsterWindowsAuthenticodeAdapterDesignError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterWindowsAuthenticodeAdapterDesignError(message)


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(record["status"] == "llmster_windows_authenticode_adapter_fixture_implementation_authorized_real_tool_blocked", "unsafe status")
    expect(record["decision_scope"] == "design_and_generated_fixture_implementation_of_a_windows_powershell_authenticode_adapter_without_retained_child_access_powershell_discovery_or_signature_tool_invocation", "scope drift")
    expect(record["baseline_commit"] == "3b3034aa2201d950cd3a851b1be43fb61a29241f", "baseline drift")

    policy = record["accepted_policy_result"]
    expect(policy["path"] == "phase6_llmster_authenticode_review_implementation_result.json", "policy path drift")
    expect(hashlib.sha256((path.parent / policy["path"]).read_bytes()).hexdigest() == policy["sha256"], "policy digest drift")
    expect(policy["status"] == "llmster_authenticode_review_policy_implemented_generated_fixtures_passed_real_review_blocked", "policy status drift")

    boundary = record["module_boundary"]
    expect(boundary["new_adapter_module"] == "Thesis.pilot_data.llmster_windows_authenticode", "adapter module drift")
    expect(boundary["new_fixed_script"] == "Thesis/pilot_data/get_authenticode_status.ps1", "script drift")
    for key in ("policy_module_remains_tree_admission_and_aggregate_evidence_owner", "existing_cli_transport_reused_unchanged", "fake_transport_only_at_this_gate"):
        expect(boundary[key] is True, f"module guard disabled: {key}")
    transport_path = path.parent.parent / "cli_transport.py"
    expect(hashlib.sha256(transport_path.read_bytes()).hexdigest() == boundary["existing_cli_transport_sha256"], "transport source drift")
    expect(boundary["new_dependencies_allowed"] is False, "dependency admitted")

    powershell = record["powershell_contract"]
    expect(powershell["executable_name_case_insensitive"] == "powershell.exe", "executable drift")
    expect(powershell["arguments"] == ["-NoLogo", "-NoProfile", "-NonInteractive", "-File", "<fixed_absolute_script>", "-CandidatePath", "<absolute_candidate>"], "argv drift")
    for key in ("executable_must_be_absolute_existing_regular_non_link", "expected_executable_sha256_required", "executable_identity_checked_before_and_after_transport", "candidate_passed_as_file_parameter_literal_string", "script_uses_get_authenticode_signature_literal_path"):
        expect(powershell[key] is True, f"PowerShell guard disabled: {key}")
    for key in ("shell", "execution_policy_override_added", "profile_loading_allowed", "interactive_input_allowed", "candidate_path_interpolated_into_powershell_source"):
        expect(powershell[key] is False, f"unsafe PowerShell behavior admitted: {key}")

    candidate = record["candidate_contract"]
    expect(candidate["suffixes_case_insensitive"] == [".dll", ".exe", ".node", ".ps1"], "suffix drift")
    for key in ("absolute_existing_regular_non_link_required", "candidate_identity_checked_before_and_after_transport"):
        expect(candidate[key] is True, f"candidate guard disabled: {key}")
    expect(candidate["one_transport_call_per_candidate_maximum"] == 1, "transport call widened")
    expect(candidate["automatic_retry_count_maximum"] == 0, "retry admitted")

    transport = record["transport_contract"]
    expect(transport["timeout_seconds"] == 10, "timeout drift")
    expect(transport["combined_retained_output_bytes_maximum"] == 4096, "output bound drift")
    expect(transport["stdout_json_bytes_maximum"] == 512, "JSON bound drift")
    expect(transport["timeout_maps_to"] == "timeout", "timeout mapping drift")
    expect(transport["transport_start_output_or_parse_failure_maps_to"] == "tool_error", "tool-error mapping drift")
    expect(transport["batch_maximum_candidate_calls"] == 91, "batch bound drift")
    for key in ("stderr_must_be_empty_on_success", "numeric_exit_zero_required_for_status", "transport_invoked_without_shell_by_existing_source_bound_transport", "batch_deadline_requires_later_execution_decision"):
        expect(transport[key] is True, f"transport guard disabled: {key}")

    response = record["response_contract"]
    expect(response["encoding"] == "utf-8-with-optional-bom", "encoding drift")
    expect(response["exact_json_keys"] == ["schema_version", "status"], "response keys drift")
    expect(response["schema_version"] == "1.0.0", "response schema drift")
    for key in ("duplicate_json_keys_rejected", "status_must_be_nonempty_bounded_ascii_text", "raw_stdout_stderr_status_messages_and_certificate_fields_not_curated", "typed_policy_observation_returned"):
        expect(response[key] is True, f"response guard disabled: {key}")

    for key, value in record["network_boundary"].items():
        expect(value is True, f"network guard disabled: {key}")
    for key, value in record["fixture_requirements"].items():
        expect(value is True, f"fixture requirement disabled: {key}")
    gate = record["execution_gate"]
    for key in ("adapter_script_and_generated_fixture_edits_authorized", "fake_transport_calls_authorized"):
        expect(gate[key] is True, f"fixture work not authorized: {key}")
    for key in ("retained_child_enumeration_or_content_read_authorized", "real_powershell_discovery_identity_read_or_invocation_authorized", "authenticode_tool_invocation_authorized", "network_request_authorized", "installation_authorized", "target_binary_execution_authorized", "retained_child_modification_or_removal_authorized", "benchmark_input_authorized"):
        expect(gate[key] is False, f"scope widened: {key}")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    try:
        record = validate(arguments.path)
    except (KeyError, OSError, TypeError, json.JSONDecodeError, LlmsterWindowsAuthenticodeAdapterDesignError) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
