from dataclasses import replace
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from sheath import (
    ArtifactStore,
    CommandAction,
    CommandPolicy,
    CoordinatorError,
    Evidence,
    GeneratorProposal,
    RepositorySnapshot,
    RunBudget,
    RunMetadata,
    SandboxProfile,
    SandboxRequest,
    SandboxResult,
    SnapshotStager,
    ToolBackedVerifier,
    ToolCheck,
    VerificationReport,
    Verdict,
    digest_bytes,
    identify_container_executable,
    identify_executable,
    run_record_digest,
    run_bounded_attempts,
    run_single_attempt,
    task_contract_from_record,
)
from sheath.patches import _build_patch_record, _runtime_digest

from fixtures import task_record


IMAGE_DIGEST = "sha256:" + "1" * 64
ENVIRONMENT_DIGEST = digest_bytes(b"coordinator-tool-environment")


def profile() -> SandboxProfile:
    return SandboxProfile(
        backend_id="fixture-isolator",
        backend_version="1",
        environment_digest=ENVIRONMENT_DIGEST,
        filesystem_isolated=True,
        network_disabled=True,
        process_isolated=True,
        resource_limits_enforced=True,
        executable_identity_enforced=True,
    )


class FakeBackend:
    def __init__(self) -> None:
        self._profile = profile()
        self.requests: list[SandboxRequest] = []
        self.exit_code: int | None = 0
        self.exit_codes: list[int | None] = []
        self.fail = False
        self.mutate_workspace = False

    @property
    def profile(self) -> SandboxProfile:
        return self._profile

    def execute(self, request: SandboxRequest) -> SandboxResult:
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("fixture backend failure")
        if self.mutate_workspace:
            (Path(request.working_directory) / "verification.tmp").write_bytes(b"drift")
        exit_code = self.exit_codes.pop(0) if self.exit_codes else self.exit_code
        return SandboxResult(
            action_id=request.action_id,
            sandbox_digest=self._profile.digest,
            started_at="2026-08-14T01:00:10Z",
            ended_at="2026-08-14T01:00:11Z",
            exit_code=exit_code,
            timed_out=False,
            stdout=b"tests passed\n" if exit_code == 0 else b"",
            stderr=b"" if exit_code == 0 else b"tests failed\n",
            stdout_truncated=False,
            stderr_truncated=False,
        )


class FixtureGenerator:
    generator_id = "fixture-generator-1"

    def generated_bytes(self, request):
        return b"generated\n"

    def propose(self, request, snapshot, store):
        (snapshot.root / "generated.txt").write_bytes(self.generated_bytes(request))
        response = store.store_bytes("response", b"Created generated.txt\n")
        identity = identify_container_executable(
            "python",
            "/usr/local/bin/python",
            IMAGE_DIGEST,
        )
        patch = store.store_bytes(
            "patch",
            _build_patch_record(
                snapshot.source_root,
                snapshot.root,
                snapshot.source_digest,
                identity.digest,
                _runtime_digest(),
                4_194_304,
            ),
        )
        return GeneratorProposal(
            f"proposal-{request.attempt}",
            self.generator_id,
            request.revision,
            request.attempt,
            response.id,
            patch.id,
            ("generated.txt was created",),
        )


class RetryGenerator(FixtureGenerator):
    def __init__(self) -> None:
        self.requests = []

    def generated_bytes(self, request):
        return f"attempt-{request.attempt}\n".encode()

    def propose(self, request, snapshot, store):
        self.requests.append(request)
        return super().propose(request, snapshot, store)


class FailSecondGenerator(RetryGenerator):
    def propose(self, request, snapshot, store):
        if request.attempt == 2:
            raise RuntimeError("fixture second-attempt failure")
        return super().propose(request, snapshot, store)


class FailingGenerator(FixtureGenerator):
    def propose(self, request, snapshot, store):
        raise RuntimeError("fixture single-attempt generator failure")


class MismatchedProposalGenerator(FixtureGenerator):
    def propose(self, request, snapshot, store):
        proposal = super().propose(request, snapshot, store)
        return replace(proposal, generator_id="another-generator")


class PassingVerifier:
    def verify(self, proposal, snapshot, ledger, store):
        revision = proposal.request.revision
        return VerificationReport(
            (
                Evidence("ev-scope", "scope.paths", revision, True, "rule"),
                Evidence("ev-tests", "tests.regression", revision, True, "tool"),
            )
        )


class IncompleteVerifier:
    def verify(self, proposal, snapshot, ledger, store):
        return VerificationReport(
            (
                Evidence(
                    "ev-scope",
                    "scope.paths",
                    proposal.request.revision,
                    True,
                    "rule",
                ),
            )
        )


class RetryVerifier:
    def verify(self, proposal, snapshot, ledger, store):
        attempt = proposal.request.attempt
        revision = proposal.request.revision
        return VerificationReport(
            (
                Evidence(
                    f"ev-scope-{attempt}",
                    "scope.paths",
                    revision,
                    True,
                    "rule",
                ),
                Evidence(
                    f"ev-tests-{attempt}",
                    "tests.regression",
                    revision,
                    attempt > 1,
                    "rule",
                ),
            )
        )


class AlwaysFailVerifier:
    def verify(self, proposal, snapshot, ledger, store):
        attempt = proposal.request.attempt
        revision = proposal.request.revision
        return VerificationReport(
            (
                Evidence(
                    f"ev-scope-{attempt}",
                    "scope.paths",
                    revision,
                    True,
                    "rule",
                ),
                Evidence(
                    f"ev-tests-{attempt}",
                    "tests.regression",
                    revision,
                    False,
                    "rule",
                ),
            )
        )


class SingleAttemptCoordinatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory(dir=Path(__file__).parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "seed.txt").write_bytes(b"original\n")
        self.stager = SnapshotStager(self.root / "staging")
        self.store = ArtifactStore(self.root / "artifacts")

    def contract(self, snapshot):
        base = task_contract_from_record(task_record())
        return replace(
            base,
            repository=RepositorySnapshot(
                base.repository.source,
                base.repository.revision,
                snapshot.source_digest,
            ),
        )

    def metadata(self):
        return RunMetadata(
            run_id="run-coordinator-1",
            condition="sheath_stage0",
            generator_id="fixture-generator-1",
            runner_revision="runner-r1",
            environment_digest="sha256:environment",
            policy_digest="sha256:policy",
            supervisor_id="sheath-stage0-0.1.0",
        )

    def run_attempt(self, verifier, *, generator=None, budget_seconds=10, timer=None):
        ticks = iter(f"2026-08-14T01:00:{second:02d}Z" for second in range(30))
        times = iter((10.0, 10.5)) if timer is None else timer
        with self.stager.stage(self.source) as snapshot:
            return run_single_attempt(
                self.contract(snapshot),
                generator or FixtureGenerator(),
                verifier,
                snapshot,
                self.store,
                self.metadata(),
                RunBudget(max_attempts=1, max_wall_seconds=budget_seconds),
                clock=lambda: next(ticks),
                timer=lambda: next(times),
            )

    def run_tool_attempt(
        self,
        *,
        argv=("python", "-m", "unittest"),
        exit_code=0,
        backend_failure=False,
        mutate_workspace=False,
        use_source_policy_root=False,
    ):
        ticks = iter(f"2026-08-14T01:01:{second:02d}Z" for second in range(30))
        times = iter((20.0, 20.5))
        backend = FakeBackend()
        backend.exit_code = exit_code
        backend.fail = backend_failure
        backend.mutate_workspace = mutate_workspace
        with self.stager.stage(self.source) as snapshot:
            policy = CommandPolicy(
                self.source if use_source_policy_root else snapshot.root,
                (identify_executable("python", Path(sys.executable)),),
                max_timeout_seconds=30,
                max_output_bytes=64,
            )
            verifier = ToolBackedVerifier(
                policy,
                backend,
                (
                    ToolCheck(
                        CommandAction(
                            "action-tests",
                            argv,
                            ".",
                            10,
                            32,
                        ),
                        ("tests.regression",),
                    ),
                ),
            )
            contract = replace(
                self.contract(snapshot),
                required_checks=("tests.regression",),
            )
            metadata = replace(
                self.metadata(),
                environment_digest=ENVIRONMENT_DIGEST,
                policy_digest=policy.digest,
            )
            result = run_single_attempt(
                contract,
                FixtureGenerator(),
                verifier,
                snapshot,
                self.store,
                metadata,
                RunBudget(max_attempts=1, max_wall_seconds=10),
                clock=lambda: next(ticks),
                timer=lambda: next(times),
            )
        return result, backend

    def run_bounded(self, generator, verifier, *, max_attempts=2, timer=None):
        ticks = iter(f"2026-08-14T01:02:{second:02d}Z" for second in range(80))
        times = iter((30.0, 30.5, 31.0)) if timer is None else timer
        with self.stager.stage(self.source) as snapshot:
            return run_bounded_attempts(
                self.contract(snapshot),
                generator,
                verifier,
                snapshot,
                self.stager,
                self.store,
                self.metadata(),
                RunBudget(max_attempts=max_attempts, max_wall_seconds=10),
                clock=lambda: next(ticks),
                timer=lambda: next(times),
            )

    def test_exports_one_accepted_attempt_with_complete_provenance(self) -> None:
        result = self.run_attempt(PassingVerifier())
        record = result.record

        self.assertEqual(result.decision.verdict, Verdict.ACCEPT)
        self.assertEqual(result.digest, run_record_digest(record))
        self.assertEqual(record["schema_version"], "1.7.0")
        self.assertEqual(record["metrics"]["attempts"], 1)
        self.assertTrue(record["metrics"]["verified_success"])
        self.assertEqual(len(record["proposals"]), 1)
        self.assertEqual(
            [event["kind"] for event in record["events"]].count("proposal"),
            1,
        )
        self.assertEqual(
            {item["kind"] for item in record["artifacts"]},
            {"patch", "response"},
        )
        self.assertEqual((self.source / "seed.txt").read_bytes(), b"original\n")
        self.assertFalse((self.source / "generated.txt").exists())

    def test_exports_revision_verdict_when_single_attempt_is_exhausted(self) -> None:
        result = self.run_attempt(IncompleteVerifier())

        self.assertEqual(result.decision.verdict, Verdict.REVISE)
        self.assertFalse(result.record["metrics"]["verified_success"])
        self.assertIn(
            "mandatory_check.missing:tests.regression",
            result.record["decision"]["reason_codes"],
        )
        final_event = result.record["events"][-1]
        self.assertEqual(final_event["from_state"], "revision_required")
        self.assertEqual(final_event["to_state"], "exported")

    def test_escalates_and_records_a_wall_time_budget_overrun(self) -> None:
        result = self.run_attempt(
            PassingVerifier(),
            budget_seconds=1,
            timer=iter((10.0, 12.0)),
        )

        self.assertEqual(result.decision.verdict, Verdict.ESCALATE)
        self.assertEqual(
            result.record["protocol_deviations"],
            ["budget.max_wall_seconds exceeded"],
        )
        self.assertEqual(
            result.record["findings"][0]["id"],
            "coordinator-wall-time-exceeded",
        )

    def test_rejects_a_proposal_from_another_generator(self) -> None:
        with self.assertRaisesRegex(CoordinatorError, "generator identity"):
            self.run_attempt(
                PassingVerifier(),
                generator=MismatchedProposalGenerator(),
            )

        self.assertEqual((self.source / "seed.txt").read_bytes(), b"original\n")
        self.assertFalse((self.source / "generated.txt").exists())

    def test_rejects_a_multi_attempt_budget(self) -> None:
        with self.stager.stage(self.source) as snapshot:
            with self.assertRaisesRegex(CoordinatorError, "requires max_attempts=1"):
                run_single_attempt(
                    self.contract(snapshot),
                    FixtureGenerator(),
                    PassingVerifier(),
                    snapshot,
                    self.store,
                    self.metadata(),
                    RunBudget(max_attempts=2, max_wall_seconds=10),
                )

    def test_tool_verifier_exports_observation_evidence_and_artifacts(self) -> None:
        result, backend = self.run_tool_attempt()

        self.assertEqual(result.decision.verdict, Verdict.ACCEPT)
        self.assertEqual(len(backend.requests), 1)
        self.assertEqual(len(result.record["actions"]), 1)
        self.assertEqual(len(result.record["observations"]), 1)
        self.assertEqual(
            {item["kind"] for item in result.record["artifacts"]},
            {"patch", "response", "stderr", "stdout"},
        )
        tool_evidence = next(
            item
            for item in result.record["evidence"]
            if item["check_id"] == "tests.regression"
        )
        self.assertTrue(tool_evidence["passed"])

    def test_tool_verifier_turns_nonzero_exit_into_revision_evidence(self) -> None:
        result, _ = self.run_tool_attempt(exit_code=1)

        self.assertEqual(result.decision.verdict, Verdict.REVISE)
        self.assertIn(
            "mandatory_check.failed:tests.regression",
            result.record["decision"]["reason_codes"],
        )

    def test_tool_verifier_preserves_blocked_action_as_hard_block(self) -> None:
        result, backend = self.run_tool_attempt(argv=("unapproved",))

        self.assertEqual(result.decision.verdict, Verdict.BLOCK)
        self.assertEqual(backend.requests, [])
        self.assertEqual(result.record["findings"][0]["category"], "unsafe_action")

    def test_tool_verifier_turns_runner_failure_into_escalation(self) -> None:
        result, _ = self.run_tool_attempt(backend_failure=True)

        self.assertEqual(result.decision.verdict, Verdict.ESCALATE)
        self.assertEqual(
            result.record["findings"][0]["id"],
            "finding:runner:action-tests",
        )
        self.assertTrue(
            any(
                event["kind"] == "error"
                and event["status"] == "sandbox.backend_failure"
                for event in result.record["events"]
            )
        )

    def test_tool_verifier_rebinds_policy_to_the_proposal_workspace(self) -> None:
        result, backend = self.run_tool_attempt(use_source_policy_root=True)

        self.assertEqual(result.decision.verdict, Verdict.ACCEPT)
        context = result.record["attempt_contexts"][0]
        self.assertEqual(context["action_ids"], ["action-tests"])
        self.assertNotEqual(
            context["policy_digest"],
            result.record["system"]["policy_digest"],
        )
        self.assertNotEqual(backend.requests[0].working_directory, str(self.source))

    def test_tool_verifier_escalates_workspace_drift(self) -> None:
        result, _ = self.run_tool_attempt(mutate_workspace=True)

        self.assertEqual(result.decision.verdict, Verdict.ESCALATE)
        self.assertIn(
            "verification changed the proposal workspace",
            result.record["protocol_deviations"],
        )
        self.assertTrue(
            any(
                item["id"] == "coordinator-verification-workspace-drift"
                for item in result.record["findings"]
            )
        )

    def test_single_attempt_exports_failed_record_on_generator_failure(self) -> None:
        with self.assertRaises(CoordinatorError) as context:
            self.run_attempt(PassingVerifier(), generator=FailingGenerator())

        error = context.exception
        self.assertIsNotNone(error.record)
        self.assertEqual(error.record["decision"]["verdict"], "failed")
        self.assertEqual(
            error.record["decision"]["reason_codes"],
            ["coordinator.generator_error"],
        )
        self.assertEqual(
            error.record["protocol_deviations"],
            ["coordinator.generator_error"],
        )
        self.assertEqual(error.record["metrics"]["attempts"], 0)

    def test_bounded_retry_revises_then_accepts_a_fresh_revision(self) -> None:
        generator = RetryGenerator()
        result = self.run_bounded(generator, RetryVerifier())

        self.assertEqual(result.decision.verdict, Verdict.ACCEPT)
        self.assertEqual(len(result.proposals), 2)
        self.assertEqual(result.record["metrics"]["attempts"], 2)
        self.assertEqual(
            generator.requests[1].feedback,
            ("mandatory_check.failed:tests.regression",),
        )
        self.assertTrue(generator.requests[1].revision.startswith("attempt-2:sha256:"))
        self.assertEqual(
            generator.requests[1].source_digest,
            result.proposals[0].result_digest,
        )
        self.assertEqual(
            [item["attempt"] for item in result.record["proposals"]],
            [1, 2],
        )
        self.assertEqual(list(self.stager.root.iterdir()), [])

    def test_bounded_retry_exports_revision_when_budget_is_exhausted(self) -> None:
        result = self.run_bounded(RetryGenerator(), AlwaysFailVerifier())

        self.assertEqual(result.decision.verdict, Verdict.REVISE)
        self.assertEqual(len(result.proposals), 2)
        self.assertFalse(result.record["metrics"]["verified_success"])
        self.assertEqual(
            result.record["events"][-1]["from_state"],
            "revision_required",
        )

    def test_bounded_retry_stops_after_early_acceptance(self) -> None:
        result = self.run_bounded(
            RetryGenerator(),
            PassingVerifier(),
            max_attempts=3,
        )

        self.assertEqual(result.decision.verdict, Verdict.ACCEPT)
        self.assertEqual(len(result.proposals), 1)
        self.assertEqual(result.record["metrics"]["attempts"], 1)

    def test_bounded_retry_exports_each_tool_session_by_attempt(self) -> None:
        ticks = iter(f"2026-08-14T01:03:{second:02d}Z" for second in range(40))
        times = iter((40.0, 40.5, 41.0))
        backends = []

        def backend_factory(active_snapshot):
            backend = FakeBackend()
            backend.exit_code = 1 if not backends else 0
            backends.append((active_snapshot.root, backend))
            return backend

        with self.stager.stage(self.source) as snapshot:
            policy = CommandPolicy(
                snapshot.root,
                (identify_executable("python", Path(sys.executable)),),
                30,
                64,
            )
            verifier = ToolBackedVerifier(
                policy,
                backend_factory,
                (
                    ToolCheck(
                        CommandAction("action-tests", ("python",), ".", 10, 32),
                        ("tests.regression",),
                    ),
                ),
            )
            contract = replace(
                self.contract(snapshot),
                required_checks=("tests.regression",),
            )
            metadata = replace(
                self.metadata(),
                environment_digest=ENVIRONMENT_DIGEST,
                policy_digest=policy.digest,
            )
            result = run_bounded_attempts(
                contract,
                RetryGenerator(),
                verifier,
                snapshot,
                self.stager,
                self.store,
                metadata,
                RunBudget(max_attempts=2, max_wall_seconds=10),
                clock=lambda: next(ticks),
                timer=lambda: next(times),
            )
        self.assertEqual(result.decision.verdict, Verdict.ACCEPT)
        self.assertEqual(len(backends), 2)
        self.assertNotEqual(backends[0][0], backends[1][0])
        self.assertEqual([len(item[1].requests) for item in backends], [1, 1])
        self.assertEqual(
            [item["attempt"] for item in result.record["attempt_contexts"]],
            [1, 2],
        )
        self.assertEqual(
            [item["action_ids"] for item in result.record["attempt_contexts"]],
            [["action-tests"], ["action-tests:attempt-2"]],
        )
        self.assertEqual(
            [
                item["environment_digests"]
                for item in result.record["attempt_contexts"]
            ],
            [[ENVIRONMENT_DIGEST], [ENVIRONMENT_DIGEST]],
        )
        self.assertNotEqual(
            result.record["attempt_contexts"][0]["policy_digest"],
            result.record["attempt_contexts"][1]["policy_digest"],
        )
        self.assertEqual(list(self.stager.root.iterdir()), [])

    def test_bounded_retry_cleans_snapshot_after_generator_failure(self) -> None:
        with self.assertRaises(CoordinatorError) as context:
            self.run_bounded(FailSecondGenerator(), RetryVerifier())

        error = context.exception
        self.assertIsNotNone(error.record)
        self.assertEqual(error.record["decision"]["verdict"], "failed")
        self.assertIn("coordinator.generator_error", error.record["protocol_deviations"])
        self.assertEqual(error.record["metrics"]["attempts"], 1)
        self.assertEqual(error.record["attempt_contexts"][0]["attempt"], 1)
        self.assertEqual(list(self.stager.root.iterdir()), [])

    def test_bounded_retry_rejects_foreign_stager_before_generation(self) -> None:
        generator = RetryGenerator()
        foreign_stager = SnapshotStager(self.root / "foreign-staging")
        with self.stager.stage(self.source) as snapshot:
            with self.assertRaisesRegex(CoordinatorError, "own the initial snapshot"):
                run_bounded_attempts(
                    self.contract(snapshot),
                    generator,
                    RetryVerifier(),
                    snapshot,
                    foreign_stager,
                    self.store,
                    self.metadata(),
                    RunBudget(max_attempts=2, max_wall_seconds=10),
                )

        self.assertEqual(generator.requests, [])


if __name__ == "__main__":
    unittest.main()
