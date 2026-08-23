"""Validate the Phase-6 outbound-use and Astropy decision."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
EXPECTED = {
    "phase6-cal-001": ("redis__redis-10068", "submitted_to_big_pickle_no_model_output"),
    "phase6-cal-008": ("fmtlib__fmt-1683", "submitted_to_big_pickle_no_model_output"),
    "phase6-cal-014": ("astropy__astropy-12907", "not_submitted"),
}
FORBIDDEN = {
    "problem_statement",
    "hints_text",
    "patch",
    "test_patch",
    "eval_script",
    "raw_prompt",
    "raw_response",
}


class OutboundDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise OutboundDecisionError(message)


def check_no_raw(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN & set(value)
        expect(not found, f"{where}: forbidden raw-content keys {sorted(found)}")
        for key, child in value.items():
            check_no_raw(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_no_raw(child, f"{where}[{index}]")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_no_raw(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"] == "astropy_retained_free_cloud_blocked_local_path_selected",
        "invalid status",
    )
    expect(
        record["decision_scope"] == "project_research_policy_not_legal_advice",
        "invalid scope",
    )

    decision = record["design_decision"]
    expect(decision["id"] == "phase6-generator-boundary-001", "decision ID drift")
    expect(decision["decision"] == "local_offline_openai_compatible_primary", "local path drift")
    expect(
        decision["implementation_status"] == "pending_synthetic_feasibility_canary",
        "premature local readiness",
    )
    expect(decision["core_change_authorized"] is False, "unauthorized core change")

    sources = record["sources"]
    cards = sources["exact_dataset_cards"]
    expect(cards["verified_declared_license"] is None, "exact-card license overclaim")
    expect(cards["multilingual_declared_license"] == "MIT", "multilingual license drift")
    project = sources["swebench_project"]
    expect(GIT_SHA.fullmatch(project["revision"]) is not None, "bad SWE-bench revision")
    expect(project["project_statement"] == "code_and_data_mit_including_verified", "project evidence drift")
    expect(project["use_inference_documented"] is True, "inference-use evidence missing")
    provider = sources["opencode_zen"]
    expect(GIT_SHA.fullmatch(provider["revision"]) is not None, "bad provider revision")
    expect(provider["route"] == "opencode/mimo-v2.5-free", "provider route drift")
    expect(provider["input_use"] == "may_be_used_to_improve_model", "provider-use mismatch")
    seam = sources["cyxcode_local_seam"]
    expect(seam["interface"] == "custom_openai_compatible_base_url", "local seam mismatch")
    expect(seam["runtime_observed"] == "not_installed", "runtime readiness overclaim")
    expect(seam["container_host_alias_present"] is True, "container-host seam missing")
    for source in (cards, project, provider, seam):
        for key, value in source.items():
            if key.endswith("sha256"):
                expect(DIGEST.fullmatch(value) is not None, f"malformed digest: {key}")

    cases = record["case_decisions"]
    expect(len(cases) == 3, "expected three case decisions")
    expect({case["candidate_id"] for case in cases} == set(EXPECTED), "candidate mismatch")
    for case in cases:
        candidate = case["candidate_id"]
        instance, history = EXPECTED[candidate]
        expect(case["instance_id"] == instance, f"{candidate}: instance mismatch")
        expect(case["research_analysis"] == "allowed", f"{candidate}: analysis unresolved")
        expect(case["model_training"] == "unknown", f"{candidate}: training-right overclaim")
        expect(case["free_mimo_outbound"] == "blocked", f"{candidate}: unsafe free route")
        expect(case["preexisting_generator_exposure"] == "unknown", f"{candidate}: exposure overclaim")
        expect(case["project_outbound_history"] == history, f"{candidate}: history mismatch")
        expect(
            case["contamination_gate"] == "pending_pinned_generator_identity",
            f"{candidate}: premature contamination clearance",
        )
        expect(case["disposition"] == "quarantined", f"{candidate}: premature admission")
        expect(
            set(case["reason_codes"]) == {"artifact.incomplete", "contamination.uncertain"},
            f"{candidate}: blocker mismatch",
        )
    astropy = next(case for case in cases if case["candidate_id"] == "phase6-cal-014")
    expect(astropy["exact_card_license"] == "NOASSERTION", "Astropy exact-card overclaim")
    expect(astropy["supplemental_project_license"] == "MIT", "Astropy supplemental evidence drift")
    expect(astropy["case_selection"] == "retained", "Astropy replacement drift")
    expect(astropy["ledger_event_id"] == "phase6-cal-review-009", "Astropy ledger mismatch")

    boundary = record["execution_boundary"]
    expect(boundary["benchmark_input_authorized"] is False, "benchmark input prematurely authorized")
    expect(boundary["free_mimo_benchmark_submission"] == "blocked", "free route prematurely authorized")
    expect(boundary["local_runtime_installation_authorized"] is False, "runtime install overclaim")
    expect(
        boundary["next_input_class"] == "generated_public_non_sensitive_non_benchmark",
        "unsafe next input class",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, OutboundDecisionError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(
        "VALID: astropy=retained; research_analysis_allowed=3; "
        "free_mimo_benchmark=blocked; local_path=pending"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
