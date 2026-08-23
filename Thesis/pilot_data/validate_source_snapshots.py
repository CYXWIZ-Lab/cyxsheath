"""Validate content-addressed source-snapshot evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^(sha256:)?[0-9a-f]{64}$")
EXPECTED = {"phase6-cal-001", "phase6-cal-008", "phase6-cal-014"}


class SourceSnapshotError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise SourceSnapshotError(message)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(path: Path, relative: str) -> Path:
    target = (path.parent / relative).resolve()
    expect(target.is_file(), f"missing referenced file: {relative}")
    return target


def ledger_prefix_sha256(path: Path, through: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    expect(0 < through <= len(lines), "invalid ledger boundary")
    return hashlib.sha256(("\n".join(lines[:through]) + "\n").encode("utf-8")).hexdigest()


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(record["status"] == "source_snapshots_content_addressed_proposals_pending", "invalid status")
    method = record["method"]
    expect(method["workspace"] == "/testbed", "wrong workspace")
    expect(method["network"] == "none", "network was not disabled")
    expect(method["raw_source_retained"] is False, "raw source retained")

    inputs = record["inputs"]
    ledger = resolve(path, inputs["candidate_ledger"])
    replay_path = resolve(path, inputs["replay_evidence"])
    expect(
        ledger_prefix_sha256(ledger, inputs["candidate_ledger_through"])
        == inputs["candidate_ledger_prefix_sha256"],
        "ledger prefix digest mismatch",
    )
    expect(sha256_file(replay_path) == inputs["replay_evidence_sha256"], "replay digest mismatch")
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    replay_by_candidate = {case["candidate_id"]: case for case in replay["cases"]}

    cases = record["cases"]
    expect(len(cases) == 3, "expected three source snapshots")
    expect({case["candidate_id"] for case in cases} == EXPECTED, "candidate mismatch")
    expect({case["language"] for case in cases} == {"C", "C++", "Python"}, "language mismatch")
    archives: set[str] = set()
    for case in cases:
        candidate = case["candidate_id"]
        replay_case = replay_by_candidate[candidate]
        expect(case["instance_id"] == replay_case["instance_id"], f"{candidate}: instance mismatch")
        expect(case["image_reference"] == replay_case["image"]["reference"], f"{candidate}: image mismatch")
        expect(case["image_linux_amd64_digest"] == replay_case["image"]["linux_amd64_digest"], f"{candidate}: image digest mismatch")
        expect(SHA1.fullmatch(case["base_revision"]) is not None, f"{candidate}: bad revision")
        expect(SHA1.fullmatch(case["container_head"]) is not None, f"{candidate}: bad container head")
        expect(SHA1.fullmatch(case["base_tree_sha1"]) is not None, f"{candidate}: bad tree")
        expect(SHA256.fullmatch(case["source_archive_sha256"]) is not None, f"{candidate}: bad archive digest")
        expect(case["base_object_type"] == "commit", f"{candidate}: base is not a commit")
        expect(case["snapshot_gate"] == "passed", f"{candidate}: snapshot gate not passed")
        archives.add(case["source_archive_sha256"])
    expect(len(archives) == 3, "source archive digest collision")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, SourceSnapshotError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(f"VALID: {len(record['cases'])} content-addressed source snapshots; proposals=pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
