from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sheath import (
    ArtifactStore,
    GenerationRequest,
    GeneratorError,
    GeneratorProposal,
    PatchApplier,
    RepositorySnapshot,
    SnapshotStager,
    identify_container_executable,
    task_contract_from_record,
    validate_proposal,
)
from sheath.patches import _build_patch_record, _runtime_digest

from fixtures import task_record


IMAGE_DIGEST = "sha256:" + "1" * 64


class FixtureGenerator:
    generator_id = "fixture-generator-1"

    def propose(self, request, snapshot, store):
        (snapshot.root / "generated.txt").write_bytes(b"generated\n")
        response = store.store_bytes("response", b"Created generated.txt\n")
        identity = identify_container_executable(
            "python",
            "/usr/local/bin/python",
            IMAGE_DIGEST,
        )
        encoded = _build_patch_record(
            snapshot.source_root,
            snapshot.root,
            snapshot.source_digest,
            identity.digest,
            _runtime_digest(),
            4_194_304,
        )
        patch = store.store_bytes("patch", encoded)
        return GeneratorProposal(
            "proposal-1",
            self.generator_id,
            request.revision,
            request.attempt,
            response.id,
            patch.id,
            ("generated.txt was created",),
        )


class GeneratorBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory(dir=Path(__file__).parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "seed.txt").write_bytes(b"original\n")
        self.stager = SnapshotStager(self.root / "staging")
        self.store = ArtifactStore(self.root / "artifacts")

    def request(self, snapshot, *, attempt=1, feedback=()):
        base = task_contract_from_record(task_record())
        contract = replace(
            base,
            repository=RepositorySnapshot(
                "fixture/repository",
                "r1",
                snapshot.source_digest,
            ),
        )
        return GenerationRequest(
            contract,
            "r1",
            snapshot.source_digest,
            attempt,
            feedback,
        )

    def fresh_snapshot(self):
        snapshot = self.stager.stage(self.source)
        self.addCleanup(snapshot.close)
        return snapshot

    def test_fixture_generator_composes_with_patch_application(self) -> None:
        generator = FixtureGenerator()
        with self.stager.stage(self.source) as generation_snapshot:
            request = self.request(generation_snapshot)
            proposal = generator.propose(
                request,
                generation_snapshot,
                self.store,
            )
            validated = validate_proposal(
                request,
                proposal,
                generation_snapshot,
                self.store,
                generator.generator_id,
            )

        application_snapshot = self.fresh_snapshot()
        application = PatchApplier().apply(
            application_snapshot,
            validated.patch_artifact,
            self.store,
        )

        self.assertEqual(validated.changed_paths, ("generated.txt",))
        self.assertEqual(application.changed_paths, validated.changed_paths)
        self.assertEqual(application.result_digest, validated.result_digest)
        self.assertEqual(
            (application_snapshot.root / "generated.txt").read_bytes(),
            b"generated\n",
        )

    def test_request_requires_matching_revision_attempt_and_tuples(self) -> None:
        snapshot = self.fresh_snapshot()
        request = self.request(snapshot, attempt=2, feedback=("add a test",))

        self.assertEqual(request.attempt, 2)
        self.assertEqual(request.feedback, ("add a test",))
        with self.assertRaisesRegex(GeneratorError, "revision"):
            GenerationRequest(request.contract, "other", request.source_digest, 1)
        with self.assertRaisesRegex(GeneratorError, "positive integer"):
            GenerationRequest(
                request.contract,
                request.revision,
                request.source_digest,
                0,
            )
        with self.assertRaisesRegex(GeneratorError, "tuple"):
            GenerationRequest(
                request.contract,
                request.revision,
                request.source_digest,
                1,
                ["invalid"],
            )
        with self.assertRaisesRegex(GeneratorError, "source digest"):
            GenerationRequest(
                replace(
                    request.contract,
                    repository=replace(
                        request.contract.repository,
                        snapshot_digest="sha256:" + "2" * 64,
                    ),
                ),
                request.revision,
                request.source_digest,
                1,
            )
        revised = GenerationRequest(
            request.contract,
            "r2",
            "sha256:" + "3" * 64,
            2,
            ("fix the failed check",),
        )
        self.assertEqual(revised.revision, "r2")

    def test_proposal_rejects_invalid_fields_and_duplicate_claims(self) -> None:
        with self.assertRaisesRegex(GeneratorError, "generator_id"):
            GeneratorProposal("proposal", "", "r1", 1, "response", "patch")
        with self.assertRaisesRegex(GeneratorError, "positive integer"):
            GeneratorProposal("proposal", "generator", "r1", True, "response", "patch")
        with self.assertRaisesRegex(GeneratorError, "unique"):
            GeneratorProposal(
                "proposal",
                "generator",
                "r1",
                1,
                "response",
                "patch",
                ("claim", "claim"),
            )

    def test_validation_rejects_mismatched_generator_revision_and_attempt(self) -> None:
        generator = FixtureGenerator()
        snapshot = self.fresh_snapshot()
        request = self.request(snapshot)
        proposal = generator.propose(request, snapshot, self.store)

        with self.assertRaisesRegex(GeneratorError, "generator identity"):
            validate_proposal(request, proposal, snapshot, self.store, "other")
        wrong_revision = replace(proposal, revision="other")
        with self.assertRaisesRegex(GeneratorError, "repository revision"):
            validate_proposal(
                request,
                wrong_revision,
                snapshot,
                self.store,
                generator.generator_id,
            )
        wrong_attempt = replace(proposal, attempt=2)
        with self.assertRaisesRegex(GeneratorError, "another attempt"):
            validate_proposal(
                request,
                wrong_attempt,
                snapshot,
                self.store,
                generator.generator_id,
            )

    def test_validation_rejects_request_source_and_workspace_mismatch(self) -> None:
        generator = FixtureGenerator()
        snapshot = self.fresh_snapshot()
        request = self.request(snapshot)
        proposal = generator.propose(request, snapshot, self.store)
        alternate_source = self.root / "alternate"
        alternate_source.mkdir()
        (alternate_source / "seed.txt").write_bytes(b"alternate\n")
        alternate_snapshot = self.stager.stage(alternate_source)
        self.addCleanup(alternate_snapshot.close)
        alternate_contract = replace(
            request.contract,
            repository=replace(
                request.contract.repository,
                snapshot_digest=alternate_snapshot.source_digest,
            ),
        )
        alternate_request = GenerationRequest(
            alternate_contract,
            request.revision,
            alternate_snapshot.source_digest,
            1,
        )

        with self.assertRaisesRegex(GeneratorError, "request source"):
            validate_proposal(
                alternate_request,
                proposal,
                snapshot,
                self.store,
                generator.generator_id,
            )
        (snapshot.root / "generated.txt").write_bytes(b"different\n")
        with self.assertRaisesRegex(GeneratorError, "workspace result"):
            validate_proposal(
                request,
                proposal,
                snapshot,
                self.store,
                generator.generator_id,
            )

    def test_validation_rejects_missing_empty_and_tampered_artifacts(self) -> None:
        generator = FixtureGenerator()
        snapshot = self.fresh_snapshot()
        request = self.request(snapshot)
        proposal = generator.propose(request, snapshot, self.store)

        missing = replace(proposal, patch_artifact_id="artifact:patch:" + "0" * 64)
        with self.assertRaisesRegex(GeneratorError, "unknown artifact"):
            validate_proposal(
                request,
                missing,
                snapshot,
                self.store,
                generator.generator_id,
            )
        empty = self.store.store_bytes("response", b"")
        with self.assertRaisesRegex(GeneratorError, "response artifact"):
            validate_proposal(
                request,
                replace(proposal, response_artifact_id=empty.id),
                snapshot,
                self.store,
                generator.generator_id,
            )
        patch = self.store.get(proposal.patch_artifact_id)
        (self.store.root / patch.path).write_bytes(b"tampered")
        with self.assertRaisesRegex(GeneratorError, "integrity check"):
            validate_proposal(
                request,
                proposal,
                snapshot,
                self.store,
                generator.generator_id,
            )


if __name__ == "__main__":
    unittest.main()
