"""Prove that a container can mutate a disposable copy, not its source."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from sheath import (
    ArtifactStore,
    CommandAction,
    CommandPolicy,
    ConstrainedRunner,
    DockerCliBackend,
    DockerPatchExtractor,
    DockerSandboxConfig,
    EvidenceLedger,
    PatchApplier,
    SnapshotStager,
    ToolSession,
    directory_digest,
    identify_container_executable,
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Image pinned as name@sha256:...")
    parser.add_argument(
        "--artifact-root",
        default="snapshot-smoke-artifacts",
        help="Content-addressed evidence directory",
    )
    parser.add_argument(
        "--executable",
        default="/usr/local/bin/python",
        help="Absolute Python path inside the pinned image",
    )
    return parser.parse_args()


def docker_version(docker: str) -> str:
    return subprocess.run(
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


def main() -> int:
    options = arguments()
    docker = shutil.which("docker")
    if docker is None:
        raise SystemExit("Docker CLI was not found")
    version = docker_version(docker)
    project_root = Path(__file__).resolve().parents[1]
    source_root = project_root / "tests" / "smoke" / "writable_snapshot"
    artifact_root = Path(options.artifact_root)
    if not artifact_root.is_absolute():
        artifact_root = project_root / artifact_root
    store = ArtifactStore(artifact_root)
    image_digest = options.image.rpartition("@")[2]
    identity = identify_container_executable(
        "python",
        options.executable,
        image_digest,
    )

    snapshot_root: Path | None = None
    source_digest = ""
    outcome = None
    fixture_result = None
    patch_extraction = None
    patch_application = None
    application_root: Path | None = None
    application_contents_passed = False
    snapshot_mutations_passed = False
    with TemporaryDirectory(prefix="sheath-staging-", dir=project_root) as staging:
        stager = SnapshotStager(Path(staging))
        with stager.stage(source_root) as snapshot:
            snapshot_root = snapshot.root
            source_digest = snapshot.source_digest
            ledger = EvidenceLedger(source_digest)
            policy = CommandPolicy(
                snapshot.root,
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
                    workspace=snapshot.binding,
                )
            )
            outcome = ConstrainedRunner(session, backend).execute(
                CommandAction(
                    "action-snapshot-smoke",
                    ("python", "mutate_snapshot.py"),
                    ".",
                    30,
                    16_384,
                ),
                ("smoke.snapshot_write",),
            )
            observation = outcome.observation
            if observation is not None:
                stdout = store.get(observation.stdout_artifact_id)
                try:
                    fixture_result = json.loads(
                        (store.root / stdout.path).read_bytes()
                    )
                except (OSError, json.JSONDecodeError):
                    fixture_result = None
            patch_backend = DockerCliBackend(
                DockerSandboxConfig(
                    docker_cli=Path(docker),
                    docker_version=version,
                    image=options.image,
                    workspace=snapshot.binding,
                    patch_runtime_root=project_root / "src",
                )
            )
            patch_extraction = DockerPatchExtractor(
                patch_backend,
                identity,
            ).extract(snapshot, store)
            patch_record = json.loads(
                (store.root / patch_extraction.artifact.path).read_bytes()
            )
            changes = {change["path"]: change for change in patch_record["changes"]}
            snapshot_mutations_passed = (
                fixture_result
                == {
                    "created_file": True,
                    "seed_changed": True,
                    "seed_was_original": True,
                }
                and patch_extraction.changed_paths == ("generated.txt", "seed.txt")
                and changes["generated.txt"]["operation"] == "add"
                and changes["seed.txt"]["operation"] == "modify"
                and base64.b64decode(
                    changes["generated.txt"]["after"]["content_base64"]
                )
                == b"generated\n"
                and base64.b64decode(
                    changes["seed.txt"]["after"]["content_base64"]
                )
                == b"changed\n"
            )
        with stager.stage(source_root) as application_snapshot:
            application_root = application_snapshot.root
            patch_application = PatchApplier().apply(
                application_snapshot,
                patch_extraction.artifact,
                store,
            )
            application_contents_passed = (
                patch_application.result_digest == patch_extraction.result_digest
                and directory_digest(application_snapshot.root)
                == patch_extraction.result_digest
                and (application_snapshot.root / "generated.txt").read_bytes()
                == b"generated\n"
                and (application_snapshot.root / "seed.txt").read_bytes()
                == b"changed\n"
            )

    assert outcome is not None
    assert patch_extraction is not None
    assert patch_application is not None
    observation = outcome.observation
    source_unchanged = directory_digest(source_root) == source_digest
    snapshot_removed = snapshot_root is not None and not snapshot_root.exists()
    application_snapshot_removed = (
        application_root is not None and not application_root.exists()
    )
    summary = {
        "allowed": outcome.authorization.allowed,
        "application_changed_paths": list(patch_application.changed_paths),
        "application_contents_passed": application_contents_passed,
        "application_patch_artifact_id": patch_application.patch_artifact_id,
        "application_result_digest": patch_application.result_digest,
        "application_snapshot_removed": application_snapshot_removed,
        "docker_version": version,
        "evidence_passed": bool(outcome.evidence and outcome.evidence[0].passed),
        "executable": options.executable,
        "exit_code": None if observation is None else observation.exit_code,
        "fixture_result": fixture_result,
        "image": options.image,
        "observation_id": None if observation is None else observation.id,
        "observed_at": None if observation is None else observation.ended_at,
        "patch_artifact_id": patch_extraction.artifact.id,
        "patch_changed_paths": list(patch_extraction.changed_paths),
        "patch_digest": patch_extraction.artifact.digest,
        "patch_evidence_ids": list(patch_extraction.evidence_ids),
        "patch_observation_id": patch_extraction.observation_id,
        "patch_sandbox_digest": patch_extraction.sandbox_digest,
        "patch_stderr_artifact_id": patch_extraction.stderr_artifact_id,
        "patch_stdout_artifact_id": patch_extraction.stdout_artifact_id,
        "result_digest": patch_extraction.result_digest,
        "sandbox_digest": None if observation is None else observation.sandbox_digest,
        "snapshot_mutations_passed": snapshot_mutations_passed,
        "snapshot_removed": snapshot_removed,
        "source_digest": source_digest,
        "source_unchanged": source_unchanged,
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
    passed = (
        summary["evidence_passed"]
        and snapshot_mutations_passed
        and application_contents_passed
        and application_snapshot_removed
        and source_unchanged
        and snapshot_removed
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
