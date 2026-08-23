from dataclasses import replace
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from sheath import (
    ArtifactStore,
    GenerationRequest,
    GeneratorProposal,
    Evidence,
    EvidenceLedger,
    Finding,
    CommandAction,
    CommandPolicy,
    Observation,
    ToolSession,
    RunBudget,
    RunMetadata,
    RunMetrics,
    RunRecordError,
    RunState,
    RunStateMachine,
    SnapshotStager,
    Severity,
    Verdict,
    build_run_record,
    decide,
    encode_run_record,
    run_record_digest,
    digest_bytes,
    identify_executable,
    identify_container_executable,
    task_contract_from_record,
    validate_proposal,
)
from sheath.patches import _build_patch_record, _runtime_digest

from fixtures import task_record


def completed_run(contract=None, proposal=None):
    ticks = iter(f"2026-08-14T00:01:{second:02d}Z" for second in range(30))
    if contract is None:
        contract = task_contract_from_record(task_record())
    ledger = EvidenceLedger("r1", clock=lambda: next(ticks))
    machine = RunStateMachine(ledger)
    for state in (
        RunState.CONTRACTED,
        RunState.TRIAGED,
        RunState.PROPOSED,
        RunState.ACTION_VALIDATION,
        RunState.EXECUTED,
    ):
        machine.transition(state)
        if state is RunState.PROPOSED and proposal is not None:
            ledger.record_proposal(
                proposal.proposal.id,
                proposal.response_artifact.id,
            )
    ledger.record_evidence(Evidence("ev-scope", "scope.paths", "r1", True, "rule"))
    ledger.record_evidence(
        Evidence("ev-tests", "tests.regression", "r1", True, "tool")
    )
    machine.transition(RunState.ASSESSED)
    decision = decide(contract, ledger)
    machine.apply_decision(decision)
    machine.transition(RunState.EXPORTED)
    return contract, ledger, machine, decision


def completed_proposal_run(artifact_root: Path):
    parent = artifact_root.parent
    source = parent / "proposal-source"
    source.mkdir()
    (source / "seed.txt").write_bytes(b"original\n")
    stager = SnapshotStager(parent / "proposal-staging")
    store = ArtifactStore(artifact_root)
    with stager.stage(source) as snapshot:
        base = task_contract_from_record(task_record())
        contract = replace(
            base,
            repository=replace(
                base.repository,
                snapshot_digest=snapshot.source_digest,
            ),
        )
        request = GenerationRequest(
            contract,
            contract.repository.revision,
            snapshot.source_digest,
            1,
        )
        (snapshot.root / "generated.txt").write_bytes(b"generated\n")
        response = store.store_bytes("response", b"Created generated.txt\n")
        identity = identify_container_executable(
            "python",
            "/usr/local/bin/python",
            "sha256:" + "1" * 64,
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
        proposal = GeneratorProposal(
            "proposal-1",
            "fixture-generator",
            request.revision,
            1,
            response.id,
            patch.id,
            ("generated.txt was created",),
        )
        validated = validate_proposal(
            request,
            proposal,
            snapshot,
            store,
            "fixture-generator",
        )
    contract, ledger, machine, decision = completed_run(contract, validated)
    return contract, ledger, machine, decision, validated, store


def completed_tool_run(artifact_root: Path):
    ticks = iter(f"2026-08-14T00:02:{second:02d}Z" for second in range(30))
    contract = task_contract_from_record(task_record())
    ledger = EvidenceLedger("r1", clock=lambda: next(ticks))
    machine = RunStateMachine(ledger)
    for state in (
        RunState.CONTRACTED,
        RunState.TRIAGED,
        RunState.PROPOSED,
        RunState.ACTION_VALIDATION,
    ):
        machine.transition(state)
    policy = CommandPolicy(
        Path(__file__).parent / "data",
        (identify_executable("python", Path(sys.executable)),),
        30,
    )
    store = ArtifactStore(artifact_root)
    session = ToolSession(policy, ledger, store)
    session.request_action(
        CommandAction("action-tests", ("python", "-m", "unittest"), ".", 10)
    )
    machine.transition(RunState.EXECUTED)
    ledger.record_evidence(Evidence("ev-scope", "scope.paths", "r1", True, "rule"))
    stdout = store.store_bytes("stdout", b"tests passed")
    stderr = store.store_bytes("stderr", b"")
    session.record_observation(
        Observation(
            id="observation-tests",
            action_id="action-tests",
            revision="r1",
            started_at="2026-08-14T00:02:10Z",
            ended_at="2026-08-14T00:02:11Z",
            exit_code=0,
            timed_out=False,
            stdout_digest=stdout.digest,
            stderr_digest=stderr.digest,
            stdout_artifact_id=stdout.id,
            stderr_artifact_id=stderr.id,
            environment_digest=digest_bytes(b"fixture-environment"),
            sandbox_id="fixture-sandbox",
            sandbox_version="1",
            sandbox_digest=digest_bytes(b"fixture-sandbox"),
            sandbox_guarantees=(
                "filesystem_isolated",
                "network_disabled",
                "process_isolated",
                "resource_limits_enforced",
                "executable_identity_enforced",
            ),
            stdout_truncated=False,
            stderr_truncated=False,
        ),
        ("tests.regression",),
    )
    machine.transition(RunState.ASSESSED)
    decision = decide(contract, ledger, session.blocking_findings)
    machine.apply_decision(decision)
    machine.transition(RunState.EXPORTED)
    return contract, ledger, machine, decision, session, store


def completed_error_run():
    ticks = iter(f"2026-08-14T00:03:{second:02d}Z" for second in range(30))
    contract = task_contract_from_record(task_record())
    ledger = EvidenceLedger("r1", clock=lambda: next(ticks))
    machine = RunStateMachine(ledger)
    for state in (
        RunState.CONTRACTED,
        RunState.TRIAGED,
        RunState.PROPOSED,
        RunState.ACTION_VALIDATION,
    ):
        machine.transition(state)
    policy = CommandPolicy(
        Path(__file__).parent / "data",
        (identify_executable("python", Path(sys.executable)),),
        30,
    )
    session = ToolSession(policy, ledger)
    authorization = session.request_action(
        CommandAction("action-error", ("python",), ".", 10)
    )
    ledger.record_tool_error("action-error", "sandbox.isolation_unavailable")
    machine.transition(RunState.EXECUTED)
    ledger.record_evidence(Evidence("ev-scope", "scope.paths", "r1", True, "rule"))
    machine.transition(RunState.ASSESSED)
    finding = Finding(
        id="finding-sandbox-error",
        category="other",
        severity=Severity.ESCALATION,
        message="Sandbox isolation is unavailable.",
        evidence_ids=(authorization.id,),
        source="policy",
    )
    decision = decide(contract, ledger, (finding,))
    machine.apply_decision(decision)
    machine.transition(RunState.EXPORTED)
    return contract, ledger, machine, decision, session, finding


class RunRecordTests(unittest.TestCase):
    def test_exports_resolvable_canonical_run_record(self) -> None:
        contract, ledger, machine, decision = completed_run()

        record = build_run_record(
            contract,
            ledger,
            machine,
            decision,
            RunMetadata(
                run_id="run-001",
                condition="sheath_stage0",
                generator_id="fixture-generator",
                runner_revision="runner-r1",
                environment_digest="sha256:environment",
                policy_digest="sha256:policy",
                supervisor_id="sheath-stage0-0.1.0",
                seed=7,
            ),
            RunBudget(max_attempts=2, max_wall_seconds=60),
            RunMetrics(attempts=0, wall_seconds=0.5, verified_success=True),
        )

        self.assertEqual(record["schema_version"], "1.7.0")
        self.assertEqual(record["decision"]["verdict"], Verdict.ACCEPT.value)
        self.assertEqual(
            set(record["decision"]["evidence_ids"]),
            {item["id"] for item in record["evidence"]},
        )
        self.assertEqual(
            [item["sequence"] for item in record["events"]],
            list(range(len(record["events"]))),
        )
        self.assertIn("state_transition", {item["kind"] for item in record["events"]})
        self.assertEqual(record["executables"], [])
        self.assertEqual(record["actions"], [])
        self.assertEqual(record["authorizations"], [])
        self.assertEqual(record["observations"], [])
        self.assertEqual(record["attempt_contexts"], [])
        self.assertEqual(record["proposals"], [])
        self.assertEqual(json.loads(encode_run_record(record)), record)
        self.assertRegex(run_record_digest(record), r"^sha256:[0-9a-f]{64}$")

    def test_exports_failed_record_without_supervisory_decision(self) -> None:
        contract, ledger, machine, decision = completed_run()
        del decision

        record = build_run_record(
            contract,
            ledger,
            machine,
            None,
            RunMetadata(
                run_id="run-failed",
                condition="sheath_stage0",
                generator_id="fixture-generator",
                runner_revision="runner-r1",
                environment_digest="sha256:environment",
                policy_digest="sha256:policy",
                supervisor_id="sheath-stage0-0.1.0",
            ),
            RunBudget(max_attempts=2, max_wall_seconds=60),
            RunMetrics(attempts=0, wall_seconds=0.5, verified_success=False),
            protocol_deviations=("coordinator.failure",),
            failure_reason_codes=("coordinator.failure",),
            failure_summary="coordinator failure",
        )

        self.assertEqual(record["decision"]["verdict"], "failed")
        self.assertEqual(record["decision"]["reason_codes"], ["coordinator.failure"])
        self.assertEqual(record["schema_version"], "1.7.0")

    def test_encoding_and_digest_are_stable(self) -> None:
        contract, ledger, machine, decision = completed_run()
        metadata = RunMetadata(
            run_id="run-stable",
            condition="sheath_stage0",
            generator_id="fixture-generator",
            runner_revision="runner-r1",
            environment_digest="sha256:environment",
            policy_digest="sha256:policy",
            supervisor_id="sheath-stage0-0.1.0",
        )
        record = build_run_record(
            contract,
            ledger,
            machine,
            decision,
            metadata,
            RunBudget(2, 60),
            RunMetrics(0, 0.5, True),
        )

        self.assertEqual(encode_run_record(record), encode_run_record(dict(record)))
        self.assertEqual(run_record_digest(record), run_record_digest(dict(record)))

    def test_rejects_export_before_exported_state(self) -> None:
        contract = task_contract_from_record(task_record())
        ledger = EvidenceLedger("r1")
        machine = RunStateMachine(ledger)

        with self.assertRaisesRegex(RunRecordError, "must be exported"):
            build_run_record(
                contract,
                ledger,
                machine,
                decide(contract, ledger),
                RunMetadata(
                    run_id="run-invalid",
                    condition="sheath_stage0",
                    generator_id="fixture-generator",
                    runner_revision="runner-r1",
                    environment_digest="sha256:environment",
                    policy_digest="sha256:policy",
                    supervisor_id="sheath-stage0-0.1.0",
                ),
                RunBudget(1, 10),
                RunMetrics(0, 0),
            )

    def test_sheath_metadata_requires_supervisor_identity(self) -> None:
        with self.assertRaisesRegex(RunRecordError, "supervisor_id"):
            RunMetadata(
                run_id="run-no-supervisor",
                condition="sheath_stage0",
                generator_id="fixture-generator",
                runner_revision="runner-r1",
                environment_digest="sha256:environment",
                policy_digest="sha256:policy",
                supervisor_id=None,
            )

    def test_rejects_state_machine_from_another_ledger(self) -> None:
        contract, ledger, machine, decision = completed_run()
        other_ledger = EvidenceLedger("r1")

        with self.assertRaisesRegex(RunRecordError, "same ledger"):
            build_run_record(
                contract,
                other_ledger,
                machine,
                decision,
                RunMetadata(
                    run_id="run-wrong-ledger",
                    condition="sheath_stage0",
                    generator_id="fixture-generator",
                    runner_revision="runner-r1",
                    environment_digest="sha256:environment",
                    policy_digest="sha256:policy",
                    supervisor_id="sheath-stage0-0.1.0",
                ),
                RunBudget(1, 10),
                RunMetrics(0, 1, True),
            )

    def test_exports_tool_records_and_event_references(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parents[1]) as temporary:
            contract, ledger, machine, decision, session, store = completed_tool_run(
                Path(temporary) / "artifacts"
            )
            environment_digest = digest_bytes(b"fixture-environment")

            record = build_run_record(
                contract,
                ledger,
                machine,
                decision,
                RunMetadata(
                    run_id="run-tools",
                    condition="sheath_stage0",
                    generator_id="fixture-generator",
                    runner_revision="runner-r1",
                    environment_digest=environment_digest,
                    policy_digest=session.policy.digest,
                    supervisor_id="sheath-stage0-0.1.0",
                ),
                RunBudget(2, 60),
                RunMetrics(0, 0.5, True),
                findings=session.blocking_findings,
                tool_sessions=(session,),
            )

        self.assertEqual(len(record["executables"]), 1)
        self.assertEqual(record["executables"][0]["scope"], "host_file")
        self.assertIsNone(record["executables"][0]["image_digest"])
        self.assertEqual(len(record["actions"]), 1)
        self.assertEqual(len(record["authorizations"]), 1)
        self.assertEqual(len(record["observations"]), 1)
        self.assertEqual(record["authorizations"][0]["action_id"], "action-tests")
        self.assertEqual(
            record["authorizations"][0]["executable_id"],
            record["executables"][0]["id"],
        )
        self.assertEqual(record["observations"][0]["action_id"], "action-tests")
        self.assertEqual(record["observations"][0]["sandbox_id"], "fixture-sandbox")
        self.assertEqual(record["observations"][0]["sandbox_version"], "1")
        self.assertFalse(record["observations"][0]["stdout_truncated"])
        context = record["attempt_contexts"][0]
        self.assertIsNone(context["attempt"])
        self.assertIsNone(context["proposal_id"])
        self.assertEqual(context["policy_digest"], session.policy.digest)
        self.assertEqual(context["environment_digests"], [environment_digest])
        self.assertEqual(context["action_ids"], ["action-tests"])
        self.assertEqual(len(record["artifacts"]), 2)
        artifact_ids = {item["id"] for item in record["artifacts"]}
        self.assertIn(record["observations"][0]["stdout_artifact_id"], artifact_ids)
        self.assertIn(record["observations"][0]["stderr_artifact_id"], artifact_ids)
        event_kinds = [item["kind"] for item in record["events"]]
        self.assertIn("tool_request", event_kinds)
        self.assertIn("tool_observation", event_kinds)

    def test_tool_events_require_session_export(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parents[1]) as temporary:
            contract, ledger, machine, decision, session, _ = completed_tool_run(
                Path(temporary) / "artifacts"
            )

            with self.assertRaisesRegex(RunRecordError, "ToolSession"):
                build_run_record(
                    contract,
                    ledger,
                    machine,
                    decision,
                    RunMetadata(
                        run_id="run-missing-session",
                        condition="sheath_stage0",
                        generator_id="fixture-generator",
                        runner_revision="runner-r1",
                        environment_digest=digest_bytes(b"fixture-environment"),
                        policy_digest=session.policy.digest,
                        supervisor_id="sheath-stage0-0.1.0",
                    ),
                    RunBudget(2, 60),
                    RunMetrics(0, 0.5, True),
                )

    def test_exports_sandbox_error_event(self) -> None:
        contract, ledger, machine, decision, session, finding = completed_error_run()

        record = build_run_record(
            contract,
            ledger,
            machine,
            decision,
            RunMetadata(
                run_id="run-sandbox-error",
                condition="sheath_stage0",
                generator_id="fixture-generator",
                runner_revision="runner-r1",
                environment_digest=digest_bytes(b"fixture-environment"),
                policy_digest=session.policy.digest,
                supervisor_id="sheath-stage0-0.1.0",
            ),
            RunBudget(2, 60),
            RunMetrics(0, 0.5, False),
            findings=(finding,),
            tool_sessions=(session,),
        )

        error = next(item for item in record["events"] if item["kind"] == "error")
        self.assertEqual(error["action_id"], "action-error")
        self.assertEqual(error["status"], "sandbox.isolation_unavailable")

    def test_export_rejects_tampered_output_artifact(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parents[1]) as temporary:
            contract, ledger, machine, decision, session, store = completed_tool_run(
                Path(temporary) / "artifacts"
            )
            stdout = store.get(session.observations[0].stdout_artifact_id)
            (store.root / stdout.path).write_bytes(b"tampered")

            with self.assertRaisesRegex(RunRecordError, "integrity check failed"):
                build_run_record(
                    contract,
                    ledger,
                    machine,
                    decision,
                    RunMetadata(
                        run_id="run-tampered-artifact",
                        condition="sheath_stage0",
                        generator_id="fixture-generator",
                        runner_revision="runner-r1",
                        environment_digest=digest_bytes(b"fixture-environment"),
                        policy_digest=session.policy.digest,
                        supervisor_id="sheath-stage0-0.1.0",
                    ),
                    RunBudget(2, 60),
                    RunMetrics(0, 0.5, True),
                    tool_sessions=(session,),
                )

    def test_exports_validated_generator_proposal_and_artifacts(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parents[1]) as temporary:
            contract, ledger, machine, decision, proposal, store = (
                completed_proposal_run(Path(temporary) / "artifacts")
            )

            record = build_run_record(
                contract,
                ledger,
                machine,
                decision,
                RunMetadata(
                    run_id="run-proposal",
                    condition="sheath_stage0",
                    generator_id="fixture-generator",
                    runner_revision="runner-r1",
                    environment_digest="sha256:environment",
                    policy_digest="sha256:policy",
                    supervisor_id="sheath-stage0-0.1.0",
                ),
                RunBudget(2, 60),
                RunMetrics(1, 0.5, True),
                proposals=(proposal,),
                proposal_store=store,
            )

        self.assertEqual(record["schema_version"], "1.7.0")
        self.assertEqual(len(record["proposals"]), 1)
        exported = record["proposals"][0]
        self.assertEqual(exported["id"], "proposal-1")
        self.assertEqual(exported["source_digest"], proposal.request.source_digest)
        self.assertEqual(exported["result_digest"], proposal.result_digest)
        self.assertEqual(exported["changed_paths"], ["generated.txt"])
        self.assertEqual(exported["claims"], ["generated.txt was created"])
        self.assertEqual(
            record["attempt_contexts"],
            [
                {
                    "attempt": 1,
                    "proposal_id": "proposal-1",
                    "revision": proposal.proposal.revision,
                    "policy_digest": None,
                    "environment_digests": [],
                    "action_ids": [],
                    "authorization_ids": [],
                    "observation_ids": [],
                }
            ],
        )
        event = next(item for item in record["events"] if item["kind"] == "proposal")
        self.assertEqual(event["proposal_id"], "proposal-1")
        self.assertEqual(event["content_artifact_id"], proposal.response_artifact.id)
        artifact_ids = {item["id"] for item in record["artifacts"]}
        self.assertEqual(
            artifact_ids,
            {proposal.response_artifact.id, proposal.patch_artifact.id},
        )

    def test_proposal_export_requires_matching_attempts_and_store(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parents[1]) as temporary:
            contract, ledger, machine, decision, proposal, store = (
                completed_proposal_run(Path(temporary) / "artifacts")
            )
            metadata = RunMetadata(
                run_id="run-proposal-invalid",
                condition="sheath_stage0",
                generator_id="fixture-generator",
                runner_revision="runner-r1",
                environment_digest="sha256:environment",
                policy_digest="sha256:policy",
                supervisor_id="sheath-stage0-0.1.0",
            )

            with self.assertRaisesRegex(RunRecordError, "proposal count"):
                build_run_record(
                    contract,
                    ledger,
                    machine,
                    decision,
                    metadata,
                    RunBudget(2, 60),
                    RunMetrics(0, 0.5, True),
                    proposals=(proposal,),
                    proposal_store=store,
                )
            with self.assertRaisesRegex(RunRecordError, "ArtifactStore"):
                build_run_record(
                    contract,
                    ledger,
                    machine,
                    decision,
                    metadata,
                    RunBudget(2, 60),
                    RunMetrics(1, 0.5, True),
                    proposals=(proposal,),
                )
            with self.assertRaisesRegex(RunRecordError, "requires proposals"):
                empty_contract, empty_ledger, empty_machine, empty_decision = (
                    completed_run(contract)
                )
                build_run_record(
                    empty_contract,
                    empty_ledger,
                    empty_machine,
                    empty_decision,
                    metadata,
                    RunBudget(2, 60),
                    RunMetrics(0, 0.5, True),
                    proposal_store=store,
                )

    def test_proposal_export_rejects_forged_binding_and_tampering(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parents[1]) as temporary:
            contract, ledger, machine, decision, proposal, store = (
                completed_proposal_run(Path(temporary) / "artifacts")
            )
            metadata = RunMetadata(
                run_id="run-proposal-tampered",
                condition="sheath_stage0",
                generator_id="fixture-generator",
                runner_revision="runner-r1",
                environment_digest="sha256:environment",
                policy_digest="sha256:policy",
                supervisor_id="sheath-stage0-0.1.0",
            )
            forged = replace(
                proposal,
                proposal=replace(proposal.proposal, generator_id="other"),
            )
            with self.assertRaisesRegex(RunRecordError, "generator"):
                build_run_record(
                    contract,
                    ledger,
                    machine,
                    decision,
                    metadata,
                    RunBudget(2, 60),
                    RunMetrics(1, 0.5, True),
                    proposals=(forged,),
                    proposal_store=store,
                )

            (store.root / proposal.response_artifact.path).write_bytes(b"tampered")
            with self.assertRaisesRegex(RunRecordError, "integrity check failed"):
                build_run_record(
                    contract,
                    ledger,
                    machine,
                    decision,
                    metadata,
                    RunBudget(2, 60),
                    RunMetrics(1, 0.5, True),
                    proposals=(proposal,),
                    proposal_store=store,
                )


if __name__ == "__main__":
    unittest.main()
