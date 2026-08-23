"""Run the complete Sheath proposal-to-verdict path through pinned CyxCode."""

from __future__ import annotations

import argparse
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from threading import Thread

from sheath import (
    ArtifactStore,
    CyxCodeGenerator,
    DockerCliBackend,
    DockerPatchExtractor,
    DockerSandboxConfig,
    Evidence,
    RepositorySnapshot,
    RunBudget,
    RunMetadata,
    SnapshotStager,
    SubprocessCyxCodeExecutor,
    VerificationReport,
    directory_digest,
    encode_run_record,
    identify_container_executable,
    run_single_attempt,
    task_contract_from_record,
)


CYXCODE_IMAGE = "sha256:8a797f1541bc715f362d0e42981c12d57aa599ee4b6ba38ea5e8332a4c06539a"
CYXCODE_EXECUTABLE = "sha256:e9e88c1635c5c357395fd2e46c211c20c5c1b99d11d81ce83ea67fce580234b0"
PATCH_IMAGE = "python@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65"


class _Provider(BaseHTTPRequestHandler):
    prompt = ""

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if not self.path.endswith("/chat/completions"):
            self.send_error(404)
            return
        size = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(size))
        users = [item for item in payload.get("messages", []) if item.get("role") == "user"]
        content = users[-1].get("content", "") if users else ""
        type(self).prompt = content if isinstance(content, str) else json.dumps(content)
        chunks = (
            {"id": "chatcmpl-sheath", "object": "chat.completion.chunk", "choices": [{"delta": {"role": "assistant"}}]},
            {"id": "chatcmpl-sheath", "object": "chat.completion.chunk", "choices": [{"delta": {"content": "Inspected seed.txt; no change is required."}}]},
            {"id": "chatcmpl-sheath", "object": "chat.completion.chunk", "choices": [{"delta": {}, "finish_reason": "stop"}]},
        )
        body = "".join(f"data: {json.dumps(item, separators=(',', ':'))}\n\n" for item in chunks) + "data: [DONE]\n\n"
        encoded = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


class _PassingVerifier:
    def verify(self, proposal, snapshot, ledger, store) -> VerificationReport:
        evidence = tuple(
            Evidence(
                f"evidence-{index}",
                check,
                proposal.request.revision,
                True,
                "rule",
                "deterministic smoke assertion",
            )
            for index, check in enumerate(proposal.request.contract.required_checks, 1)
        )
        return VerificationReport(evidence)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", default="cyxcode-smoke-artifacts")
    parser.add_argument("--cyxcode-image", default=CYXCODE_IMAGE)
    parser.add_argument("--cyxcode-digest", default=CYXCODE_EXECUTABLE)
    parser.add_argument("--patch-image", default=PATCH_IMAGE)
    return parser.parse_args()


def _docker_version(docker: str) -> str:
    return subprocess.run(
        (docker, "version", "--format", "{{.Client.Version}}/{{.Server.Version}}"),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
        shell=False,
        text=True,
        timeout=15,
    ).stdout.strip()


def main() -> int:
    options = _arguments()
    docker = shutil.which("docker")
    bun = shutil.which("bun")
    if docker is None or bun is None:
        raise SystemExit("Docker and Bun must both be installed")
    root = Path(__file__).resolve().parents[1]
    integration = root.parent / "integrations" / "cyxcode" / "packages" / "opencode"
    bridge = integration / "src" / "sheath-bridge.ts"
    proxy = integration / "src" / "sheath-docker.ts"
    if not bridge.is_file() or not proxy.is_file():
        raise SystemExit("the local CyxCode bridge sources were not found")
    artifacts = Path(options.artifact_root)
    if not artifacts.is_absolute():
        artifacts = root / artifacts
    store = ArtifactStore(artifacts)
    version = _docker_version(docker)

    server = ThreadingHTTPServer(("0.0.0.0", 0), _Provider)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with TemporaryDirectory(prefix="sheath-cyxcode-", dir=root) as temporary:
            temporary_root = Path(temporary)
            source = temporary_root / "source"
            source.mkdir()
            (source / "seed.txt").write_text("unchanged\n", encoding="utf-8")
            policy = source / ".opencode" / "cyxwatch"
            policy.mkdir(parents=True)
            (policy / "policy.json").write_text(
                json.dumps(
                    {
                        "version": 2,
                        "rules": [{
                            "id": "fixture-provider",
                            "permission": ["webfetch"],
                            "host": ["host.docker.internal:*"],
                            "decision": "allow",
                        }],
                    },
                    separators=(",", ":"),
                ),
                encoding="utf-8",
            )
            source_digest = directory_digest(source)
            stager = SnapshotStager(temporary_root / "staging")
            with stager.stage(source) as snapshot:
                contract = task_contract_from_record(
                    {
                        "schema_version": "1.0.0",
                        "task_id": "cyxcode-pinned-smoke",
                        "raw_request": "Inspect seed.txt and report completion without editing files.",
                        "repository": {
                            "source": str(source),
                            "revision": "fixture-r1",
                            "snapshot_digest": snapshot.source_digest,
                        },
                        "goal": "Prove the pinned CyxCode image completes the Sheath proposal-to-verdict path.",
                        "constraints": [{
                            "id": "constraint-no-edit",
                            "kind": "scope",
                            "text": "Do not modify repository files.",
                            "hard": True,
                            "source": "smoke fixture",
                        }],
                        "success_criteria": [{
                            "id": "criterion-complete",
                            "text": "CyxCode returns a successful, exportable session.",
                            "verification": "tests.regression",
                        }],
                        "out_of_scope": ["External model providers"],
                        "unresolved_questions": [],
                        "risk": {"level": "light"},
                        "allowed_tools": ["read"],
                        "required_checks": ["scope.paths", "tests.regression"],
                    }
                )
                contract = replace(
                    contract,
                    repository=RepositorySnapshot(
                        contract.repository.source,
                        contract.repository.revision,
                        snapshot.source_digest,
                    ),
                )
                executor = SubprocessCyxCodeExecutor(
                    (str(Path(bun).resolve()), "--conditions=browser", str(bridge.resolve())),
                    (
                        str(Path(bun).resolve()),
                        str(proxy.resolve()),
                        str(Path(docker).resolve()),
                        options.cyxcode_image,
                        options.cyxcode_digest,
                    ),
                    (temporary_root / "isolation").resolve(),
                    "fixture/model",
                    {
                        "enabled_providers": ["fixture"],
                        "provider": {
                            "fixture": {
                                "name": "Sheath deterministic fixture",
                                "npm": "@ai-sdk/openai-compatible",
                                "env": [],
                                "models": {
                                    "model": {
                                        "name": "Fixture model",
                                        "tool_call": True,
                                        "limit": {"context": 8192, "output": 1024},
                                    }
                                },
                                "options": {
                                    "apiKey": "fixture-secret",
                                    "baseURL": f"http://host.docker.internal:{server.server_port}/v1",
                                },
                            }
                        },
                    },
                    options.cyxcode_digest,
                    timeout_seconds=90,
                )
                patch_identity = identify_container_executable(
                    "python",
                    "/usr/local/bin/python",
                    options.patch_image.rpartition("@")[2],
                )
                patch_backend = DockerCliBackend(
                    DockerSandboxConfig(
                        docker_cli=Path(docker),
                        docker_version=version,
                        image=options.patch_image,
                        workspace=snapshot.binding,
                        patch_runtime_root=root / "src",
                    )
                )
                generator = CyxCodeGenerator(
                    "cyxcode:2.3.8:fixture/model",
                    executor,
                    DockerPatchExtractor(patch_backend, patch_identity),
                )
                result = run_single_attempt(
                    contract,
                    generator,
                    _PassingVerifier(),
                    snapshot,
                    store,
                    RunMetadata(
                        "run-cyxcode-pinned-smoke",
                        "sheath_stage0",
                        generator.generator_id,
                        "runner-r1",
                        options.cyxcode_digest,
                        "sha256:" + "0" * 64,
                        supervisor_id="sheath-stage0-0.1.0",
                    ),
                    RunBudget(1, 180),
                )
                record_artifact = store.store_bytes("other", encode_run_record(result.record))
                response = store.get(result.proposal.response_artifact.id)
                response_bytes = (store.root / response.path).read_bytes()
                source_unchanged = directory_digest(source) == source_digest
                prompt_preserved = "cyxcode-pinned-smoke" in _Provider.prompt
                secret_redacted = b"fixture-secret" not in response_bytes
                summary = {
                    "cyxcode_executable_digest": options.cyxcode_digest,
                    "cyxcode_image": options.cyxcode_image,
                    "decision": result.decision.verdict.value,
                    "docker_version": version,
                    "patch_image": options.patch_image,
                    "prompt_preserved": prompt_preserved,
                    "record_artifact_id": record_artifact.id,
                    "record_digest": result.digest,
                    "response_artifact_id": result.proposal.response_artifact.id,
                    "secret_redacted": secret_redacted,
                    "source_unchanged": source_unchanged,
                }
                manifest = store.store_bytes(
                    "manifest",
                    (json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n").encode(),
                )
                summary["manifest_artifact_id"] = manifest.id
                print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
                return 0 if all(
                    (
                        result.decision.verdict.value == "accept",
                        prompt_preserved,
                        secret_redacted,
                        source_unchanged,
                    )
                ) else 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
