from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).parents[2] / "sheath" / "src"))

from sheath import (
    ArtifactStore,
    CommandPolicy,
    EvidenceLedger,
    GenerationRequest,
    GeneratorProposal,
    SandboxProfile,
    SandboxResult,
    SnapshotStager,
    ValidatedProposal,
    build_cyxcode_prompt,
    digest_bytes,
    identify_container_executable,
)

from phase6_minimum_poc import (
    MinimumPocError,
    PocVerifier,
    build_contract,
    curate_run,
    load_tasks,
)


TASKS = Path(__file__).parent / "poc_tasks" / "manifest.json"
IMAGE_DIGEST = "sha256:" + "1" * 64
ENVIRONMENT_DIGEST = digest_bytes(b"phase6-minimum-poc-fixture")


class FakeBackend:
    def __init__(self, exit_codes: list[int]) -> None:
        self.exit_codes = exit_codes
        self.requests = []
        self._profile = SandboxProfile(
            backend_id="poc-fixture",
            backend_version="1",
            environment_digest=ENVIRONMENT_DIGEST,
            filesystem_isolated=True,
            network_disabled=True,
            process_isolated=True,
            resource_limits_enforced=True,
            executable_identity_enforced=True,
        )

    @property
    def profile(self):
        return self._profile

    def execute(self, request):
        self.requests.append(request)
        exit_code = self.exit_codes.pop(0)
        return SandboxResult(
            action_id=request.action_id,
            sandbox_digest=self.profile.digest,
            started_at="2026-09-01T20:00:00Z",
            ended_at="2026-09-01T20:00:01Z",
            exit_code=exit_code,
            timed_out=False,
            stdout=b"ok\n" if exit_code == 0 else b"",
            stderr=b"" if exit_code == 0 else b"failed\n",
            stdout_truncated=False,
            stderr_truncated=False,
        )


class MinimumPocTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tasks = load_tasks(TASKS)

    def test_frozen_inventory_and_order(self) -> None:
        self.assertEqual(3, len(self.tasks))
        self.assertEqual(("A", "D0"), self.tasks[0].condition_order)
        self.assertEqual(("D0", "A"), self.tasks[1].condition_order)
        self.assertEqual(("A", "D0"), self.tasks[2].condition_order)
        self.assertTrue(all(not (task.source_root / "hidden_tests.py").exists() for task in self.tasks))

    def test_source_digest_drift_is_rejected(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parent) as name:
            copied = Path(name) / "poc_tasks"
            shutil.copytree(TASKS.parent, copied)
            target = copied / self.tasks[0].directory / "source" / "ranges.py"
            target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(MinimumPocError, "source digest drift"):
                load_tasks(copied / "manifest.json")

    def test_model_prompt_excludes_hidden_source(self) -> None:
        task = self.tasks[0]
        with TemporaryDirectory(dir=Path(__file__).parent) as name:
            stager = SnapshotStager(Path(name) / "staging")
            with stager.stage(task.source_root) as snapshot:
                contract = build_contract(task, snapshot.source_digest)
                prompt = build_cyxcode_prompt(
                    GenerationRequest(contract, contract.repository.revision, snapshot.source_digest, 1)
                ).decode("utf-8")
        self.assertNotIn("RangeMergeHiddenTests", prompt)
        self.assertNotIn(task.hidden_script, prompt)
        self.assertIn(task.request, prompt)

    def _verify(self, changed_paths=("ranges.py",), exit_codes=None):
        task = self.tasks[0]
        temporary = TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        stager = SnapshotStager(root / "staging")
        snapshot = stager.stage(task.source_root)
        self.addCleanup(snapshot.close)
        contract = build_contract(task, snapshot.source_digest)
        request = GenerationRequest(contract, contract.repository.revision, snapshot.source_digest, 1)
        store = ArtifactStore(root / "artifacts")
        response = store.store_bytes("response", b"fixture response")
        patch = store.store_bytes("patch", b"fixture patch")
        proposal_record = GeneratorProposal(
            "proposal-poc-fixture",
            "fixture-generator",
            request.revision,
            1,
            response.id,
            patch.id,
        )
        proposal = ValidatedProposal(request, proposal_record, response, patch, snapshot.source_digest, changed_paths)
        identity = identify_container_executable("python", "/usr/local/bin/python", IMAGE_DIGEST)
        policy = CommandPolicy(snapshot.root, (identity,), max_timeout_seconds=30, max_output_bytes=65_536)
        backend = FakeBackend([0, 1] if exit_codes is None else exit_codes)
        ledger = EvidenceLedger(request.revision)
        report = PocVerifier(task, policy, backend).verify(proposal, snapshot, ledger, store)
        return task, report, backend, ledger

    def test_verifier_runs_visible_then_hidden_without_staging_hidden_file(self) -> None:
        task, report, backend, ledger = self._verify()
        self.assertTrue(report.evidence[0].passed)
        self.assertEqual(2, len(backend.requests))
        self.assertEqual(("-m", "unittest", "-v"), backend.requests[0].argv[1:])
        self.assertEqual("-c", backend.requests[1].argv[1])
        self.assertEqual(task.hidden_script, backend.requests[1].argv[2])
        hidden = next(item for item in ledger.evidence if item.check_id == "tests.hidden")
        self.assertFalse(hidden.passed)

    def test_scope_rejects_an_unapproved_changed_path(self) -> None:
        _, report, _, _ = self._verify(changed_paths=("test_visible.py",), exit_codes=[0, 0])
        self.assertFalse(report.evidence[0].passed)

    def test_curated_measurement_has_no_raw_artifacts(self) -> None:
        record = {
            "metrics": {"verified_success": True, "attempts": 2, "wall_seconds": 12.5},
            "decision": {"verdict": "accept", "reason_codes": [], "summary": "must not escape"},
            "actions": [{"argv": ["python", "-c", "hidden source"]}],
        }
        curated = curate_run(record, "sha256:" + "d" * 64, "D0")
        self.assertTrue(curated["recovered_after_first_attempt"])
        encoded = json.dumps(curated)
        self.assertNotIn("hidden source", encoded)
        self.assertNotIn("must not escape", encoded)


if __name__ == "__main__":
    unittest.main()
