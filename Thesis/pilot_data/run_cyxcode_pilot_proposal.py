"""Capture one genuine CyxCode proposal for a pinned Phase-6 candidate."""

from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sheath" / "src"))

from sheath import (  # noqa: E402
    ArtifactStore,
    CyxCodeGenerator,
    DockerCliBackend,
    DockerPatchExtractor,
    DockerSandboxConfig,
    GenerationRequest,
    GeneratorError,
    SnapshotStager,
    SubprocessCyxCodeExecutor,
    directory_digest,
    identify_container_executable,
    task_contract_from_record,
    validate_proposal,
)


CYXCODE_IMAGE = "sha256:f0a466626dcb1f123645ea9a40e2e7ef55c046dd7b76b8726d603605751b560c"
CYXCODE_EXECUTABLE = "sha256:8c9d82ad1dc42961666470248e9a2241a45eeb1f0327fa6ec6aefe61c6c1a31e"
PATCH_IMAGE = "python@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65"
MODEL = "opencode/big-pickle"
MODEL_RECORD = {
    "provider": "opencode",
    "model": "big-pickle",
    "name": "Big Pickle",
    "input_cost": 0,
    "output_cost": 0,
    "tool_call": True,
    "input_modality": "text",
    "output_modality": "text",
    "registry": "bundled models-snapshot.js",
}
PROVIDER_SUBMISSION_APPROVED = False
PROVIDER_BLOCK_REASON = "big-pickle-stealth-model-and-free-period-data-improvement-use"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def latest_events(path: Path) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank ledger line {number}")
        event = json.loads(line)
        latest[event["candidate_id"]] = event
    return latest


def load_row(multilingual: Path, verified: Path, event: dict) -> dict:
    import pyarrow.parquet as parquet

    source = multilingual if event["benchmark"]["dataset_id"].endswith("Multilingual") else verified
    table = parquet.read_table(
        source,
        filters=[("instance_id", "=", event["benchmark"]["instance_id"])],
    )
    rows = table.to_pylist()
    if len(rows) != 1:
        raise ValueError(f"expected one pinned row, got {len(rows)}")
    row = rows[0]
    if row["base_commit"] != event["source"]["base_revision"]:
        raise ValueError("pinned row base revision mismatch")
    return row


def source_record(path: Path, candidate: str) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    matches = [case for case in record["cases"] if case["candidate_id"] == candidate]
    if len(matches) != 1 or matches[0]["snapshot_gate"] != "passed":
        raise ValueError("candidate has no passed source snapshot")
    return matches[0]


def archive_source(docker: str, case: dict) -> bytes:
    result = subprocess.run(
        (
            docker,
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "git",
            case["image_reference"],
            "-C",
            "/testbed",
            "archive",
            "--format=tar",
            case["base_revision"],
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
        raise RuntimeError(f"source archive failed: {detail[:500]}")
    digest = hashlib.sha256(result.stdout).hexdigest()
    if digest != case["source_archive_sha256"]:
        raise RuntimeError("source archive digest mismatch")
    return result.stdout


def extract_archive(content: bytes, target: Path) -> None:
    target.mkdir()
    with tarfile.open(fileobj=BytesIO(content), mode="r:") as archive:
        archive.extractall(target, filter="data")


def task_record(event: dict, row: dict, snapshot_digest: str) -> dict:
    repository = event["source"]["repository"]
    revision = event["source"]["base_revision"]
    return {
        "schema_version": "1.0.0",
        "task_id": event["benchmark"]["instance_id"],
        "raw_request": row["problem_statement"],
        "repository": {
            "source": f"https://github.com/{repository}/tree/{revision}",
            "revision": revision,
            "snapshot_digest": snapshot_digest,
        },
        "goal": "Resolve the reported defect with the smallest correct repository patch.",
        "constraints": [
            {
                "id": "constraint-scope",
                "kind": "scope",
                "text": "Modify only files necessary to resolve the reported defect.",
                "hard": True,
                "source": "pilot protocol",
            },
            {
                "id": "constraint-no-reference",
                "kind": "authorization",
                "text": "Do not seek or use reference solutions, hidden checks, or external issue content.",
                "hard": True,
                "source": "pilot protocol",
            },
            {
                "id": "constraint-preserve-controls",
                "kind": "compatibility",
                "text": "Preserve unrelated existing behavior and tests.",
                "hard": True,
                "source": "pilot protocol",
            },
        ],
        "success_criteria": [
            {
                "id": "criterion-reported-defect",
                "text": "The resulting patch addresses the behavior described in the task.",
                "verification": "tests.fail_to_pass",
            },
            {
                "id": "criterion-regression",
                "text": "Relevant existing regression controls continue to pass.",
                "verification": "tests.pass_to_pass",
            },
        ],
        "out_of_scope": [
            "Reference patch and pull-request implementation",
            "Blinded verification scripts and expected test lists",
            "Unrelated refactoring or dependency upgrades",
        ],
        "unresolved_questions": [],
        "risk": {"level": "standard"},
        "allowed_tools": ["read", "search", "edit", "shell"],
        "required_checks": [
            "scope.paths",
            "patch.canonical",
            "tests.fail_to_pass",
            "tests.pass_to_pass",
        ],
    }


def docker_version(docker: str) -> str:
    result = subprocess.run(
        (docker, "version", "--format", "{{.Client.Version}}/{{.Server.Version}}"),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=True,
        text=True,
        timeout=15,
    )
    return result.stdout.strip()


def write_evidence(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--source-evidence", type=Path, required=True)
    parser.add_argument("--multilingual", type=Path, required=True)
    parser.add_argument("--verified", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--recorded-at", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=900)
    args = parser.parse_args()

    if not PROVIDER_SUBMISSION_APPROVED:
        raise SystemExit(f"provider submission blocked: {PROVIDER_BLOCK_REASON}")

    docker = shutil.which("docker")
    bun = shutil.which("bun")
    if docker is None or bun is None:
        raise SystemExit("Docker and Bun are required")
    events = latest_events(args.ledger)
    event = events.get(args.candidate)
    if event is None:
        raise SystemExit(f"unknown candidate: {args.candidate}")
    case = source_record(args.source_evidence, args.candidate)
    row = load_row(args.multilingual, args.verified, event)

    cache = (ROOT / ".replay_cache").resolve()
    artifacts = args.artifact_root.resolve()
    try:
        artifacts.relative_to(cache)
    except ValueError as error:
        raise SystemExit("artifact-root must remain under .replay_cache") from error
    artifacts.parent.mkdir(parents=True, exist_ok=True)

    bridge = ROOT / "integrations" / "cyxcode" / "packages" / "opencode" / "src" / "sheath-bridge.ts"
    proxy = ROOT / "integrations" / "cyxcode" / "packages" / "opencode" / "src" / "sheath-docker.ts"
    patch_root = ROOT / "sheath" / "src"
    for required in (bridge, proxy, patch_root):
        if not required.exists():
            raise SystemExit(f"missing required integration path: {required}")

    with TemporaryDirectory(prefix="cyxcode-pilot-", dir=cache) as temporary:
        root = Path(temporary)
        source = root / "source"
        extract_archive(archive_source(str(Path(docker).resolve()), case), source)
        source_digest = directory_digest(source)
        contract_record = task_record(event, row, source_digest)
        contract = task_contract_from_record(contract_record)
        task_bytes = (json.dumps(contract_record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        forbidden = (row["patch"], row["test_patch"], row["eval_script"])
        if any(value and value in task_bytes.decode("utf-8") for value in forbidden):
            raise RuntimeError("generator task contains a blinded artifact")

        store = ArtifactStore(artifacts)
        stager = SnapshotStager(root / "staging")
        with stager.stage(source) as snapshot:
            request = GenerationRequest(
                contract,
                event["source"]["base_revision"],
                snapshot.source_digest,
                1,
            )
            executor = SubprocessCyxCodeExecutor(
                (str(Path(bun).resolve()), "--conditions=browser", str(bridge.resolve())),
                (
                    str(Path(bun).resolve()),
                    str(proxy.resolve()),
                    str(Path(docker).resolve()),
                    CYXCODE_IMAGE,
                    CYXCODE_EXECUTABLE,
                ),
                (root / "isolation").resolve(),
                MODEL,
                {
                    "enabled_providers": ["opencode"],
                    "provider": {
                        "opencode": {"options": {"apiKey": "public"}},
                    },
                },
                CYXCODE_EXECUTABLE,
                timeout_seconds=args.timeout_seconds,
            )
            patch_identity = identify_container_executable(
                "python",
                "/usr/local/bin/python",
                PATCH_IMAGE.rpartition("@")[2],
            )
            backend = DockerCliBackend(
                DockerSandboxConfig(
                    docker_cli=Path(docker),
                    docker_version=docker_version(str(Path(docker).resolve())),
                    image=PATCH_IMAGE,
                    workspace=snapshot.binding,
                    patch_runtime_root=patch_root,
                )
            )
            generator = CyxCodeGenerator(
                f"cyxcode:2.3.8:{MODEL}",
                executor,
                DockerPatchExtractor(backend, patch_identity),
            )
            try:
                proposal = generator.propose(request, snapshot, store)
                validated = validate_proposal(
                    request,
                    proposal,
                    snapshot,
                    store,
                    generator.generator_id,
                )
            except GeneratorError as error:
                evidence = {
                    "schema_version": "1.0.0",
                    "recorded_at": args.recorded_at,
                    "status": "generator_failed",
                    "candidate_id": args.candidate,
                    "instance_id": event["benchmark"]["instance_id"],
                    "model": MODEL_RECORD,
                    "failure_reason": str(error),
                    "retained_artifacts": [
                        {
                            "id": item.id,
                            "digest": item.digest,
                            "kind": item.kind,
                            "size_bytes": item.size_bytes,
                        }
                        for item in error.artifacts
                    ],
                    "source_archive_sha256": case["source_archive_sha256"],
                    "source_directory_digest": source_digest,
                    "task_contract_sha256": hashlib.sha256(task_bytes).hexdigest(),
                    "gold_patch_in_generator_context": False,
                    "blinded_checks_in_generator_context": False,
                    "disposition": "quarantined",
                }
                write_evidence(args.output, evidence)
                print(f"FAILED: {args.candidate}: {error}")
                return 1

            evidence = {
                "schema_version": "1.0.0",
                "recorded_at": args.recorded_at,
                "status": "proposal_captured_verification_pending",
                "candidate_id": args.candidate,
                "instance_id": event["benchmark"]["instance_id"],
                "language": event["source"]["language"],
                "repository": event["source"]["repository"],
                "base_revision": event["source"]["base_revision"],
                "model": MODEL_RECORD,
                "generator_id": generator.generator_id,
                "cyxcode_image": CYXCODE_IMAGE,
                "cyxcode_executable_digest": CYXCODE_EXECUTABLE,
                "patch_image": PATCH_IMAGE,
                "source_archive_sha256": case["source_archive_sha256"],
                "source_directory_digest": source_digest,
                "task_contract_sha256": hashlib.sha256(task_bytes).hexdigest(),
                "proposal_id": validated.proposal.id,
                "response_artifact": {
                    "id": validated.response_artifact.id,
                    "digest": validated.response_artifact.digest,
                    "size_bytes": validated.response_artifact.size_bytes,
                },
                "patch_artifact": {
                    "id": validated.patch_artifact.id,
                    "digest": validated.patch_artifact.digest,
                    "size_bytes": validated.patch_artifact.size_bytes,
                },
                "changed_paths": list(validated.changed_paths),
                "result_directory_digest": validated.result_digest,
                "gold_patch_in_generator_context": False,
                "blinded_checks_in_generator_context": False,
                "verification": "pending",
                "disposition": "quarantined",
                "raw_artifact_boundary": ".replay_cache only",
                "inputs": {
                    "ledger_sha256": sha256_file(args.ledger),
                    "source_evidence_sha256": sha256_file(args.source_evidence),
                    "multilingual_parquet_sha256": sha256_file(args.multilingual),
                    "verified_parquet_sha256": sha256_file(args.verified),
                    "runner_sha256": sha256_file(Path(__file__)),
                },
            }
            write_evidence(args.output, evidence)
            print(
                f"CAPTURED: {args.candidate}; proposal={validated.proposal.id}; "
                f"paths={list(validated.changed_paths)}"
            )
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
