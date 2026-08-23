"""Extract a bounded replay slice from pinned SWE-bench parquet shards."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as parquet


PARQUET_BY_DATASET = {
    "SWE-bench/SWE-bench_Multilingual": "multilingual",
    "SWE-bench/SWE-bench_Verified": "verified",
}
REQUIRED_ROW_FIELDS = {
    "instance_id",
    "repo",
    "base_commit",
    "patch",
    "test_patch",
    "eval_script",
    "image",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
}


def latest_events(ledger: Path) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for line_number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank ledger line {line_number}")
        event = json.loads(line)
        latest[event["candidate_id"]] = event
    return latest


def rows_by_id(path: Path) -> dict[str, dict]:
    rows = parquet.read_table(path).to_pylist()
    return {row["instance_id"]: row for row in rows}


def materialize(
    ledger: Path,
    multilingual: Path,
    verified: Path,
    output: Path,
    candidate_ids: list[str],
) -> str:
    events = latest_events(ledger)
    sources = {
        "multilingual": rows_by_id(multilingual),
        "verified": rows_by_id(verified),
    }
    selected: list[dict] = []
    seen_instances: set[str] = set()
    for candidate_id in candidate_ids:
        if candidate_id not in events:
            raise ValueError(f"unknown candidate: {candidate_id}")
        event = events[candidate_id]
        dataset_id = event["benchmark"]["dataset_id"]
        source_name = PARQUET_BY_DATASET.get(dataset_id)
        if source_name is None:
            raise ValueError(f"unsupported dataset: {dataset_id}")
        instance_id = event["benchmark"]["instance_id"]
        row = sources[source_name].get(instance_id)
        if row is None:
            raise ValueError(f"missing pinned row: {instance_id}")
        if instance_id in seen_instances:
            raise ValueError(f"duplicate instance selection: {instance_id}")
        if row["repo"] != event["source"]["repository"]:
            raise ValueError(f"repository mismatch: {instance_id}")
        if row["base_commit"] != event["source"]["base_revision"]:
            raise ValueError(f"base revision mismatch: {instance_id}")
        missing = REQUIRED_ROW_FIELDS - set(row)
        if missing:
            raise ValueError(f"{instance_id}: missing fields {sorted(missing)}")
        for field in ("patch", "test_patch", "eval_script", "image", "FAIL_TO_PASS"):
            if not row[field]:
                raise ValueError(f"{instance_id}: empty {field}")
        selected.append(row)
        seen_instances.add(instance_id)

    payload = json.dumps(selected, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload + "\n", encoding="utf-8", newline="\n")
    return hashlib.sha256((payload + "\n").encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--multilingual", type=Path, required=True)
    parser.add_argument("--verified", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", action="append", required=True)
    args = parser.parse_args()
    digest = materialize(
        args.ledger,
        args.multilingual,
        args.verified,
        args.output,
        args.candidate,
    )
    print(f"MATERIALIZED: {len(args.candidate)} rows; sha256={digest}; path={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
