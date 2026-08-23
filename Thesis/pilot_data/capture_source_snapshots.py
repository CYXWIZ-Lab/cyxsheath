"""Capture content identities for pinned source revisions inside replay images."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ledger_prefix(path: Path, through: int) -> tuple[dict[str, dict], str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if through < 1 or through > len(lines):
        raise ValueError(f"ledger-through must be between 1 and {len(lines)}")
    chosen = lines[:through]
    latest: dict[str, dict] = {}
    for number, line in enumerate(chosen, 1):
        if not line.strip():
            raise ValueError(f"blank ledger line {number}")
        event = json.loads(line)
        latest[event["candidate_id"]] = event
    payload = ("\n".join(chosen) + "\n").encode("utf-8")
    return latest, hashlib.sha256(payload).hexdigest()


def probe(docker: str, image: str, revision: str) -> dict:
    script = "\n".join((
        "set -eu",
        "cd /testbed",
        "git --version",
        "git rev-parse HEAD",
        f"git cat-file -t '{revision}'",
        f"git rev-parse '{revision}^{{tree}}'",
        f"git archive --format=tar '{revision}' | sha256sum",
    ))
    result = subprocess.run(
        (
            docker,
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "/bin/sh",
            image,
            "-c",
            script,
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
        timeout=300,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"source snapshot probe failed: {detail[:500]}")
    lines = result.stdout.decode("utf-8").splitlines()
    if len(lines) != 5:
        raise RuntimeError(f"source snapshot probe returned {len(lines)} lines")
    version, head, object_type, tree, archive_line = lines
    archive = archive_line.split(maxsplit=1)[0]
    if not version.startswith("git version "):
        raise RuntimeError("source snapshot probe returned an invalid Git version")
    if SHA1.fullmatch(head) is None or SHA1.fullmatch(tree) is None:
        raise RuntimeError("source snapshot probe returned an invalid Git identity")
    if object_type != "commit" or SHA256.fullmatch(archive) is None:
        raise RuntimeError("source snapshot probe did not resolve a commit archive")
    return {
        "git_version": version.removeprefix("git version "),
        "container_head": head,
        "head_matches_base_revision": head == revision,
        "base_object_type": object_type,
        "base_tree_sha1": tree,
        "source_archive_sha256": archive,
        "snapshot_gate": "passed",
    }


def build(
    ledger: Path,
    through: int,
    replay_path: Path,
    candidates: list[str],
    docker: str,
    recorded_at: str,
) -> dict:
    events, ledger_digest = ledger_prefix(ledger, through)
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    replay_by_candidate = {case["candidate_id"]: case for case in replay["cases"]}
    cases: list[dict] = []
    for candidate in candidates:
        event = events.get(candidate)
        replay_case = replay_by_candidate.get(candidate)
        if event is None or replay_case is None:
            raise ValueError(f"candidate is absent from an input: {candidate}")
        if event["benchmark"]["instance_id"] != replay_case["instance_id"]:
            raise ValueError(f"instance mismatch: {candidate}")
        result = probe(
            docker,
            replay_case["image"]["reference"],
            event["source"]["base_revision"],
        )
        cases.append({
            "candidate_id": candidate,
            "instance_id": replay_case["instance_id"],
            "language": event["source"]["language"],
            "repository": event["source"]["repository"],
            "base_revision": event["source"]["base_revision"],
            "image_reference": replay_case["image"]["reference"],
            "image_linux_amd64_digest": replay_case["image"]["linux_amd64_digest"],
            **result,
        })
    return {
        "schema_version": "1.0.0",
        "recorded_at": recorded_at,
        "status": "source_snapshots_content_addressed_proposals_pending",
        "method": {
            "workspace": "/testbed",
            "network": "none",
            "archive_command": "git archive --format=tar <base_revision>",
            "digest": "SHA-256 over exact tar bytes emitted by the pinned image",
            "raw_source_retained": False,
        },
        "inputs": {
            "candidate_ledger": "../candidate_events.jsonl",
            "candidate_ledger_through": through,
            "candidate_ledger_prefix_sha256": ledger_digest,
            "replay_evidence": "../replay_evidence/phase6_vertical_slice.json",
            "replay_evidence_sha256": sha256_file(replay_path),
        },
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--ledger-through", type=int, required=True)
    parser.add_argument("--replay-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", action="append", required=True)
    parser.add_argument("--recorded-at", required=True)
    parser.add_argument("--docker")
    args = parser.parse_args()
    docker = args.docker or shutil.which("docker")
    if docker is None:
        raise SystemExit("Docker is required")
    record = build(
        args.ledger,
        args.ledger_through,
        args.replay_evidence,
        args.candidate,
        str(Path(docker).resolve()),
        args.recorded_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(
        f"CAPTURED: {len(record['cases'])} source snapshots; "
        f"sha256={hashlib.sha256(payload.encode('utf-8')).hexdigest()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
