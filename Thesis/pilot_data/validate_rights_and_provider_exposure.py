"""Validate the Phase-6 rights and provider-exposure decision record."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
EXPECTED = {
    "phase6-cal-001": ("multilingual", "allowed"),
    "phase6-cal-008": ("multilingual", "allowed"),
    "phase6-cal-014": ("verified", "unknown"),
}
SUBMISSIONS = {
    "phase6-cal-001": "submitted_no_model_output",
    "phase6-cal-008": "submitted_no_model_output",
    "phase6-cal-014": "not_submitted",
}
UNKNOWN_RIGHTS = {
    "redistribute_metadata",
    "redistribute_derived_labels",
    "redistribute_source",
    "model_training",
}
FORBIDDEN = {"problem_statement", "hints_text", "patch", "test_patch", "eval_script"}


class RightsEvidenceError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise RightsEvidenceError(message)


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
    expect(record["status"] == "rights_partially_resolved_provider_blocked", "invalid status")
    expect(record["decision_scope"] == "project_research_policy_not_legal_advice", "invalid scope")

    cards = record["sources"]["dataset_cards"]
    expect(set(cards) == {"multilingual", "verified"}, "dataset-card mismatch")
    expect(cards["multilingual"]["revision"] == "846e647b9f33c0b51b739d005d13d85493c9af09", "multilingual revision drift")
    expect(cards["multilingual"]["declared_license"] == "MIT", "multilingual license overclaim")
    expect(cards["verified"]["revision"] == "78f471bf655a3137b2e8a75af1501690ec009ec3", "verified revision drift")
    expect(cards["verified"]["declared_license"] is None, "verified license overclaim")
    for card in cards.values():
        expect(card["url"].startswith("https://huggingface.co/datasets/SWE-bench/"), "untrusted card URL")
        expect(DIGEST.fullmatch(card["sha256"]) is not None, "malformed card digest")

    source = record["sources"]["provider"]
    expect(source["model_id"] == "opencode/big-pickle", "model drift")
    for key in ("local_catalog_sha256", "local_zen_document_sha256"):
        expect(DIGEST.fullmatch(source[key]) is not None, f"malformed provider digest: {key}")
    provider = record["provider_assessment"]
    expect(provider["open_weights"] is False, "open-weights overclaim")
    expect(provider["underlying_model_identity_disclosed"] is False, "identity overclaim")
    expect(provider["weights_revision_pinned"] is False, "weights pin overclaim")
    expect(provider["training_corpus_disclosed"] is False, "training-data overclaim")
    expect(provider["preexisting_benchmark_exposure"] == "unknown", "exposure overclaim")
    expect(provider["free_period_prompt_use"] == "may_be_used_to_improve_model", "provider data-use mismatch")
    expect(provider["further_benchmark_submission"] == "blocked", "unsafe provider admission")

    cases = record["cases"]
    expect(len(cases) == 3, "expected three cases")
    expect({case["candidate_id"] for case in cases} == set(EXPECTED), "candidate mismatch")
    for case in cases:
        candidate = case["candidate_id"]
        dataset, analysis = EXPECTED[candidate]
        expect(case["dataset_key"] == dataset, f"{candidate}: dataset mismatch")
        expect(case["rights"]["research_analysis"] == analysis, f"{candidate}: research-right mismatch")
        expect(all(case["rights"][key] == "unknown" for key in UNKNOWN_RIGHTS), f"{candidate}: downstream-right overclaim")
        expect(case["file_scope_license"] == "passed", f"{candidate}: file-scope regression")
        expect(DIGEST.fullmatch(case["upstream_license_evidence_sha256"]) is not None, f"{candidate}: bad upstream digest")
        expect(case["contamination"] == {
            "benchmark_membership": "known",
            "generator_exposure": "unknown",
            "outbound_submission": SUBMISSIONS[candidate],
            "gate": "pending",
        }, f"{candidate}: contamination overclaim")
        expect(case["disposition"] == "quarantined", f"{candidate}: premature admission")
        reasons = set(case["reason_codes"])
        expect({"artifact.incomplete", "contamination.uncertain"} <= reasons, f"{candidate}: missing blocker")
        expect(("license.unclear" in reasons) == (analysis == "unknown"), f"{candidate}: license reason mismatch")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, RightsEvidenceError) as exc:
        print(f"INVALID: {exc}")
        return 1
    allowed = sum(case["rights"]["research_analysis"] == "allowed" for case in record["cases"])
    print(f"VALID: research_analysis_allowed={allowed}; provider_submission=blocked; admitted=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
