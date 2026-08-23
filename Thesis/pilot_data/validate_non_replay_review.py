"""Validate the privacy-minimized Phase-6 non-replay review evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath


DIGEST = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_CANDIDATES = {"phase6-cal-001", "phase6-cal-008", "phase6-cal-014"}
EXPECTED_LANGUAGES = {"C", "C++", "Python"}
EXPECTED_REASONS = {"artifact.incomplete", "contamination.uncertain", "license.unclear"}
FORBIDDEN_KEYS = {"problem_statement", "hints_text", "patch", "test_patch", "eval_script", "matched_text"}
SECRET_SIGNALS = {"private_key", "aws_access_key", "github_token", "generic_secret_assignment"}


class ReviewEvidenceError(ValueError):
    pass


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewEvidenceError(message)


def resolve(path: Path, relative: str) -> Path:
    target = (path.parent / relative).resolve()
    expect(target.is_file(), f"missing referenced file: {relative}")
    return target


def check_no_raw_keys(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        forbidden = FORBIDDEN_KEYS & set(value)
        expect(not forbidden, f"{where}: forbidden raw-content keys {sorted(forbidden)}")
        for key, child in value.items():
            check_no_raw_keys(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_no_raw_keys(child, f"{where}[{index}]")


def validate_case(case: dict, manual_decisions: dict) -> None:
    candidate_id = case["candidate_id"]
    artifacts = case["artifacts"]
    scan = case["automated_scan"]
    lineage = case["lineage"]
    boundaries = case["review_boundaries"]
    manual = case["manual_review"]

    expect(candidate_id in EXPECTED_CANDIDATES, f"unexpected candidate: {candidate_id}")
    expect(manual == manual_decisions[candidate_id], f"{candidate_id}: manual decision mismatch")
    for key in ("task_sha256", "normalized_task_sha256", "patch_sha256", "test_patch_sha256", "eval_script_sha256"):
        expect(DIGEST.fullmatch(artifacts[key]) is not None, f"{candidate_id}: malformed {key}")
    paths = artifacts["changed_paths"]
    expect(paths and paths == sorted(set(paths)), f"{candidate_id}: changed paths not canonical")
    for raw_path in paths:
        path = PurePosixPath(raw_path)
        expect(not path.is_absolute() and ".." not in path.parts, f"{candidate_id}: unsafe changed path")
    fingerprint = artifacts["patch_fingerprint"]
    expect(DIGEST.fullmatch(fingerprint["sha256"]) is not None, f"{candidate_id}: bad fingerprint")
    expect(fingerprint["entry_count"] == len(paths), f"{candidate_id}: fingerprint/path mismatch")
    expect(artifacts["source_snapshot_digest"] is None, f"{candidate_id}: unproven snapshot digest")
    expect(artifacts["generator_proposal_present"] is False, f"{candidate_id}: proposal incorrectly present")
    expect(artifacts["artifact_gate"] == "pending", f"{candidate_id}: artifact gate must remain pending")

    expect(scan["raw_text_retained"] is False, f"{candidate_id}: raw text retained")
    signals = scan["signal_counts"]
    expect(signals["email"] == 0 and signals["account_mention"] == 0, f"{candidate_id}: privacy signal")
    expect(all(signals[name] == 0 for name in SECRET_SIGNALS), f"{candidate_id}: secret signal")
    expect(scan["secret_signal_total"] == 0, f"{candidate_id}: secret total nonzero")
    expect(signals["offensive_security"] == 0, f"{candidate_id}: offensive signal")

    expect(lineage["inventory_size"] == 20, f"{candidate_id}: wrong lineage inventory")
    expect(lineage["near_duplicate_threshold"] == 0.85, f"{candidate_id}: wrong threshold")
    for key in ("exact_normalized_task_matches", "exact_patch_matches", "near_task_matches"):
        expect(lineage[key] == [], f"{candidate_id}: unresolved lineage match")
    expect(lineage["maximum_other_task_jaccard"] < 0.85, f"{candidate_id}: near duplicate")
    expect(lineage["automated_gate"] == "passed", f"{candidate_id}: lineage gate not passed")

    expect(boundaries["benchmark_membership"] == "known", f"{candidate_id}: benchmark membership")
    expect(boundaries["generator_exposure"] == "unknown", f"{candidate_id}: exposure overclaim")
    expect(boundaries["contamination_gate"] == "pending", f"{candidate_id}: contamination overclaim")
    expect(boundaries["research_analysis"] == "unknown", f"{candidate_id}: rights overclaim")
    expect(DIGEST.fullmatch(boundaries["upstream_license_evidence_sha256"]) is not None, f"{candidate_id}: bad license digest")

    for gate in ("privacy", "secrets", "safety", "lineage", "file_scope_license"):
        expect(manual[gate] == "passed", f"{candidate_id}: {gate} not passed")
    expect(manual["contamination"] == "pending", f"{candidate_id}: contamination overclaim")
    expect(manual["research_analysis"] == "unknown", f"{candidate_id}: rights overclaim")
    expect(manual["artifact"] == "pending", f"{candidate_id}: artifact overclaim")
    expect(manual["disposition"] == "quarantined", f"{candidate_id}: premature admission")
    expect(set(manual["reason_codes"]) == EXPECTED_REASONS, f"{candidate_id}: wrong reasons")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_no_raw_keys(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(record["status"] == "non_replay_review_complete_admission_blocked", "invalid status")
    expect(record["scope"] == {"inventory_candidates": 20, "reviewed_candidates": 3}, "invalid scope")
    inputs = record["inputs"]
    expect(inputs["candidate_ledger_pre_review_event_count"] == 23, "wrong pre-review ledger size")
    for key in (
        "candidate_ledger_pre_review_sha256", "multilingual_parquet_sha256",
        "verified_parquet_sha256", "review_script_sha256", "manual_decisions_sha256",
    ):
        expect(DIGEST.fullmatch(inputs[key]) is not None, f"malformed input digest: {key}")
    for path_key, digest_key in (
        ("review_script", "review_script_sha256"),
        ("manual_decisions", "manual_decisions_sha256"),
    ):
        target = resolve(path, inputs[path_key])
        expect(file_sha256(target) == inputs[digest_key], f"{path_key} digest mismatch")
    decisions = json.loads(resolve(path, inputs["manual_decisions"]).read_text(encoding="utf-8"))
    expect(decisions["schema_version"] == "1.0.0", "unsupported decisions schema")
    expect(set(decisions["cases"]) == EXPECTED_CANDIDATES, "manual decision candidate mismatch")

    cases = record["cases"]
    expect(len(cases) == 3, "expected three reviewed cases")
    expect({case["candidate_id"] for case in cases} == EXPECTED_CANDIDATES, "candidate mismatch")
    expect({case["language"] for case in cases} == EXPECTED_LANGUAGES, "language mismatch")
    for case in cases:
        validate_case(case, decisions["cases"])
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, ReviewEvidenceError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print("VALID: 3 non-replay reviews; privacy/secrets/safety/lineage/file-scope passed; admitted=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
