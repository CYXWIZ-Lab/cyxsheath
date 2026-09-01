"""Run the frozen three-task A-versus-D0 CyxCode development pilot once."""

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
    CommandPolicy,
    CoordinatorError,
    CyxCodeGenerator,
    DockerCliBackend,
    DockerPatchExtractor,
    DockerSandboxConfig,
    RunBudget,
    RunMetadata,
    SnapshotStager,
    SubprocessCyxCodeExecutor,
    digest_bytes,
    encode_run_record,
    identify_container_executable,
    run_bounded_attempts,
    run_single_attempt,
)
from phase6_minimum_poc import (  # noqa: E402
    PocTask,
    PocVerifier,
    build_contract,
    curate_run,
    load_tasks,
)


CYXCODE_IMAGE = "sha256:f0a466626dcb1f123645ea9a40e2e7ef55c046dd7b76b8726d603605751b560c"
CYXCODE_EXECUTABLE = "sha256:8c9d82ad1dc42961666470248e9a2241a45eeb1f0327fa6ec6aefe61c6c1a31e"
PATCH_IMAGE = "python@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65"
MODEL = "opencode/mimo-v2.5-free"
GENERATOR_ID = f"cyxcode:2.3.8:{MODEL}:phase6-minimum-poc-v1"
MANIFEST = Path(__file__).parent / "poc_tasks" / "manifest.json"
PROTOCOL = ROOT / "Thesis" / "Phase6_Minimum_POC_Protocol.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _docker_version(docker: str) -> str:
    return subprocess.run(
        (docker, "version", "--format", "{{.Client.Version}}/{{.Server.Version}}"),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=True,
        text=True,
        timeout=15,
    ).stdout.strip()


def _git_identity() -> str:
    status = subprocess.run(
        ("git", "status", "--porcelain"),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=True,
        text=True,
        timeout=15,
    ).stdout
    if status:
        raise RuntimeError("repository must be clean before the first POC model call")
    return subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=True,
        text=True,
        timeout=15,
    ).stdout.strip()


def _cyxcode_config() -> dict[str, object]:
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


def _generator(
    snapshot,
    *,
    docker: Path,
    docker_version: str,
    bun: Path,
    bridge: Path,
    proxy: Path,
    isolation: Path,
) -> CyxCodeGenerator:
    executor = SubprocessCyxCodeExecutor(
        (str(bun), "--conditions=browser", str(bridge)),
        (str(bun), str(proxy), str(docker), CYXCODE_IMAGE, CYXCODE_EXECUTABLE),
        isolation,
        MODEL,
        _cyxcode_config(),
        CYXCODE_EXECUTABLE,
        environment={"CYXCODE_DISABLE_STATE_CONTEXT": "1"},
        timeout_seconds=180,
    )
    identity = identify_container_executable("python", "/usr/local/bin/python", PATCH_IMAGE.rpartition("@")[2])
    backend = DockerCliBackend(
        DockerSandboxConfig(
            docker_cli=docker,
            docker_version=docker_version,
            image=PATCH_IMAGE,
            workspace=snapshot.binding,
            patch_runtime_root=ROOT / "sheath" / "src",
        )
    )
    return CyxCodeGenerator(GENERATOR_ID, executor, DockerPatchExtractor(backend, identity))


def _verifier(task: PocTask, snapshot, docker: Path, docker_version: str):
    identity = identify_container_executable("python", "/usr/local/bin/python", PATCH_IMAGE.rpartition("@")[2])
    policy = CommandPolicy(snapshot.root, (identity,), max_timeout_seconds=30, max_output_bytes=65_536)

    def backend_factory(current_snapshot):
        return DockerCliBackend(
            DockerSandboxConfig(
                docker_cli=docker,
                docker_version=docker_version,
                image=PATCH_IMAGE,
                workspace=current_snapshot.binding,
            )
        )

    return PocVerifier(task, policy, backend_factory), policy, backend_factory(snapshot).profile.environment_digest


def _run_condition(
    task: PocTask,
    condition: str,
    temporary: Path,
    store: ArtifactStore,
    *,
    docker: Path,
    docker_version: str,
    bun: Path,
    bridge: Path,
    proxy: Path,
    runner_revision: str,
) -> dict[str, object]:
    stager = SnapshotStager(temporary / f"staging-{task.task_id}-{condition.lower()}")
    with stager.stage(task.source_root) as snapshot:
        contract = build_contract(task, snapshot.source_digest)
        generator = _generator(
            snapshot,
            docker=docker,
            docker_version=docker_version,
            bun=bun,
            bridge=bridge,
            proxy=proxy,
            isolation=(temporary / f"isolation-{task.task_id}-{condition.lower()}").resolve(),
        )
        verifier, policy, environment_digest = _verifier(task, snapshot, docker, docker_version)
        metadata = RunMetadata(
            run_id=f"phase6-minimum-poc-v1:{task.task_id}:{condition}",
            condition="direct" if condition == "A" else "sheath_stage0",
            generator_id=GENERATOR_ID,
            runner_revision=runner_revision,
            environment_digest=environment_digest,
            policy_digest=policy.digest,
            supervisor_id=None if condition == "A" else "sheath-stage0-0.1.0",
            seed=0,
        )
        if condition == "A":
            result = run_single_attempt(
                contract,
                generator,
                verifier,
                snapshot,
                store,
                metadata,
                RunBudget(max_attempts=1, max_wall_seconds=240),
            )
        else:
            result = run_bounded_attempts(
                contract,
                generator,
                verifier,
                snapshot,
                stager,
                store,
                metadata,
                RunBudget(max_attempts=2, max_wall_seconds=420),
            )
        store.store_bytes("manifest", encode_run_record(result.record))
        return curate_run(result.record, result.digest, condition)


def _write(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recorded-at", required=True)
    parser.add_argument("--artifact-root", type=Path, default=ROOT / ".replay_cache" / "phase6-minimum-poc-v1" / "artifacts")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "poc_evidence" / "phase6_minimum_poc_v1.json")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists():
        raise SystemExit("POC output already exists; automatic rerun is blocked")
    commit = _git_identity()
    tasks = load_tasks(MANIFEST)
    docker_text = shutil.which("docker")
    bun_text = shutil.which("bun")
    if docker_text is None or bun_text is None:
        raise SystemExit("Docker and Bun are required")
    docker = Path(docker_text).resolve(strict=True)
    bun = Path(bun_text).resolve(strict=True)
    integration = ROOT / "integrations" / "cyxcode" / "packages" / "opencode" / "src"
    bridge = (integration / "sheath-bridge.ts").resolve(strict=True)
    proxy = (integration / "sheath-docker.ts").resolve(strict=True)
    version = _docker_version(str(docker))
    artifact_root = args.artifact_root.resolve()
    cache = (ROOT / ".replay_cache").resolve()
    if not artifact_root.is_relative_to(cache):
        raise SystemExit("artifact root must remain under .replay_cache")
    artifact_root.parent.mkdir(parents=True, exist_ok=True)
    store = ArtifactStore(artifact_root)

    record: dict[str, object] = {
        "schema_version": "1.0.0",
        "status": "incomplete",
        "pilot_id": "phase6-minimum-poc-v1",
        "recorded_at": args.recorded_at,
        "protocol_sha256": _sha256(PROTOCOL),
        "task_manifest_sha256": _sha256(MANIFEST),
        "runner_commit": commit,
        "runner_sha256": _sha256(Path(__file__)),
        "model": MODEL,
        "cost_class": "free",
        "cyxcode_image": CYXCODE_IMAGE,
        "cyxcode_executable_digest": CYXCODE_EXECUTABLE,
        "verification_image": PATCH_IMAGE,
        "runs": [],
    }
    _write(output, record)
    with TemporaryDirectory(prefix="phase6-minimum-poc-", dir=cache) as name:
        temporary = Path(name)
        for task in tasks:
            for condition in task.condition_order:
                try:
                    row = _run_condition(
                        task,
                        condition,
                        temporary,
                        store,
                        docker=docker,
                        docker_version=version,
                        bun=bun,
                        bridge=bridge,
                        proxy=proxy,
                        runner_revision=commit,
                    )
                except CoordinatorError as error:
                    if error.record is not None and error.record_digest is not None:
                        store.store_bytes("manifest", encode_run_record(error.record))
                        row = curate_run(error.record, error.record_digest, condition)
                    else:
                        row = {
                            "condition": condition,
                            "status": "infrastructure_failure",
                            "verified_success": False,
                            "verdict": "failed",
                            "attempts": 0,
                            "wall_seconds": 0.0,
                            "recovered_after_first_attempt": False,
                            "record_digest": None,
                            "failure_reason_codes": [error.failure_code or "coordinator.failure"],
                        }
                row["task_id"] = task.task_id
                record["runs"].append(row)  # type: ignore[union-attr]
                _write(output, record)

    runs = record["runs"]
    assert isinstance(runs, list)
    record["status"] = "complete"
    record["summary"] = {
        "task_count": len(tasks),
        "run_count": len(runs),
        "A_verified_success": sum(item["verified_success"] is True for item in runs if item["condition"] == "A"),
        "D0_verified_success": sum(item["verified_success"] is True for item in runs if item["condition"] == "D0"),
        "D0_recoveries": sum(item["recovered_after_first_attempt"] is True for item in runs if item["condition"] == "D0"),
        "infrastructure_failures": sum(item["status"] == "infrastructure_failure" for item in runs),
        "inferential_claim_authorized": False,
    }
    record["artifact_boundary"] = ".replay_cache_only_for_raw_prompts_responses_patches_tool_output_and_canonical_run_records"
    _write(output, record)
    print(json.dumps(record["summary"], sort_keys=True))
    return 0 if record["summary"]["infrastructure_failures"] == 0 else 1  # type: ignore[index]


if __name__ == "__main__":
    raise SystemExit(main())
