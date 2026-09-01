"""Validate the fixture-only Authenticode execution-preflight design."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


class LlmsterAuthenticodeExecutionPreflightDesignError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterAuthenticodeExecutionPreflightDesignError(message)


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(record["status"] == "llmster_authenticode_execution_preflight_fixture_implementation_authorized_real_host_state_blocked", "unsafe status")
    expect(record["decision_scope"] == "design_and_generated_fixture_implementation_of_a_pure_authenticode_execution_preflight_without_retained_child_powershell_firewall_or_signature_tool_access", "scope drift")
    expect(record["baseline_commit"] == "eacadc018060dbe44d2b62d09416b90b6113b971", "baseline drift")

    inputs = record["accepted_inputs"]
    expected = {
        "adapter_implementation": ("phase6_llmster_windows_authenticode_adapter_implementation_result.json", "llmster_windows_authenticode_adapter_implemented_generated_fixtures_passed_real_tool_blocked"),
        "review_policy_implementation": ("phase6_llmster_authenticode_review_implementation_result.json", "llmster_authenticode_review_policy_implemented_generated_fixtures_passed_real_review_blocked"),
        "retained_staging_result": ("phase6_llmster_real_staging_execution_result.json", "llmster_real_archive_owned_staging_accepted_signature_installation_execution_blocked"),
    }
    for key, (name, status) in expected.items():
        item = inputs[key]
        expect(item["path"] == name, f"input path drift: {key}")
        expect(hashlib.sha256((path.parent / name).read_bytes()).hexdigest() == item["sha256"], f"input digest drift: {key}")
        expect(item["status"] == status, f"input status drift: {key}")
    staging = inputs["retained_staging_result"]
    expect(staging["content_manifest_sha256"] == "9c6600dc9a72b265d3d37abf5d499c1cd760561ac026ace2629ea452cc3b4a45", "content manifest drift")
    expect(staging["candidate_count"] == 91, "candidate count drift")
    expect(staging["candidate_paths_sha256"] == "d2cfc905e98305006a5f80b65951cb1927be48a7f308ae22c10d077366faa90e", "candidate digest drift")

    boundary = record["module_boundary"]
    expect(boundary["new_module"] == "Thesis.pilot_data.llmster_authenticode_execution_preflight", "module drift")
    for key in ("review_policy_remains_owned_tree_admission_candidate_order_and_aggregate_result_owner", "windows_adapter_remains_single_candidate_process_and_response_owner", "later_firewall_provider_owns_host_state_mutation_and_observation", "later_execution_runner_owns_atomic_claim_deadline_and_cleanup", "preflight_has_no_filesystem_process_network_firewall_or_clock_io"):
        expect(boundary[key] is True, f"module boundary weakened: {key}")
    expect(boundary["new_dependencies_allowed"] is False, "dependency admitted")

    powershell = record["powershell_observation_contract"]
    expect(powershell["basename_case_insensitive"] == "powershell.exe", "PowerShell name drift")
    for key in ("absolute_path_required", "regular_non_link_observed", "positive_byte_count_required", "lowercase_sha256_required", "observation_source_must_be_later_source_bound_provider", "expected_digest_is_passed_unchanged_to_windows_adapter"):
        expect(powershell[key] is True, f"PowerShell guard weakened: {key}")
    expect(powershell["real_discovery_or_hashing_at_this_gate"] is False, "real PowerShell access admitted")

    containment = record["external_containment_contract"]
    expect(containment["provider"] == "windows_defender_firewall_windows_filtering_platform", "containment provider drift")
    expect(containment["direction"] == "Outbound", "firewall direction drift")
    expect(containment["action"] == "Block", "firewall action drift")
    expect(containment["profiles"] == ["Domain", "Private", "Public"], "profile drift")
    expect(containment["protocol"] == "Any", "protocol drift")
    for key, value in containment.items():
        if isinstance(value, bool):
            expect(value is True, f"containment guard weakened: {key}")
    expect(containment["local_and_remote_addresses"] == "Any", "address scope drift")
    expect(containment["local_and_remote_ports"] == "Any", "port scope drift")

    batch = record["batch_contract"]
    expect(batch["candidate_count"] == 91, "batch candidate drift")
    expect(batch["maximum_adapter_calls"] == 91, "adapter call bound widened")
    expect(batch["individual_adapter_timeout_seconds"] == 10, "adapter timeout drift")
    expect(batch["overall_deadline_seconds"] == 300, "batch deadline drift")
    expect(batch["minimum_remaining_seconds_before_next_adapter_call"] == 10, "remaining-time guard drift")
    expect(batch["automatic_retry_count_maximum"] == 0, "retry admitted")
    expect(batch["target_binary_launch_count_maximum"] == 0, "binary launch admitted")
    for key in ("candidate_order_owned_by_review_policy", "deadline_is_operational_safety_bound_not_performance_claim", "deadline_expiry_stops_before_next_call_and_produces_normalized_incomplete_result"):
        expect(batch[key] is True, f"batch guard weakened: {key}")

    one_shot = record["one_shot_contract"]
    expect(one_shot["maximum_runner_invocations"] == 1, "runner count widened")
    expect(one_shot["automatic_retry_count_maximum"] == 0, "one-shot retry admitted")
    for key, value in one_shot.items():
        if isinstance(value, bool):
            expect(value is True, f"one-shot guard weakened: {key}")
    for key, value in record["output_contract"].items():
        expect(value is True, f"output guard weakened: {key}")
    for key, value in record["fixture_requirements"].items():
        expect(value is True, f"fixture requirement weakened: {key}")

    gate = record["execution_gate"]
    for key in ("preflight_source_and_generated_fixture_edits_authorized", "generated_observation_validation_authorized"):
        expect(gate[key] is True, f"fixture work not authorized: {key}")
    for key in ("retained_child_enumeration_or_content_read_authorized", "real_powershell_discovery_identity_read_or_invocation_authorized", "firewall_state_read_create_modify_or_remove_authorized", "event_log_read_or_audit_policy_change_authorized", "authenticode_tool_invocation_authorized", "network_request_authorized", "installation_authorized", "target_binary_execution_authorized", "retained_child_modification_or_removal_authorized", "benchmark_input_authorized"):
        expect(gate[key] is False, f"scope widened: {key}")
    expect(record["next_action"] == "implement_and_source_bind_the_pure_preflight_with_generated_observations_only_then_make_a_separate_provider_design_before_any_real_host_state_or_retained_child_access", "next action drift")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    try:
        record = validate(arguments.path)
    except (KeyError, OSError, TypeError, json.JSONDecodeError, LlmsterAuthenticodeExecutionPreflightDesignError) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
