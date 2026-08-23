from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from sheath import (
    ArtifactStore,
    CommandAction,
    CommandPolicy,
    ConstrainedRunner,
    EvidenceLedger,
    RunnerError,
    SandboxProfile,
    SandboxRequest,
    SandboxResult,
    ToolSession,
    digest_bytes,
    identify_executable,
)


ENVIRONMENT_DIGEST = digest_bytes(b"isolated-fixture-environment")


def profile(**changes) -> SandboxProfile:
    values = {
        "backend_id": "fixture-isolator",
        "backend_version": "1",
        "environment_digest": ENVIRONMENT_DIGEST,
        "filesystem_isolated": True,
        "network_disabled": True,
        "process_isolated": True,
        "resource_limits_enforced": True,
        "executable_identity_enforced": True,
    }
    values.update(changes)
    return SandboxProfile(**values)


class FakeBackend:
    def __init__(self, sandbox_profile: SandboxProfile) -> None:
        self._profile = sandbox_profile
        self.requests: list[SandboxRequest] = []
        self.stdout = b"tests passed\n"
        self.stderr = b""
        self.exit_code: int | None = 0
        self.timed_out = False
        self.stdout_truncated = False
        self.stderr_truncated = False
        self.result_digest: str | None = None

    @property
    def profile(self) -> SandboxProfile:
        return self._profile

    def execute(self, request: SandboxRequest) -> SandboxResult:
        self.requests.append(request)
        return SandboxResult(
            action_id=request.action_id,
            sandbox_digest=self.result_digest or self._profile.digest,
            started_at="2026-08-14T00:10:00Z",
            ended_at="2026-08-14T00:10:01Z",
            exit_code=self.exit_code,
            timed_out=self.timed_out,
            stdout=self.stdout,
            stderr=self.stderr,
            stdout_truncated=self.stdout_truncated,
            stderr_truncated=self.stderr_truncated,
        )


class MutatingBackend(FakeBackend):
    def __init__(self, sandbox_profile: SandboxProfile, executable: Path) -> None:
        super().__init__(sandbox_profile)
        self._executable = executable

    @property
    def profile(self) -> SandboxProfile:
        self._executable.write_bytes(b"changed after authorization")
        return self._profile


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory(dir=Path(__file__).parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = ArtifactStore(self.root / "artifacts")
        self.ledger = EvidenceLedger("r1")
        self.policy = CommandPolicy(
            self.root,
            (identify_executable("python", Path(sys.executable)),),
            max_timeout_seconds=30,
            max_output_bytes=64,
        )
        self.session = ToolSession(self.policy, self.ledger, self.store)
        self.backend = FakeBackend(profile())
        self.runner = ConstrainedRunner(self.session, self.backend)

    def action(self, **changes) -> CommandAction:
        values = {
            "id": "action-tests",
            "argv": ("python", "-m", "unittest"),
            "working_directory": ".",
            "timeout_seconds": 10,
            "max_output_bytes": 32,
        }
        values.update(changes)
        return CommandAction(**values)

    def test_dispatches_absolute_identity_and_records_artifacts(self) -> None:
        outcome = self.runner.execute(self.action(), ("tests.regression",))

        request = self.backend.requests[0]
        self.assertEqual(request.argv[0], str(Path(sys.executable).resolve()))
        self.assertEqual(request.executable_digest, self.session.executables[0].digest)
        self.assertEqual(request.environment_digest, ENVIRONMENT_DIGEST)
        self.assertTrue(outcome.authorization.allowed)
        self.assertTrue(outcome.evidence[0].passed)
        self.assertIsNotNone(outcome.observation)
        assert outcome.observation is not None
        stdout = self.store.get(outcome.observation.stdout_artifact_id)
        self.assertEqual((self.store.root / stdout.path).read_bytes(), b"tests passed\n")

    def test_blocked_action_never_reaches_backend(self) -> None:
        outcome = self.runner.execute(
            self.action(argv=("unapproved",)),
            ("tests.regression",),
        )

        self.assertFalse(outcome.authorization.allowed)
        self.assertIsNone(outcome.observation)
        self.assertEqual(outcome.evidence, ())
        self.assertEqual(self.backend.requests, [])

    def test_invalid_check_contract_fails_before_authorization(self) -> None:
        with self.assertRaisesRegex(RunnerError, "non-empty tuple"):
            self.runner.execute(self.action(), ())

        self.assertEqual(self.backend.requests, [])
        self.assertEqual(self.session.actions, ())

    def test_incomplete_isolation_fails_before_dispatch(self) -> None:
        backend = FakeBackend(profile(network_disabled=False))
        runner = ConstrainedRunner(self.session, backend)

        with self.assertRaisesRegex(RunnerError, "required isolation"):
            runner.execute(self.action(), ("tests.regression",))

        self.assertEqual(backend.requests, [])
        self.assertEqual(self.ledger.evidence_for("tests.regression"), ())
        self.assertEqual(self.ledger.events[-1].kind, "error")
        self.assertEqual(
            self.ledger.events[-1].status,
            "sandbox.isolation_unavailable",
        )

    def test_executable_is_revalidated_immediately_before_dispatch(self) -> None:
        executable = self.root / "runner.bin"
        executable.write_bytes(b"trusted executable")
        identity = identify_executable("runner", executable)
        session = ToolSession(
            CommandPolicy(self.root, (identity,), 30, 64),
            EvidenceLedger("r1"),
            self.store,
        )
        backend = MutatingBackend(profile(), executable)
        runner = ConstrainedRunner(session, backend)

        with self.assertRaisesRegex(RunnerError, "changed before sandbox dispatch"):
            runner.execute(
                self.action(argv=("runner",)),
                ("tests.regression",),
            )

        self.assertEqual(backend.requests, [])

    def test_backend_cannot_return_more_than_output_limit(self) -> None:
        self.backend.stdout = b"x" * 33

        with self.assertRaisesRegex(RunnerError, "output byte limit"):
            self.runner.execute(self.action(), ("tests.regression",))

        self.assertEqual(self.ledger.evidence_for("tests.regression"), ())
        self.assertEqual(self.ledger.events[-1].status, "sandbox.invalid_result")

    def test_truncated_output_is_recorded_as_failed_evidence(self) -> None:
        self.backend.stdout_truncated = True

        outcome = self.runner.execute(self.action(), ("tests.regression",))

        self.assertFalse(outcome.evidence[0].passed)
        assert outcome.observation is not None
        self.assertTrue(outcome.observation.stdout_truncated)

    def test_timeout_is_recorded_as_failed_evidence(self) -> None:
        self.backend.exit_code = None
        self.backend.timed_out = True

        outcome = self.runner.execute(self.action(), ("tests.regression",))

        self.assertFalse(outcome.evidence[0].passed)
        assert outcome.observation is not None
        self.assertTrue(outcome.observation.timed_out)

    def test_result_must_bind_to_declared_sandbox_profile(self) -> None:
        self.backend.result_digest = digest_bytes(b"another-profile")

        with self.assertRaisesRegex(RunnerError, "profile does not match"):
            self.runner.execute(self.action(), ("tests.regression",))

        self.assertEqual(self.ledger.evidence_for("tests.regression"), ())


if __name__ == "__main__":
    unittest.main()
