"""Run the first Sheath smoke fixture through a digest-pinned Docker image."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

from sheath import (
    ArtifactStore,
    CommandAction,
    CommandPolicy,
    ConstrainedRunner,
    DockerCliBackend,
    DockerSandboxConfig,
    EvidenceLedger,
    ToolSession,
    identify_container_executable,
    read_only_workspace,
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Image pinned as name@sha256:...")
    parser.add_argument(
        "--artifact-root",
        default="smoke-artifacts",
        help="Content-addressed output directory",
    )
    parser.add_argument(
        "--executable",
        default="/usr/local/bin/python",
        help="Absolute Python path inside the pinned image",
    )
    return parser.parse_args()


def main() -> int:
    options = arguments()
    docker = shutil.which("docker")
    if docker is None:
        raise SystemExit("Docker CLI was not found")
    version = subprocess.run(
        (
            docker,
            "version",
            "--format",
            "{{.Client.Version}}/{{.Server.Version}}",
        ),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
        shell=False,
        text=True,
        timeout=10,
    ).stdout.strip()

    project_root = Path(__file__).resolve().parents[1]
    artifact_root = Path(options.artifact_root)
    if not artifact_root.is_absolute():
        artifact_root = project_root / artifact_root
    image_digest = options.image.rpartition("@")[2]
    identity = identify_container_executable(
        "python",
        options.executable,
        image_digest,
    )
    store = ArtifactStore(artifact_root)
    ledger = EvidenceLedger("smoke-fixture-r1")
    policy = CommandPolicy(
        project_root,
        (identity,),
        max_timeout_seconds=35,
        max_output_bytes=16_384,
    )
    session = ToolSession(policy, ledger, store)
    backend = DockerCliBackend(
        DockerSandboxConfig(
            docker_cli=Path(docker),
            docker_version=version,
            image=options.image,
            workspace=read_only_workspace(project_root),
        )
    )
    outcome = ConstrainedRunner(session, backend).execute(
        CommandAction(
            "action-container-smoke",
            ("python", "container_smoke.py"),
            "tests/smoke",
            30,
            16_384,
        ),
        ("smoke.isolation",),
    )
    observation = outcome.observation
    fixture_assertions_passed = False
    if observation is not None:
        stdout = store.get(observation.stdout_artifact_id)
        try:
            fixture_result = json.loads((store.root / stdout.path).read_bytes())
        except (OSError, json.JSONDecodeError):
            fixture_result = None
        fixture_assertions_passed = fixture_result == {
            "network_blocked": True,
            "workspace_write_blocked": True,
        }
    summary = {
        "allowed": outcome.authorization.allowed,
        "docker_version": version,
        "evidence_passed": bool(outcome.evidence and outcome.evidence[0].passed),
        "executable": options.executable,
        "exit_code": None if observation is None else observation.exit_code,
        "fixture_assertions_passed": fixture_assertions_passed,
        "image": options.image,
        "observation_id": None if observation is None else observation.id,
        "observed_at": None if observation is None else observation.ended_at,
        "sandbox_guarantees": (
            [] if observation is None else list(observation.sandbox_guarantees)
        ),
        "sandbox_digest": None if observation is None else observation.sandbox_digest,
        "started_at": None if observation is None else observation.started_at,
        "stderr_artifact_id": (
            None if observation is None else observation.stderr_artifact_id
        ),
        "stdout_artifact_id": (
            None if observation is None else observation.stdout_artifact_id
        ),
        "stdout_truncated": (
            None if observation is None else observation.stdout_truncated
        ),
        "stderr_truncated": (
            None if observation is None else observation.stderr_truncated
        ),
        "timed_out": None if observation is None else observation.timed_out,
    }
    manifest = store.store_bytes(
        "manifest",
        (json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        ),
    )
    summary["manifest_artifact_id"] = manifest.id
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0 if summary["evidence_passed"] and fixture_assertions_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
