from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from sheath import (
    ArtifactStore,
    CommandAction,
    CommandPolicy,
    Evidence,
    EvidenceLedger,
    Observation,
    ToolBoundaryError,
    ToolSession,
    Verdict,
    decide,
    digest_bytes,
    identify_executable,
    task_contract_from_record,
)

from fixtures import task_record


EMPTY_DIGEST = digest_bytes(b"")
ENVIRONMENT_DIGEST = digest_bytes(b"fixture-environment")
SANDBOX_DIGEST = digest_bytes(b"fixture-sandbox")
PYTHON_IDENTITY = identify_executable("python", Path(sys.executable))


def observation(
    *,
    action_id: str = "action-tests",
    revision: str = "r1",
    exit_code: int | None = 0,
    timed_out: bool = False,
    stdout_digest: str = EMPTY_DIGEST,
    stderr_digest: str = EMPTY_DIGEST,
    stdout_artifact_id: str = "artifact:stdout:empty",
    stderr_artifact_id: str = "artifact:stderr:empty",
    stdout_truncated: bool = False,
    stderr_truncated: bool = False,
    sandbox_guarantees: tuple[str, ...] = (
        "filesystem_isolated",
        "network_disabled",
        "process_isolated",
        "resource_limits_enforced",
        "executable_identity_enforced",
    ),
) -> Observation:
    return Observation(
        id="observation-tests",
        action_id=action_id,
        revision=revision,
        started_at="2026-08-14T00:00:00Z",
        ended_at="2026-08-14T00:00:01Z",
        exit_code=exit_code,
        timed_out=timed_out,
        stdout_digest=stdout_digest,
        stderr_digest=stderr_digest,
        stdout_artifact_id=stdout_artifact_id,
        stderr_artifact_id=stderr_artifact_id,
        environment_digest=ENVIRONMENT_DIGEST,
        sandbox_id="fixture-sandbox",
        sandbox_version="1",
        sandbox_digest=SANDBOX_DIGEST,
        sandbox_guarantees=sandbox_guarantees,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
    )


class ToolPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).parent / "data"
        self.policy = CommandPolicy(
            self.root,
            (PYTHON_IDENTITY,),
            max_timeout_seconds=30,
        )

    def test_authorizes_exact_executable_inside_root(self) -> None:
        action = CommandAction("action-1", ("python", "-m", "unittest"), ".", 10)

        authorization = self.policy.authorize(action, "r1")

        self.assertTrue(authorization.allowed)
        self.assertEqual(authorization.reason_codes, ("policy.command_allowed",))
        self.assertEqual(authorization.executable_id, PYTHON_IDENTITY.id)
        self.assertEqual(authorization.resolved_working_directory, str(self.root.resolve()))

    def test_rejects_executable_not_on_exact_allowlist(self) -> None:
        action = CommandAction("action-1", ("python-wrapper",), ".", 10)

        authorization = self.policy.authorize(action, "r1")

        self.assertFalse(authorization.allowed)
        self.assertIn("policy.executable_not_allowed", authorization.reason_codes)

    def test_rejects_working_directory_outside_root(self) -> None:
        outside = self.root.parent
        action = CommandAction("action-1", ("python",), str(outside), 10)

        authorization = self.policy.authorize(action, "r1")

        self.assertFalse(authorization.allowed)
        self.assertIn("policy.cwd_outside_root", authorization.reason_codes)

    def test_rejects_missing_working_directory(self) -> None:
        action = CommandAction("action-1", ("python",), "missing", 10)

        authorization = self.policy.authorize(action, "r1")

        self.assertFalse(authorization.allowed)
        self.assertIn("policy.cwd_missing", authorization.reason_codes)

    def test_rejects_timeout_above_policy_limit(self) -> None:
        action = CommandAction("action-1", ("python",), ".", 31)

        authorization = self.policy.authorize(action, "r1")

        self.assertFalse(authorization.allowed)
        self.assertIn("policy.timeout_exceeded", authorization.reason_codes)

    def test_rejects_output_limit_above_policy_cap(self) -> None:
        action = CommandAction(
            "action-1",
            ("python",),
            ".",
            10,
            max_output_bytes=4_194_305,
        )

        authorization = self.policy.authorize(action, "r1")

        self.assertFalse(authorization.allowed)
        self.assertIn("policy.output_limit_exceeded", authorization.reason_codes)

    def test_policy_digest_is_stable(self) -> None:
        equivalent = CommandPolicy(
            self.root,
            (identify_executable("PYTHON", Path(sys.executable)),),
            max_timeout_seconds=30,
        )

        self.assertEqual(self.policy.digest, equivalent.digest)
        self.assertRegex(self.policy.digest, r"^sha256:[0-9a-f]{64}$")

    def test_rejects_executable_changed_after_identity_was_pinned(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parents[1]) as temporary:
            root = Path(temporary)
            executable = root / "runner.bin"
            executable.write_bytes(b"trusted")
            identity = identify_executable("runner", executable)
            policy = CommandPolicy(root, (identity,), max_timeout_seconds=30)
            executable.write_bytes(b"changed")

            authorization = policy.authorize(
                CommandAction("action-1", ("runner",), ".", 10),
                "r1",
            )

            self.assertFalse(authorization.allowed)
            self.assertIn(
                "policy.executable_identity_changed",
                authorization.reason_codes,
            )


class ToolSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).parent / "data"
        self.temporary = TemporaryDirectory(dir=Path(__file__).parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.store = ArtifactStore(Path(self.temporary.name) / "artifacts")
        self.stdout = self.store.store_bytes("stdout", b"")
        self.stderr = self.store.store_bytes("stderr", b"")
        self.ledger = EvidenceLedger("r1")
        self.session = ToolSession(
            CommandPolicy(
                self.root,
                (PYTHON_IDENTITY,),
                max_timeout_seconds=30,
            ),
            self.ledger,
            self.store,
        )

    def stored_observation(self, **changes) -> Observation:
        values = {
            "stdout_digest": self.stdout.digest,
            "stderr_digest": self.stderr.digest,
            "stdout_artifact_id": self.stdout.id,
            "stderr_artifact_id": self.stderr.id,
        }
        values.update(changes)
        return observation(**values)

    def test_authorized_observation_produces_current_tool_evidence(self) -> None:
        action = CommandAction(
            "action-tests",
            ("python", "-m", "unittest"),
            ".",
            10,
        )
        authorization = self.session.request_action(action)

        evidence = self.session.record_observation(
            self.stored_observation(),
            ("tests.regression",),
        )

        self.assertTrue(authorization.allowed)
        self.assertTrue(evidence[0].passed)
        self.assertEqual(evidence[0].revision, "r1")
        self.assertTrue(self.ledger.has_evidence(evidence[0].id))

    def test_blocked_action_produces_blocking_finding_not_observation(self) -> None:
        action = CommandAction("action-tests", ("unapproved",), ".", 10)
        authorization = self.session.request_action(action)

        with self.assertRaisesRegex(ToolBoundaryError, "blocked actions"):
            self.session.record_observation(
                self.stored_observation(),
                ("tests.regression",),
            )

        self.assertFalse(authorization.allowed)
        self.assertEqual(len(self.session.blocking_findings), 1)
        decision = decide(
            task_contract_from_record(task_record()),
            self.ledger,
            self.session.blocking_findings,
        )
        self.assertEqual(decision.verdict, Verdict.BLOCK)

    def test_revision_invalidates_prior_authorization(self) -> None:
        self.session.request_action(
            CommandAction("action-tests", ("python",), ".", 10)
        )
        self.ledger.record_revision("r2")

        with self.assertRaisesRegex(ToolBoundaryError, "authorization is stale"):
            self.session.record_observation(
                self.stored_observation(revision="r2"),
                ("tests.regression",),
            )

    def test_rejects_observation_for_unknown_action(self) -> None:
        with self.assertRaisesRegex(ToolBoundaryError, "unknown action"):
            self.session.record_observation(
                self.stored_observation(action_id="action-unknown"),
                ("tests.regression",),
            )

    def test_rejects_observation_for_wrong_revision(self) -> None:
        self.session.request_action(
            CommandAction("action-tests", ("python",), ".", 10)
        )

        with self.assertRaisesRegex(ToolBoundaryError, "revision is not current"):
            self.session.record_observation(
                self.stored_observation(revision="r2"),
                ("tests.regression",),
            )

    def test_timeout_produces_failed_evidence(self) -> None:
        self.session.request_action(
            CommandAction("action-tests", ("python",), ".", 10)
        )

        evidence = self.session.record_observation(
            self.stored_observation(exit_code=None, timed_out=True),
            ("tests.regression",),
        )

        self.assertFalse(evidence[0].passed)

    def test_truncated_output_produces_failed_evidence(self) -> None:
        self.session.request_action(
            CommandAction("action-tests", ("python",), ".", 10)
        )

        evidence = self.session.record_observation(
            self.stored_observation(stdout_truncated=True),
            ("tests.regression",),
        )

        self.assertFalse(evidence[0].passed)

    def test_observation_requires_artifact_store(self) -> None:
        session = ToolSession(self.session.policy, self.ledger)
        session.request_action(CommandAction("action-tests", ("python",), ".", 10))

        with self.assertRaisesRegex(ToolBoundaryError, "ArtifactStore"):
            session.record_observation(
                self.stored_observation(),
                ("tests.regression",),
            )

        self.assertEqual(self.ledger.evidence_for("tests.regression"), ())

    def test_tampered_artifact_cannot_produce_evidence(self) -> None:
        self.session.request_action(
            CommandAction("action-tests", ("python",), ".", 10)
        )
        (self.store.root / self.stdout.path).write_bytes(b"tampered")

        with self.assertRaisesRegex(ToolBoundaryError, "integrity check failed"):
            self.session.record_observation(
                self.stored_observation(),
                ("tests.regression",),
            )

        self.assertEqual(self.ledger.evidence_for("tests.regression"), ())

    def test_observation_rejects_boolean_exit_code(self) -> None:
        with self.assertRaisesRegex(ToolBoundaryError, "integer exit code"):
            observation(exit_code=True)

    def test_observation_rejects_incomplete_sandbox_guarantees(self) -> None:
        with self.assertRaisesRegex(ToolBoundaryError, "guarantees are incomplete"):
            observation(sandbox_guarantees=("filesystem_isolated",))

    def test_duplicate_action_id_is_rejected(self) -> None:
        action = CommandAction("action-tests", ("python",), ".", 10)
        self.session.request_action(action)

        with self.assertRaisesRegex(ToolBoundaryError, "duplicate action"):
            self.session.request_action(action)

    def test_observation_and_rule_evidence_can_complete_contract(self) -> None:
        contract = task_contract_from_record(task_record())
        self.ledger.record_evidence(
            Evidence("ev-scope", "scope.paths", "r1", True, "rule")
        )
        self.session.request_action(
            CommandAction("action-tests", ("python", "-m", "unittest"), ".", 10)
        )
        self.session.record_observation(
            self.stored_observation(),
            ("tests.regression",),
        )

        decision = decide(contract, self.ledger, self.session.blocking_findings)

        self.assertEqual(decision.verdict, Verdict.ACCEPT)


if __name__ == "__main__":
    unittest.main()
