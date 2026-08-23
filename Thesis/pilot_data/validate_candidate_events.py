"""Validate the append-only Phase-6 candidate event ledger."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


SCHEMA_VERSION = "1.0.0"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
DISPOSITIONS = {"admitted", "quarantined", "rejected"}
QUARANTINE_CODES = {
    "license.unclear",
    "privacy.review_required",
    "replay.transient",
    "label.conflict",
    "lineage.uncertain",
    "contamination.uncertain",
    "artifact.incomplete",
}
REJECT_CODES = {
    "license.denied",
    "privacy.personal_data",
    "secret.detected",
    "safety.offensive",
    "provenance.missing",
    "revision.unpinned",
    "snapshot.unreplayable",
    "evidence.missing",
    "lineage.duplicate",
    "scope.unsupported",
    "artifact.malformed",
}
RIGHTS = {
    "research_analysis",
    "redistribute_metadata",
    "redistribute_derived_labels",
    "redistribute_source",
    "model_training",
}
REVIEWS = {"privacy", "secrets", "safety", "lineage", "contamination"}


class LedgerError(ValueError):
    pass


def _expect_keys(value: object, keys: set[str], where: str) -> dict:
    if not isinstance(value, dict):
        raise LedgerError(f"{where}: expected object")
    actual = set(value)
    if actual != keys:
        raise LedgerError(
            f"{where}: keys differ; missing={sorted(keys - actual)}, "
            f"extra={sorted(actual - keys)}"
        )
    return value


def _https(value: object, where: str) -> None:
    parsed = urlparse(value) if isinstance(value, str) else None
    if parsed is None or parsed.scheme != "https" or not parsed.netloc:
        raise LedgerError(f"{where}: expected absolute HTTPS URI")


def _timestamp(value: object, where: str) -> None:
    if not isinstance(value, str):
        raise LedgerError(f"{where}: expected timestamp string")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LedgerError(f"{where}: invalid timestamp") from exc


def _digest(value: object, pattern: re.Pattern[str], where: str) -> None:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise LedgerError(f"{where}: malformed digest")


def _validate_event(event: object, line: int) -> dict:
    prefix = f"line {line}"
    event = _expect_keys(
        event,
        {
            "schema_version",
            "sequence",
            "event_id",
            "recorded_at",
            "candidate_id",
            "action",
            "supersedes_event_id",
            "disposition",
            "reason_codes",
            "benchmark",
            "source",
            "license",
            "replay",
            "reviews",
        },
        prefix,
    )
    if event["schema_version"] != SCHEMA_VERSION:
        raise LedgerError(f"{prefix}: unsupported schema_version")
    if not isinstance(event["sequence"], int) or event["sequence"] < 1:
        raise LedgerError(f"{prefix}: sequence must be a positive integer")
    for key in ("event_id", "candidate_id"):
        if not isinstance(event[key], str) or not event[key]:
            raise LedgerError(f"{prefix}.{key}: expected non-empty string")
    if event["action"] not in {"registered", "reviewed"}:
        raise LedgerError(f"{prefix}: unsupported action")
    if event["action"] == "registered" and event["supersedes_event_id"] is not None:
        raise LedgerError(f"{prefix}: registration cannot supersede an event")
    if event["action"] == "reviewed" and not isinstance(
        event["supersedes_event_id"], str
    ):
        raise LedgerError(f"{prefix}: review must name the superseded event")
    _timestamp(event["recorded_at"], f"{prefix}.recorded_at")

    disposition = event["disposition"]
    reasons = event["reason_codes"]
    if disposition not in DISPOSITIONS:
        raise LedgerError(f"{prefix}: unsupported disposition")
    if not isinstance(reasons, list) or len(reasons) != len(set(reasons)):
        raise LedgerError(f"{prefix}: reason_codes must be a duplicate-free list")
    allowed_reasons = (
        set() if disposition == "admitted" else
        QUARANTINE_CODES if disposition == "quarantined" else REJECT_CODES
    )
    if any(reason not in allowed_reasons for reason in reasons):
        raise LedgerError(f"{prefix}: reason does not match disposition")
    if disposition != "admitted" and not reasons:
        raise LedgerError(f"{prefix}: non-admitted event needs a reason")

    benchmark = _expect_keys(
        event["benchmark"],
        {"dataset_id", "dataset_revision", "dataset_license", "split", "instance_id"},
        f"{prefix}.benchmark",
    )
    for key in ("dataset_id", "dataset_license", "split", "instance_id"):
        if not isinstance(benchmark[key], str) or not benchmark[key]:
            raise LedgerError(f"{prefix}.benchmark.{key}: expected string")
    _digest(benchmark["dataset_revision"], GIT_SHA, f"{prefix}.benchmark.dataset_revision")

    source = _expect_keys(
        event["source"],
        {
            "repository",
            "repository_family",
            "language",
            "base_revision",
            "source_date",
            "pull_request_uri",
            "environment_setup_revision",
        },
        f"{prefix}.source",
    )
    if source["language"] not in {"C", "C++", "Python"}:
        raise LedgerError(f"{prefix}.source.language: unsupported language")
    for key in ("repository", "repository_family"):
        if not isinstance(source[key], str) or not source[key]:
            raise LedgerError(f"{prefix}.source.{key}: expected string")
    _digest(source["base_revision"], GIT_SHA, f"{prefix}.source.base_revision")
    _timestamp(source["source_date"], f"{prefix}.source.source_date")
    _https(source["pull_request_uri"], f"{prefix}.source.pull_request_uri")
    setup_revision = source["environment_setup_revision"]
    if setup_revision is not None:
        _digest(setup_revision, GIT_SHA, f"{prefix}.source.environment_setup_revision")

    license_record = _expect_keys(
        event["license"],
        {
            "spdx_expression",
            "spdx_list_version",
            "evidence_uri",
            "evidence_sha256",
            "file_scope_review",
            "rights",
        },
        f"{prefix}.license",
    )
    if license_record["spdx_expression"] is not None and not isinstance(
        license_record["spdx_expression"], str
    ):
        raise LedgerError(f"{prefix}.license.spdx_expression: expected string or null")
    if not isinstance(license_record["spdx_list_version"], str):
        raise LedgerError(f"{prefix}.license.spdx_list_version: expected string")
    _https(license_record["evidence_uri"], f"{prefix}.license.evidence_uri")
    _digest(license_record["evidence_sha256"], SHA256, f"{prefix}.license.evidence_sha256")
    if license_record["file_scope_review"] not in {"pending", "passed", "failed"}:
        raise LedgerError(f"{prefix}.license.file_scope_review: unsupported state")
    rights = _expect_keys(license_record["rights"], RIGHTS, f"{prefix}.license.rights")
    if any(value not in {"allowed", "prohibited", "unknown"} for value in rights.values()):
        raise LedgerError(f"{prefix}.license.rights: unsupported decision")

    replay = _expect_keys(
        event["replay"], {"status", "image_reference", "image_digest"}, f"{prefix}.replay"
    )
    if replay["status"] not in {"not_attempted", "passed", "failed"}:
        raise LedgerError(f"{prefix}.replay.status: unsupported state")
    if not isinstance(replay["image_reference"], str) or not replay["image_reference"]:
        raise LedgerError(f"{prefix}.replay.image_reference: expected string")
    if replay["image_digest"] is not None:
        _digest(replay["image_digest"], SHA256, f"{prefix}.replay.image_digest")

    reviews = _expect_keys(event["reviews"], REVIEWS, f"{prefix}.reviews")
    if any(value not in {"pending", "passed", "failed"} for value in reviews.values()):
        raise LedgerError(f"{prefix}.reviews: unsupported state")

    if disposition == "admitted":
        if rights["research_analysis"] != "allowed":
            raise LedgerError(f"{prefix}: admission requires research_analysis=allowed")
        if license_record["file_scope_review"] != "passed":
            raise LedgerError(f"{prefix}: admission requires passed license review")
        if replay["status"] != "passed" or replay["image_digest"] is None:
            raise LedgerError(f"{prefix}: admission requires digest-pinned replay")
        if any(value != "passed" for value in reviews.values()):
            raise LedgerError(f"{prefix}: admission requires all reviews to pass")
    return event


def load_and_validate(path: Path) -> list[dict]:
    events: list[dict] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            raise LedgerError(f"line {line_number}: blank lines are not allowed")
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise LedgerError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
        events.append(_validate_event(event, line_number))
    if not events:
        raise LedgerError("ledger is empty")

    event_ids: set[str] = set()
    latest_by_candidate: dict[str, dict] = {}
    for expected_sequence, event in enumerate(events, 1):
        if event["sequence"] != expected_sequence:
            raise LedgerError(
                f"line {expected_sequence}: expected sequence {expected_sequence}, "
                f"got {event['sequence']}"
            )
        if event["event_id"] in event_ids:
            raise LedgerError(f"duplicate event_id: {event['event_id']}")
        event_ids.add(event["event_id"])
        previous = latest_by_candidate.get(event["candidate_id"])
        if event["action"] == "registered":
            if previous is not None:
                raise LedgerError(f"duplicate registration: {event['candidate_id']}")
        else:
            if previous is None:
                raise LedgerError(f"review before registration: {event['candidate_id']}")
            if event["supersedes_event_id"] != previous["event_id"]:
                raise LedgerError(f"non-latest supersession: {event['candidate_id']}")
        latest_by_candidate[event["candidate_id"]] = event
    return events


def current_events(events: list[dict]) -> list[dict]:
    latest: dict[str, dict] = {}
    for event in events:
        latest[event["candidate_id"]] = event
    return list(latest.values())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--expect-count", type=int)
    parser.add_argument("--expect-language", action="append", default=[], metavar="NAME=N")
    args = parser.parse_args()
    try:
        events = load_and_validate(args.ledger)
        current = current_events(events)
        if args.expect_count is not None and len(current) != args.expect_count:
            raise LedgerError(f"expected {args.expect_count} candidates, got {len(current)}")
        languages = Counter(event["source"]["language"] for event in current)
        for requirement in args.expect_language:
            name, separator, raw_count = requirement.rpartition("=")
            if not separator or not name:
                raise LedgerError(f"invalid language requirement: {requirement}")
            if languages[name] != int(raw_count):
                raise LedgerError(f"expected {name}={raw_count}, got {languages[name]}")
    except (LedgerError, OSError, ValueError) as exc:
        print(f"INVALID: {exc}")
        return 1

    dispositions = Counter(event["disposition"] for event in current)
    repositories = {event["source"]["repository_family"] for event in current}
    print(
        f"VALID: {len(events)} events; {len(current)} candidates; "
        f"languages={dict(sorted(languages.items()))}; "
        f"dispositions={dict(sorted(dispositions.items()))}; "
        f"repository_families={len(repositories)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
