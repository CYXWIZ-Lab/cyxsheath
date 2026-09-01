"""Validate the curated Phase-6 minimum-POC result without reading raw artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re


ROOT = Path(__file__).parents[2]
PROTOCOL = ROOT / "Thesis" / "Phase6_Minimum_POC_Protocol.md"
MANIFEST = Path(__file__).parent / "poc_tasks" / "manifest.json"
RUNNER = Path(__file__).parent / "run_phase6_minimum_poc.py"
SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
IMAGE = re.compile(r"python@sha256:[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
FORBIDDEN_KEYS = {
    "argv",
    "hidden_script",
    "hidden_tests",
    "patch",
    "prompt",
    "response",
    "stderr",
    "stdout",
    "tool_output",
}


class PocResultError(ValueError):
    """Raised when curated POC evidence is invalid or no longer source-bound."""


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise PocResultError(message)


def _keys(value: dict, expected: set[str], label: str) -> None:
    _expect(set(value) == expected, f"{label} fields invalid")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _walk_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_walk_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_walk_keys(item) for item in value), set())
    return set()


def validate_result(path: Path) -> dict:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    _expect(isinstance(record, dict), "result must be an object")
    _keys(
        record,
        {
            "artifact_boundary",
            "cost_class",
            "cyxcode_executable_digest",
            "cyxcode_image",
            "model",
            "pilot_id",
            "protocol_sha256",
            "recorded_at",
            "runner_commit",
            "runner_sha256",
            "runs",
            "schema_version",
            "status",
            "summary",
            "task_manifest_sha256",
            "verification_image",
        },
        "result",
    )
    _expect(not (_walk_keys(record) & FORBIDDEN_KEYS), "raw artifact field present")
    _expect(record["schema_version"] == "1.0.0", "schema version invalid")
    _expect(record["pilot_id"] == "phase6-minimum-poc-v1", "pilot ID invalid")
    _expect(record["status"] == "complete", "result is incomplete")
    _expect(record["cost_class"] == "free", "cost class invalid")
    _expect(
        record["artifact_boundary"]
        == ".replay_cache_only_for_raw_prompts_responses_patches_tool_output_and_canonical_run_records",
        "artifact boundary invalid",
    )
    _expect(record["protocol_sha256"] == _sha256(PROTOCOL), "protocol digest drift")
    _expect(record["task_manifest_sha256"] == _sha256(MANIFEST), "manifest digest drift")
    _expect(record["runner_sha256"] == _sha256(RUNNER), "runner digest drift")
    _expect(isinstance(record["runner_commit"], str) and COMMIT.fullmatch(record["runner_commit"]), "runner commit invalid")
    for name in ("cyxcode_executable_digest", "cyxcode_image"):
        _expect(isinstance(record[name], str) and SHA256.fullmatch(record[name]), f"{name} invalid")
    _expect(
        isinstance(record["verification_image"], str) and IMAGE.fullmatch(record["verification_image"]),
        "verification_image invalid",
    )

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    _expect(record["model"] == manifest["model"], "model drift")
    expected_order = [
        (task["task_id"], condition)
        for task in manifest["tasks"]
        for condition in task["condition_order"]
    ]
    runs = record["runs"]
    _expect(isinstance(runs, list) and len(runs) == 6, "run count invalid")
    _expect([(run.get("task_id"), run.get("condition")) for run in runs] == expected_order, "run order drift")
    seen_digests: set[str] = set()
    for index, run in enumerate(runs, start=1):
        _expect(isinstance(run, dict), f"run {index} invalid")
        _keys(
            run,
            {
                "attempts",
                "condition",
                "failure_reason_codes",
                "record_digest",
                "recovered_after_first_attempt",
                "status",
                "task_id",
                "verdict",
                "verified_success",
                "wall_seconds",
            },
            f"run {index}",
        )
        _expect(run["condition"] in ("A", "D0"), f"run {index} condition invalid")
        _expect(run["status"] in ("completed", "infrastructure_failure"), f"run {index} status invalid")
        _expect(type(run["verified_success"]) is bool, f"run {index} success invalid")
        _expect(type(run["recovered_after_first_attempt"]) is bool, f"run {index} recovery invalid")
        _expect(type(run["attempts"]) is int and 0 <= run["attempts"] <= (1 if run["condition"] == "A" else 2), f"run {index} attempts invalid")
        _expect(type(run["wall_seconds"]) in (int, float) and math.isfinite(run["wall_seconds"]) and run["wall_seconds"] >= 0, f"run {index} time invalid")
        digest = run["record_digest"]
        _expect(isinstance(digest, str) and SHA256.fullmatch(digest), f"run {index} digest invalid")
        _expect(digest not in seen_digests, f"run {index} digest duplicated")
        seen_digests.add(digest)
        reasons = run["failure_reason_codes"]
        _expect(isinstance(reasons, list) and all(isinstance(item, str) and item for item in reasons), f"run {index} reasons invalid")
        if run["status"] == "infrastructure_failure":
            _expect(run["verdict"] == "failed" and not run["verified_success"] and bool(reasons), f"run {index} failure inconsistent")
        else:
            _expect(run["verdict"] in ("accept", "revise") and not reasons, f"run {index} completion inconsistent")
        expected_recovery = run["condition"] == "D0" and run["attempts"] == 2 and run["verified_success"]
        _expect(run["recovered_after_first_attempt"] == expected_recovery, f"run {index} recovery inconsistent")

    summary = record["summary"]
    _keys(
        summary,
        {
            "A_verified_success",
            "D0_recoveries",
            "D0_verified_success",
            "inferential_claim_authorized",
            "infrastructure_failures",
            "run_count",
            "task_count",
        },
        "summary",
    )
    expected_summary = {
        "task_count": 3,
        "run_count": 6,
        "A_verified_success": sum(run["verified_success"] for run in runs if run["condition"] == "A"),
        "D0_verified_success": sum(run["verified_success"] for run in runs if run["condition"] == "D0"),
        "D0_recoveries": sum(run["recovered_after_first_attempt"] for run in runs if run["condition"] == "D0"),
        "infrastructure_failures": sum(run["status"] == "infrastructure_failure" for run in runs),
        "inferential_claim_authorized": False,
    }
    _expect(summary == expected_summary, "summary mismatch")
    _expect(summary["infrastructure_failures"] == 5, "v1 infrastructure count drift")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    record = validate_result(args.path)
    print(json.dumps(record["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
