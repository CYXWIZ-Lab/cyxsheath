"""Run one free CyxCode infrastructure canary on a generated local fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sheath" / "src"))
sys.path.insert(0, str(Path(__file__).parent))

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
from validate_synthetic_canary_gate import validate as validate_gate  # noqa: E402


CYXCODE_IMAGE = "sha256:f0a466626dcb1f123645ea9a40e2e7ef55c046dd7b76b8726d603605751b560c"
CYXCODE_EXECUTABLE = "sha256:8c9d82ad1dc42961666470248e9a2241a45eeb1f0327fa6ec6aefe61c6c1a31e"
PATCH_IMAGE = "python@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65"
MODEL = "opencode/mimo-v2.5-free"
GATE = Path(__file__).parent / "review_evidence" / "phase6_synthetic_canary_gate.json"
PROHIBITED_MARKERS = (
    "swe-bench",
    "candidate_events.jsonl",
    "redis__redis-",
    "fmtlib__fmt-",
    "astropy__astropy-",
    "same_hello_query_plus.md",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ROOT / ".replay_cache" / "cyxcode-synthetic-canary" / "artifacts",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "proposal_evidence" / "phase6_synthetic_free_canary.json",
    )
    parser.add_argument("--recorded-at", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=180)
    return parser


def write_fixture(path: Path) -> None:
    path.mkdir()
    (path / "arithmetic.py").write_text(
        "def add(left: int, right: int) -> int:\n"
        "    \"\"\"Return the sum of two integers.\"\"\"\n"
        "    return left - right\n",
        encoding="utf-8",
        newline="\n",
    )
    (path / "test_arithmetic.py").write_text(
        "import unittest\n\n"
        "from arithmetic import add\n\n\n"
        "class ArithmeticTests(unittest.TestCase):\n"
        "    def test_adds_positive_integers(self):\n"
        "        self.assertEqual(5, add(2, 3))\n\n\n"
        "if __name__ == \"__main__\":\n"
        "    unittest.main()\n",
        encoding="utf-8",
        newline="\n",
    )


def task_record(snapshot_digest: str) -> dict:
    return {
        "schema_version": "1.0.0",
        "task_id": "synthetic-arithmetic-v1",
        "raw_request": "Fix the generated arithmetic fixture so its documented addition behavior passes its test.",
        "repository": {
            "source": "synthetic://sheath/arithmetic-v1",
            "revision": "synthetic-arithmetic-v1",
            "snapshot_digest": snapshot_digest,
        },
        "goal": "Correct the smallest implementation defect in the generated fixture.",
        "constraints": [
            {
                "id": "constraint-synthetic-scope",
                "kind": "scope",
                "text": "Modify only arithmetic.py when necessary.",
                "hard": True,
                "source": "synthetic canary policy",
            },
            {
                "id": "constraint-no-external-context",
                "kind": "authorization",
                "text": "Use only files in this generated fixture.",
                "hard": True,
                "source": "synthetic canary policy",
            },
        ],
        "success_criteria": [
            {
                "id": "criterion-generated-test",
                "text": "The included arithmetic test passes.",
                "verification": "python -m unittest -v",
            }
        ],
        "out_of_scope": ["New features", "Dependency changes", "External repositories"],
        "unresolved_questions": [],
        "risk": {"level": "light"},
        "allowed_tools": ["read", "edit", "shell"],
        "required_checks": ["scope.paths", "patch.canonical"],
    }


def cyxcode_config() -> dict:
    return {
        "enabled_providers": ["opencode"],
        "provider": {
            "opencode": {
                "options": {"apiKey": "public"},
                "models": {
                    "mimo-v2.5-free": {
                        "name": "MiMo-V2.5 Free",
                        "reasoning": True,
                        "tool_call": True,
                        "modalities": {"input": ["text"], "output": ["text"]},
                        "cost": {"input": 0, "output": 0},
                        "limit": {"context": 262144, "output": 65536},
                    }
                },
            }
        },
    }


def assert_synthetic_boundary(source: Path, record: dict) -> None:
    combined = json.dumps(record, sort_keys=True).lower()
    combined += "\n" + "\n".join(
        item.read_text(encoding="utf-8", errors="strict").lower()
        for item in sorted(source.rglob("*"))
        if item.is_file()
    )
    found = [marker for marker in PROHIBITED_MARKERS if marker in combined]
    if found:
        raise ValueError(f"synthetic fixture contains prohibited marker: {found[0]}")


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
    args = build_parser().parse_args()
    gate = validate_gate(GATE)
    if gate["execution_gate"]["decision"] != "approved_to_attempt_once":
        raise SystemExit("synthetic canary is not approved")

    cache = (ROOT / ".replay_cache").resolve()
    artifacts = args.artifact_root.resolve()
    try:
        artifacts.relative_to(cache)
    except ValueError as error:
        raise SystemExit("artifact-root must remain under .replay_cache") from error

    docker = shutil.which("docker")
    bun = shutil.which("bun")
    if docker is None or bun is None:
        raise SystemExit("Docker and Bun are required")
    bridge = ROOT / "integrations" / "cyxcode" / "packages" / "opencode" / "src" / "sheath-bridge.ts"
    proxy = ROOT / "integrations" / "cyxcode" / "packages" / "opencode" / "src" / "sheath-docker.ts"
    patch_root = ROOT / "sheath" / "src"
    for required in (bridge, proxy, patch_root):
        if not required.exists():
            raise SystemExit(f"missing required integration path: {required}")

    artifacts.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="cyxcode-synthetic-", dir=cache) as temporary:
        root = Path(temporary)
        source = root / "source"
        write_fixture(source)
        initial_source_digest = directory_digest(source)
        record = task_record(initial_source_digest)
        assert_synthetic_boundary(source, record)
        contract = task_contract_from_record(record)
        contract_digest = hashlib.sha256(
            (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        ).hexdigest()

        store = ArtifactStore(artifacts)
        stager = SnapshotStager(root / "staging")
        isolation = (root / "isolation").resolve()
        with stager.stage(source) as snapshot:
            request = GenerationRequest(contract, contract.repository.revision, snapshot.source_digest, 1)
            executor = SubprocessCyxCodeExecutor(
                (str(Path(bun).resolve()), "--conditions=browser", str(bridge.resolve())),
                (
                    str(Path(bun).resolve()),
                    str(proxy.resolve()),
                    str(Path(docker).resolve()),
                    CYXCODE_IMAGE,
                    CYXCODE_EXECUTABLE,
                ),
                isolation,
                MODEL,
                cyxcode_config(),
                CYXCODE_EXECUTABLE,
                timeout_seconds=args.timeout_seconds,
            )
            patch_identity = identify_container_executable(
                "python", "/usr/local/bin/python", PATCH_IMAGE.rpartition("@")[2]
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
                f"cyxcode:2.3.8:{MODEL}:synthetic",
                executor,
                DockerPatchExtractor(backend, patch_identity),
            )
            try:
                proposal = generator.propose(request, snapshot, store)
                validated = validate_proposal(
                    request, proposal, snapshot, store, generator.generator_id
                )
            except GeneratorError as error:
                evidence = {
                    "schema_version": "1.0.0",
                    "recorded_at": args.recorded_at,
                    "status": "generator_failed",
                    "input_class": "synthetic_public_non_sensitive_non_benchmark",
                    "model": MODEL,
                    "cost_class": "free",
                    "attempt": 1,
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
                    "task_contract_sha256": contract_digest,
                    "source_directory_digest": initial_source_digest,
                    "source_preserved": directory_digest(source) == initial_source_digest,
                    "benchmark_input_used": False,
                    "paid_credential_used": False,
                    "raw_artifact_boundary": ".replay_cache only",
                }
                write_evidence(args.output, evidence)
                print(f"FAILED: synthetic canary: {error}")
                return 1

            evidence = {
                "schema_version": "1.0.0",
                "recorded_at": args.recorded_at,
                "status": "proposal_captured",
                "input_class": "synthetic_public_non_sensitive_non_benchmark",
                "model": MODEL,
                "cost_class": "free",
                "attempt": 1,
                "proposal_id": validated.proposal.id,
                "changed_paths": list(validated.changed_paths),
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
                "task_contract_sha256": contract_digest,
                "source_directory_digest": initial_source_digest,
                "result_directory_digest": validated.result_digest,
                "source_preserved": directory_digest(source) == initial_source_digest,
                "benchmark_input_used": False,
                "paid_credential_used": False,
                "raw_artifact_boundary": ".replay_cache only",
            }
            write_evidence(args.output, evidence)
            print(f"CAPTURED: synthetic canary; paths={list(validated.changed_paths)}")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
