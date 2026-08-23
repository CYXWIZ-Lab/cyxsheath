"""Create a privacy-minimized review artifact for selected Phase-6 candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from itertools import combinations
from pathlib import Path

import pyarrow.parquet as parquet


DATASET_KEYS = {
    "SWE-bench/SWE-bench_Multilingual": "multilingual",
    "SWE-bench/SWE-bench_Verified": "verified",
}
TEXT_FIELDS = ("problem_statement", "hints_text", "patch", "test_patch", "eval_script")
TOKEN = re.compile(r"[A-Za-z0-9_]+")
DIFF_PATH = re.compile(r"^diff --git a/(.+?) b/(.+?)$", re.MULTILINE)
INDEX = re.compile(r"^index ([0-9a-f]+)\.\.([0-9a-f]+)(?: .*)?$", re.MULTILINE)
SIGNALS = {
    "email": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "account_mention": re.compile(r"(?<![\w@])@[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\b"),
    "url": re.compile(r"(?i)\bhttps?://[^\s<>]+"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "generic_secret_assignment": re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\b\s*[:=]\s*['\"]?[A-Za-z0-9+/=_-]{8,}"
    ),
    "offensive_security": re.compile(
        r"(?i)\b(?:ransomware|shellcode|reverse\s+shell|credential\s+steal|weaponized|exploit\s+payload|backdoor)\b"
    ),
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_task(value: str) -> str:
    value = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    return "\n".join(line.rstrip() for line in value.split("\n")).strip()


def fivegrams(value: str) -> set[tuple[str, ...]]:
    tokens = [token.lower() for token in TOKEN.findall(normalize_task(value))]
    return {tuple(tokens[index:index + 5]) for index in range(max(0, len(tokens) - 4))}


def jaccard(left: set[tuple[str, ...]], right: set[tuple[str, ...]]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def ledger_prefix(path: Path, through: int) -> tuple[dict[str, dict], bytes]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if through < 1 or through > len(lines):
        raise ValueError(f"ledger-through must be between 1 and {len(lines)}")
    selected = lines[:through]
    latest: dict[str, dict] = {}
    for line_number, line in enumerate(selected, 1):
        if not line.strip():
            raise ValueError(f"blank ledger line {line_number}")
        event = json.loads(line)
        latest[event["candidate_id"]] = event
    return latest, ("\n".join(selected) + "\n").encode("utf-8")


def rows_by_id(path: Path) -> dict[str, dict]:
    return {row["instance_id"]: row for row in parquet.read_table(path).to_pylist()}


def changed_paths(patch: str) -> list[str]:
    paths: set[str] = set()
    for before, after in DIFF_PATH.findall(patch):
        paths.add(after if after != "/dev/null" else before)
    return sorted(paths)


def patch_fingerprint(patch: str, test_patch: str) -> dict:
    records: list[dict] = []
    complete_blob_ids = True
    for kind, value in (("solution", patch), ("tests", test_patch)):
        sections = re.split(r"(?=^diff --git )", value, flags=re.MULTILINE)
        for section in sections:
            match = DIFF_PATH.search(section)
            if match is None:
                continue
            before_path, after_path = match.groups()
            index = INDEX.search(section)
            if index is None:
                complete_blob_ids = False
                removed = "\n".join(
                    line[1:] for line in section.splitlines()
                    if line.startswith("-") and not line.startswith("---")
                )
                added = "\n".join(
                    line[1:] for line in section.splitlines()
                    if line.startswith("+") and not line.startswith("+++")
                )
                before_id = "diff-side-sha256:" + sha256_text(removed)
                after_id = "diff-side-sha256:" + sha256_text(added)
            else:
                before_id, after_id = index.groups()
            records.append({
                "kind": kind,
                "path": after_path if after_path != "/dev/null" else before_path,
                "before_id": before_id,
                "after_id": after_id,
            })
    records.sort(key=lambda item: (item["path"], item["kind"]))
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"))
    return {
        "sha256": sha256_text(canonical),
        "complete_git_blob_ids": complete_blob_ids,
        "entry_count": len(records),
    }


def signal_counts(row: dict) -> dict[str, int]:
    combined = "\n".join(str(row.get(field) or "") for field in TEXT_FIELDS)
    return {name: len(pattern.findall(combined)) for name, pattern in SIGNALS.items()}


def build_record(
    ledger: Path,
    multilingual: Path,
    verified: Path,
    script: Path,
    decisions_path: Path,
    candidate_ids: list[str],
    recorded_at: str,
    ledger_through: int,
) -> dict:
    events, ledger_payload = ledger_prefix(ledger, ledger_through)
    ledger_event_count = ledger_through
    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
    if decisions.get("schema_version") != "1.0.0":
        raise ValueError("unsupported manual decision schema")
    manual_by_candidate = decisions.get("cases")
    if not isinstance(manual_by_candidate, dict):
        raise ValueError("manual decisions must contain a cases object")
    sources = {
        "multilingual": rows_by_id(multilingual),
        "verified": rows_by_id(verified),
    }
    inventory: dict[str, tuple[dict, dict]] = {}
    for candidate_id, event in events.items():
        dataset_key = DATASET_KEYS[event["benchmark"]["dataset_id"]]
        instance_id = event["benchmark"]["instance_id"]
        row = sources[dataset_key].get(instance_id)
        if row is None:
            raise ValueError(f"missing pinned row: {instance_id}")
        inventory[candidate_id] = (event, row)

    normalized_digests: dict[str, str] = {}
    patch_digests: dict[str, str] = {}
    grams: dict[str, set[tuple[str, ...]]] = {}
    for candidate_id, (_, row) in inventory.items():
        task = str(row.get("problem_statement") or "")
        normalized_digests[candidate_id] = sha256_text(normalize_task(task))
        patch_digests[candidate_id] = sha256_text(str(row.get("patch") or ""))
        grams[candidate_id] = fivegrams(task)

    similarities: dict[tuple[str, str], float] = {}
    for left, right in combinations(sorted(inventory), 2):
        similarities[(left, right)] = jaccard(grams[left], grams[right])

    cases: list[dict] = []
    for candidate_id in candidate_ids:
        event, row = inventory[candidate_id]
        task = str(row.get("problem_statement") or "")
        patch = str(row.get("patch") or "")
        test_patch = str(row.get("test_patch") or "")
        eval_script = str(row.get("eval_script") or "")
        matches: list[dict] = []
        maximum = 0.0
        for other_id in sorted(inventory):
            if other_id == candidate_id:
                continue
            pair = tuple(sorted((candidate_id, other_id)))
            score = similarities[pair]
            maximum = max(maximum, score)
            if score >= 0.85:
                matches.append({"candidate_id": other_id, "task_fivegram_jaccard": round(score, 6)})
        exact_tasks = sorted(
            other_id for other_id, digest in normalized_digests.items()
            if other_id != candidate_id and digest == normalized_digests[candidate_id]
        )
        exact_patches = sorted(
            other_id for other_id, digest in patch_digests.items()
            if other_id != candidate_id and digest == patch_digests[candidate_id]
        )
        signals = signal_counts(row)
        secret_total = sum(signals[name] for name in (
            "private_key", "aws_access_key", "github_token", "generic_secret_assignment"
        ))
        paths = changed_paths(patch + "\n" + test_patch)
        manual = manual_by_candidate.get(candidate_id)
        if not isinstance(manual, dict):
            raise ValueError(f"missing manual decision: {candidate_id}")
        if secret_total != 0 or signals["offensive_security"] != 0:
            raise ValueError(f"{candidate_id}: manual pass conflicts with automated signal")
        if exact_tasks or exact_patches or matches:
            raise ValueError(f"{candidate_id}: manual lineage pass conflicts with match")
        cases.append({
            "candidate_id": candidate_id,
            "instance_id": event["benchmark"]["instance_id"],
            "repository_family": event["source"]["repository_family"],
            "language": event["source"]["language"],
            "artifacts": {
                "task_sha256": sha256_text(task),
                "normalized_task_sha256": normalized_digests[candidate_id],
                "patch_sha256": sha256_text(patch),
                "test_patch_sha256": sha256_text(test_patch),
                "eval_script_sha256": sha256_text(eval_script),
                "changed_paths": paths,
                "patch_fingerprint": patch_fingerprint(patch, test_patch),
                "source_snapshot_digest": None,
                "generator_proposal_present": False,
                "artifact_gate": "pending",
            },
            "automated_scan": {
                "fields_scanned": list(TEXT_FIELDS),
                "raw_text_retained": False,
                "signal_counts": signals,
                "secret_signal_total": secret_total,
            },
            "lineage": {
                "inventory_size": len(inventory),
                "normalization": "UTF-8 NFC; LF; trailing spaces removed; outer whitespace trimmed",
                "task_similarity": "lowercase alphanumeric/underscore token five-gram Jaccard",
                "near_duplicate_threshold": 0.85,
                "exact_normalized_task_matches": exact_tasks,
                "exact_patch_matches": exact_patches,
                "near_task_matches": matches,
                "maximum_other_task_jaccard": round(maximum, 6),
                "automated_gate": "passed" if not exact_tasks and not exact_patches and not matches else "pending",
            },
            "review_boundaries": {
                "benchmark_membership": "known",
                "generator_exposure": "unknown",
                "contamination_gate": "pending",
                "upstream_spdx_expression": event["license"]["spdx_expression"],
                "upstream_license_evidence_uri": event["license"]["evidence_uri"],
                "upstream_license_evidence_sha256": event["license"]["evidence_sha256"],
                "benchmark_dataset_license": event["benchmark"]["dataset_license"],
                "research_analysis": "unknown",
            },
            "manual_review": manual,
        })

    return {
        "schema_version": "1.0.0",
        "recorded_at": recorded_at,
        "status": "non_replay_review_complete_admission_blocked",
        "privacy_policy": "No task text, hints, patches, test bodies, scripts, or matched substrings are retained.",
        "inputs": {
            "candidate_ledger_pre_review_event_count": ledger_event_count,
            "candidate_ledger_pre_review_sha256": hashlib.sha256(ledger_payload).hexdigest(),
            "multilingual_parquet_sha256": sha256_file(multilingual),
            "verified_parquet_sha256": sha256_file(verified),
            "review_script": "../review_candidate_artifacts.py",
            "review_script_sha256": sha256_file(script),
            "manual_decisions": "phase6_non_replay_decisions.json",
            "manual_decisions_sha256": sha256_file(decisions_path),
        },
        "scope": {"inventory_candidates": len(inventory), "reviewed_candidates": len(cases)},
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--multilingual", type=Path, required=True)
    parser.add_argument("--verified", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--candidate", action="append", required=True)
    parser.add_argument("--recorded-at", required=True)
    parser.add_argument("--ledger-through", type=int, required=True)
    args = parser.parse_args()
    record = build_record(
        args.ledger,
        args.multilingual,
        args.verified,
        Path(__file__),
        args.decisions,
        args.candidate,
        args.recorded_at,
        args.ledger_through,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(f"REVIEWED: {len(record['cases'])} selected of {record['scope']['inventory_candidates']}; sha256={sha256_text(payload)}")
    for case in record["cases"]:
        print(
            f"{case['candidate_id']} {case['instance_id']}: "
            f"signals={case['automated_scan']['signal_counts']}; "
            f"max_jaccard={case['lineage']['maximum_other_task_jaccard']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
