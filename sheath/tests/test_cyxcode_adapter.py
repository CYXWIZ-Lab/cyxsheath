from dataclasses import replace
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from sheath import (
    ArtifactStore,
    CoordinatorError,
    CyxCodeExecution,
    CyxCodeGenerator,
    Evidence,
    GenerationRequest,
    GeneratorError,
    PatchExtraction,
    RepositorySnapshot,
    RunBudget,
    RunMetadata,
    SnapshotStager,
    SubprocessCyxCodeExecutor,
    VerificationReport,
    run_single_attempt,
    task_contract_from_record,
    build_cyxcode_prompt,
    validate_proposal,
)
from sheath.patches import _build_patch_record, _runtime_digest, _validate_record
from sheath.tools import identify_container_executable

from fixtures import task_record


IMAGE_DIGEST = "sha256:" + "1" * 64


def execution(status="ok", reason=None):
    prompt_digest = "sha256:" + "2" * 64
    environment_digest = "sha256:" + "3" * 64
    envelope = {
        "environment_digest": environment_digest,
        "failure_reason": reason,
        "prompt_digest": prompt_digest,
        "schema_version": "1.0.0",
        "session": {"id": "session-fixture"},
        "status": status,
    }
    encoded = (
        json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    return CyxCodeExecution(
        status,
        encoded,
        prompt_digest,
        environment_digest,
        reason,
    )


class FixtureExecutor:
    def __init__(self, result):
        self.result = result
        self.requests = []

    def execute(self, request, snapshot):
        self.requests.append(request)
        for root in (".opencode", ".cyxcode"):
            path = snapshot.root / root
            path.mkdir(exist_ok=True)
            (path / "runtime.json").write_text("runtime\n", encoding="utf-8")
        if self.result.status == "ok":
            (snapshot.root / "generated.txt").write_text(
                "generated\n",
                encoding="utf-8",
            )
        return self.result


class CanonicalPatchExtractor:
    def __init__(self):
        self.calls = 0
        self.identity = identify_container_executable(
            "python",
            "/usr/local/bin/python",
            IMAGE_DIGEST,
        )

    def extract(self, snapshot, store):
        self.calls += 1
        encoded = _build_patch_record(
            snapshot.source_root,
            snapshot.root,
            snapshot.source_digest,
            self.identity.digest,
            _runtime_digest(),
            4_194_304,
        )
        record, paths = _validate_record(
            encoded,
            snapshot.source_digest,
            self.identity.digest,
            _runtime_digest(),
        )
        artifact = store.store_bytes("patch", encoded)
        return PatchExtraction(
            artifact,
            record["source_digest"],
            record["result_digest"],
            paths,
            "observation-fixture",
            ("evidence-fixture",),
            "sha256:" + "4" * 64,
            "stdout-fixture",
            "stderr-fixture",
        )


class PassingVerifier:
    def verify(self, proposal, snapshot, ledger, store):
        return VerificationReport(
            (
                Evidence(
                    "evidence-scope",
                    "scope.paths",
                    proposal.request.revision,
                    True,
                    "rule",
                ),
                Evidence(
                    "evidence-tests",
                    "tests.regression",
                    proposal.request.revision,
                    True,
                    "tool",
                ),
            )
        )


class CyxCodeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(dir=Path(__file__).parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "seed.txt").write_text("source\n", encoding="utf-8")
        for root in (".opencode", ".cyxcode"):
            path = self.source / root
            path.mkdir()
            (path / "config.json").write_text(f"{root}\n", encoding="utf-8")
        self.stager = SnapshotStager(self.root / "staging")
        self.store = ArtifactStore(self.root / "artifacts")

    def request(self, snapshot):
        contract = task_contract_from_record(task_record())
        contract = replace(
            contract,
            repository=RepositorySnapshot(
                contract.repository.source,
                contract.repository.revision,
                snapshot.source_digest,
            ),
        )
        return GenerationRequest(
            contract,
            contract.repository.revision,
            snapshot.source_digest,
            1,
        )

    def generator(self, result):
        executor = FixtureExecutor(result)
        extractor = CanonicalPatchExtractor()
        return (
            CyxCodeGenerator("cyxcode:2.3.8:fixture/model", executor, extractor),
            executor,
            extractor,
        )

    def test_maps_execution_to_repeatable_proposal_without_runtime_metadata(self):
        generator, executor, extractor = self.generator(execution())
        proposals = []
        patches = []
        for _ in range(2):
            with self.stager.stage(self.source) as snapshot:
                request = self.request(snapshot)
                proposal = generator.propose(request, snapshot, self.store)
                validated = validate_proposal(
                    request,
                    proposal,
                    snapshot,
                    self.store,
                    generator.generator_id,
                )
                proposals.append(proposal)
                patches.append(
                    (self.store.root / validated.patch_artifact.path).read_bytes()
                )
                self.assertEqual(validated.changed_paths, ("generated.txt",))
                for root in (".opencode", ".cyxcode"):
                    self.assertFalse((snapshot.root / root / "runtime.json").exists())
                    self.assertEqual(
                        (snapshot.root / root / "config.json").read_text("utf-8"),
                        f"{root}\n",
                    )

        self.assertEqual(len(executor.requests), 2)
        self.assertEqual(extractor.calls, 2)
        self.assertEqual(proposals[0].id, proposals[1].id)
        self.assertEqual(patches[0], patches[1])

    def test_failed_execution_preserves_response_artifact_in_run_record(self):
        generator, _, extractor = self.generator(
            execution("failed", "fixture provider failed")
        )
        with self.stager.stage(self.source) as snapshot:
            request = self.request(snapshot)
            metadata = RunMetadata(
                run_id="run-cyxcode-failure",
                condition="sheath_stage0",
                generator_id=generator.generator_id,
                runner_revision="runner-r1",
                environment_digest="sha256:" + "5" * 64,
                policy_digest="sha256:" + "6" * 64,
                supervisor_id="sheath-stage0-0.1.0",
            )
            with self.assertRaises(CoordinatorError) as context:
                run_single_attempt(
                    request.contract,
                    generator,
                    PassingVerifier(),
                    snapshot,
                    self.store,
                    metadata,
                    RunBudget(1, 30),
                )

            record = context.exception.record
            self.assertIsNotNone(record)
            self.assertEqual(record["schema_version"], "1.7.0")
            self.assertEqual(record["decision"]["verdict"], "failed")
            self.assertEqual(
                record["decision"]["reason_codes"],
                ["coordinator.generator_error"],
            )
            self.assertEqual([item["kind"] for item in record["artifacts"]], ["response"])
            self.assertEqual(extractor.calls, 0)
            for root in (".opencode", ".cyxcode"):
                self.assertFalse((snapshot.root / root / "runtime.json").exists())

    def test_successful_execution_exports_proposal_and_artifacts(self):
        generator, _, _ = self.generator(execution())
        with self.stager.stage(self.source) as snapshot:
            request = self.request(snapshot)
            result = run_single_attempt(
                request.contract,
                generator,
                PassingVerifier(),
                snapshot,
                self.store,
                RunMetadata(
                    run_id="run-cyxcode-success",
                    condition="sheath_stage0",
                    generator_id=generator.generator_id,
                    runner_revision="runner-r1",
                    environment_digest="sha256:" + "5" * 64,
                    policy_digest="sha256:" + "6" * 64,
                    supervisor_id="sheath-stage0-0.1.0",
                ),
                RunBudget(1, 30),
            )

        self.assertEqual(result.record["schema_version"], "1.7.0")
        self.assertEqual(result.record["decision"]["verdict"], "accept")
        self.assertEqual(len(result.record["proposals"]), 1)
        self.assertEqual(
            [item["kind"] for item in result.record["artifacts"]],
            ["patch", "response"],
        )
        self.assertEqual(
            result.record["attempt_contexts"][0]["proposal_id"],
            result.proposal.proposal.id,
        )

    def test_subprocess_executor_preserves_canonical_model_input(self):
        bridge = Path(__file__).parent / "fixtures" / "cyxcode_bridge.py"
        executable_digest = "sha256:" + "8" * 64
        executor = SubprocessCyxCodeExecutor(
            (sys.executable, str(bridge)),
            (sys.executable, "-c", "pass"),
            self.root / "isolation",
            "fixture/model",
            {"provider": {"fixture": {"apiKey": "do-not-export"}}},
            executable_digest,
            timeout_seconds=10,
        )
        generator = CyxCodeGenerator(
            "cyxcode:fixture-bridge",
            executor,
            CanonicalPatchExtractor(),
        )
        with self.stager.stage(self.source) as snapshot:
            request = self.request(snapshot)
            proposal = generator.propose(request, snapshot, self.store)
            validated = validate_proposal(
                request,
                proposal,
                snapshot,
                self.store,
                generator.generator_id,
            )
            response = json.loads(
                (self.store.root / validated.response_artifact.path).read_bytes()
            )

        self.assertEqual(validated.changed_paths, ("generated.txt",))
        self.assertEqual(
            response["request"]["prompt"].encode("utf-8"),
            build_cyxcode_prompt(request),
        )
        self.assertEqual(
            response["request"]["config"]["provider"]["fixture"]["apiKey"],
            "<redacted>",
        )
        self.assertNotIn("do-not-export", json.dumps(response))
        self.assertEqual(response["request"]["executable_digest"], executable_digest)

    def test_rejects_noncanonical_or_inconsistent_execution_envelopes(self):
        with self.assertRaisesRegex(GeneratorError, "canonical"):
            CyxCodeExecution(
                "ok",
                b'{"status": "ok"}\n',
                "sha256:" + "2" * 64,
                "sha256:" + "3" * 64,
            )
        with self.assertRaisesRegex(GeneratorError, "failure reason"):
            execution("failed")


if __name__ == "__main__":
    unittest.main()
