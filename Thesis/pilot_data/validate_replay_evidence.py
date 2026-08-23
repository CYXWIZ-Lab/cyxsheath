"""Validate the content-addressed Phase-6 vertical replay evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^(sha256:)?[0-9a-f]{64}$")


class ReplayEvidenceError(ValueError):
    pass


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayEvidenceError(message)


def _resolve(evidence_path: Path, relative: str) -> Path:
    path = (evidence_path.parent / relative).resolve()
    _expect(path.is_file(), f"missing evidence file: {relative}")
    return path


def _validate_case(case: dict, evidence_path: Path) -> None:
    instance_id = case["instance_id"]
    baseline = case["baseline"]
    gold = case["gold"]
    image = case["image"]
    _expect(case["replay_gate"] == "passed", f"{instance_id}: replay gate not passed")
    _expect(case["disposition"] == "quarantined", f"{instance_id}: premature admission")
    _expect(DIGEST.fullmatch(image["index_digest"]) is not None, f"{instance_id}: bad index digest")
    _expect(
        DIGEST.fullmatch(image["linux_amd64_digest"]) is not None,
        f"{instance_id}: bad platform digest",
    )
    _expect(image["local_size_bytes"] > 0, f"{instance_id}: invalid image size")

    _expect(baseline["resolved"] is False, f"{instance_id}: baseline unexpectedly resolved")
    _expect(baseline["patch_applied"] is True, f"{instance_id}: baseline patch not applied")
    _expect(
        baseline["infrastructure_failure"] is False,
        f"{instance_id}: baseline infrastructure failure",
    )
    _expect(baseline["fail_to_pass_failed"] > 0, f"{instance_id}: baseline has no failing oracle")
    _expect(gold["resolved"] is True, f"{instance_id}: gold did not resolve")
    _expect(gold["patch_applied"] is True, f"{instance_id}: gold patch not applied")
    _expect(gold["infrastructure_failure"] is False, f"{instance_id}: gold infrastructure failure")
    _expect(
        gold["fail_to_pass_succeeded"] == baseline["fail_to_pass_failed"],
        f"{instance_id}: fail-to-pass count mismatch",
    )
    _expect(
        gold["pass_to_pass_succeeded"] == baseline["pass_to_pass_succeeded"],
        f"{instance_id}: pass-to-pass count mismatch",
    )

    for phase, record in (("baseline", baseline), ("gold", gold)):
        report_path = _resolve(evidence_path, record["report_path"])
        _expect(
            file_sha256(report_path) == record["report_sha256"],
            f"{instance_id}: {phase} report digest mismatch",
        )
        output_path = report_path.with_name("test_output.txt")
        _expect(output_path.is_file(), f"{instance_id}: missing {phase} test output")
        _expect(
            file_sha256(output_path) == record["test_output_sha256"],
            f"{instance_id}: {phase} output digest mismatch",
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))[instance_id]
        _expect(report["patch_successfully_applied"] is True, f"{instance_id}: report patch failure")
        _expect(report["infra_failure"] is False, f"{instance_id}: report infrastructure failure")
        _expect(report["resolved"] is record["resolved"], f"{instance_id}: report outcome mismatch")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    _expect(record["schema_version"] == "1.0.0", "unsupported evidence schema")
    _expect(record["status"] == "replay_passed_admission_pending", "invalid evidence status")
    _expect(record["admission"]["admitted_count"] == 0, "evidence claims admission")
    _expect(len(record["cases"]) == 3, "vertical slice must contain three cases")
    _expect(
        {case["language"] for case in record["cases"]} == {"C", "C++", "Python"},
        "vertical slice language mismatch",
    )
    for key, digest_key in (
        ("requirements_lock", "requirements_lock_sha256"),
        ("compatibility_patch", "compatibility_patch_sha256"),
    ):
        target = _resolve(path, record["harness"][key])
        _expect(file_sha256(target) == record["harness"][digest_key], f"{key} digest mismatch")
    materializer = _resolve(path, record["materialization"]["script"])
    _expect(
        file_sha256(materializer) == record["materialization"]["script_sha256"],
        "materializer digest mismatch",
    )
    for case in record["cases"]:
        _validate_case(case, path)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, ReplayEvidenceError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(
        f"VALID: {len(record['cases'])} replay pairs; languages="
        f"{sorted(case['language'] for case in record['cases'])}; admitted=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
