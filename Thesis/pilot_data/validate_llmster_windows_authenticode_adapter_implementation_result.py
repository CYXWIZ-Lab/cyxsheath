"""Validate the fixture-only Windows Authenticode adapter implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

try:
    from .validate_llmster_windows_authenticode_adapter_design_decision import validate as validate_design
except ImportError:
    from validate_llmster_windows_authenticode_adapter_design_decision import validate as validate_design


DIGEST = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN = {
    "absolute_candidate_path",
    "candidate_path",
    "candidate_paths",
    "raw_stdout",
    "raw_stderr",
    "raw_status_message",
    "certificate",
    "certificate_subject",
    "thumbprint",
    "hostname",
    "username",
    "credential",
    "api_token",
}


class LlmsterWindowsAuthenticodeAdapterImplementationError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterWindowsAuthenticodeAdapterImplementationError(message)


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
    expect(record["status"] == "llmster_windows_authenticode_adapter_implemented_generated_fixtures_passed_real_tool_blocked", "unsafe status")
    expect(record["decision_scope"] == "dependency_free_windows_authenticode_adapter_fixed_script_and_generated_fake_transport_fixtures_only_without_retained_child_or_real_powershell_access", "scope drift")
    expect(record["baseline_commit"] == "722df1c66fc8471ec673fa30e04ef7a3b153021c", "baseline drift")

    reviewed = record["reviewed_decision"]
    expect(reviewed["record"] == "phase6_llmster_windows_authenticode_adapter_design_decision.json", "design path drift")
    design_path = path.parent / reviewed["record"]
    expect(DIGEST.fullmatch(reviewed["sha256"]) is not None, "malformed design digest")
    expect(hashlib.sha256(design_path.read_bytes()).hexdigest() == reviewed["sha256"], "design digest drift")
    design = validate_design(design_path)
    expect(design["status"] == reviewed["status"], "design status drift")
    expect(design["execution_gate"]["adapter_script_and_generated_fixture_edits_authorized"] is True, "fixture authority missing")
    expect(design["execution_gate"]["authenticode_tool_invocation_authorized"] is False, "design boundary widened")

    sources = record["source_identity"]
    expected_paths = ["../cli_transport.py", "../llmster_authenticode_review.py", "../get_authenticode_status.ps1", "../llmster_windows_authenticode.py", "../test_llmster_windows_authenticode.py", "../../../.gitattributes"]
    expected_changes = ["unchanged_reused_transport", "unchanged_typed_observation_contract", "new_fixed_script", "new_adapter", "new_generated_fixture_tests", "modified_force_ps1_lf"]
    expect([item["path"] for item in sources] == expected_paths, "source set drift")
    expect([item["change"] for item in sources] == expected_changes, "source classification drift")
    for item in sources:
        expect(DIGEST.fullmatch(item["sha256"]) is not None, f"malformed source digest: {item['path']}")
        target = (path.parent / item["path"]).resolve()
        expect(target.is_file(), f"source missing: {item['path']}")
        expect({key: item[key] for key in ("bytes", "lines", "sha256")} == file_identity(target), f"source identity drift: {item['path']}")

    script = (path.parent / "../get_authenticode_status.ps1").resolve().read_text(encoding="utf-8")
    expect("Get-AuthenticodeSignature -LiteralPath $CandidatePath" in script, "literal-path script drift")
    for forbidden in ("Invoke-Expression", "Start-Process", "Set-ExecutionPolicy"):
        expect(forbidden not in script, f"unsafe script surface admitted: {forbidden}")

    boundary = record["module_boundary"]
    for key in ("policy_module_unchanged_and_owns_tree_admission_and_aggregation", "adapter_owns_identity_argv_transport_mapping_and_strict_response_parsing", "fixed_script_owns_one_literal_path_cmdlet_call_and_minimal_json_output", "cli_transport_unchanged_and_owns_shell_false_timeout_and_retention", "real_transport_capability_present_but_not_invoked_or_authorized", "egress_containment_not_claimed_by_adapter", "repository_attributes_force_ps1_lf_for_stable_script_identity"):
        expect(boundary[key] is True, f"module boundary weakened: {key}")
    for key in ("sheath_core_changed", "cyxcode_changed"):
        expect(boundary[key] is False, f"scope expansion admitted: {key}")
    expect(boundary["new_dependency_count"] == 0, "dependency growth admitted")
    expect(boundary["new_thread_count"] == 0, "concurrency growth admitted")

    for key, value in record["verified_behaviors"].items():
        expect(value is True, f"verified behavior weakened: {key}")
    fixtures = record["fixture_evidence"]
    for version in ("python_3_12", "python_3_14"):
        expect(fixtures[version] == {"tests_run": 567, "tests_passed": 567}, f"full fixture drift: {version}")
    expect(fixtures["focused_adapter_tests"] == 20, "adapter fixture count drift")
    expect(fixtures["implementation_result_tests"] == 10, "result fixture count drift")
    for key in ("generated_candidate_and_fake_executable_fixtures_authorized", "fake_transport_only"):
        expect(fixtures[key] is True, f"fixture boundary concealed: {key}")
    for key, value in fixtures.items():
        if key.endswith("_count"):
            expect(value == 0, f"operation admitted: {key}")

    gate = record["decision_gate"]
    for key in ("windows_adapter_implementation_complete", "generated_fixture_gate_passed"):
        expect(gate[key] is True, f"implementation gate missing: {key}")
    for key in ("retained_child_enumeration_or_content_read_authorized", "real_powershell_discovery_identity_read_or_invocation_authorized", "authenticode_tool_invocation_authorized", "network_request_authorized", "installation_authorized", "target_binary_execution_authorized", "retained_child_modification_or_removal_authorized", "benchmark_input_authorized"):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(gate["next_action"] == "separately_design_and_fixture_test_a_real_execution_preflight_for_exact_powershell_identity_batch_deadline_and_external_zero_egress_evidence_without_retained_child_or_signature_tool_access", "next action drift")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    arguments = parser.parse_args()
    try:
        record = validate(arguments.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, LlmsterWindowsAuthenticodeAdapterImplementationError) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
