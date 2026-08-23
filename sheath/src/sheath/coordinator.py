"""Minimal single- and bounded-attempt composition for Stage-0 workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any, Protocol

from .artifacts import ArtifactStore, StoredArtifact
from .contracts import TaskContract
from .decision import Decision, Finding, Severity, Verdict, decide
from .generator import (
    GenerationRequest,
    GeneratorAdapter,
    GeneratorError,
    ValidatedProposal,
    validate_proposal,
)
from .ledger import Evidence, EvidenceLedger, LedgerError
from .records import (
    RunBudget,
    RunMetadata,
    RunMetrics,
    RunRecordError,
    build_run_record,
    run_record_digest,
)
from .snapshots import (
    SnapshotError,
    SnapshotStager,
    WorkspaceSnapshot,
    directory_digest,
)
from .state import RunState, RunStateMachine, StateError
from .tools import ToolSession


class CoordinatorError(RuntimeError):
    """Raised when a single attempt cannot produce a trustworthy run record."""

    def __init__(
        self,
        message: str,
        *,
        record: dict[str, Any] | None = None,
        record_digest: str | None = None,
        cause: Exception | None = None,
        failure_code: str | None = None,
    ):
        super().__init__(message)
        self.record = record
        self.record_digest = record_digest
        self.cause = cause
        self.failure_code = failure_code


def _coordinator_failure_code(error: Exception) -> str:
    if isinstance(error, GeneratorError):
        return "coordinator.generator_error"
    if isinstance(error, SnapshotError):
        return "coordinator.snapshot_error"
    if isinstance(error, LedgerError):
        return "coordinator.ledger_error"
    if isinstance(error, RunRecordError):
        return "coordinator.record_error"
    if isinstance(error, StateError):
        return "coordinator.state_error"
    if isinstance(error, CoordinatorError) and error.failure_code:
        return error.failure_code
    return f"coordinator.{error.__class__.__name__.lower()}"


def _propose(
    generator: GeneratorAdapter,
    request: GenerationRequest,
    snapshot: WorkspaceSnapshot,
    store: ArtifactStore,
):
    """Keep implementation failures inside the typed generator boundary."""

    try:
        return generator.propose(request, snapshot, store)
    except GeneratorError:
        raise
    except Exception as error:
        raise GeneratorError(str(error)) from error


def _build_failure_record(
    contract: TaskContract,
    ledger: EvidenceLedger,
    machine: RunStateMachine,
    metadata: RunMetadata,
    budget: RunBudget,
    metrics: RunMetrics,
    *,
    failure_code: str,
    failure_summary: str,
    protocol_deviations: tuple[str, ...],
    findings: tuple[Finding, ...] = (),
    proposals: tuple[ValidatedProposal, ...] = (),
    tool_sessions: tuple[ToolSession | None, ...] = (),
    proposal_store: ArtifactStore | None = None,
    failure_artifacts: tuple[StoredArtifact, ...] = (),
    failure_store: ArtifactStore | None = None,
) -> dict[str, Any]:
    return build_run_record(
        contract,
        ledger,
        machine,
        None,
        metadata,
        budget,
        metrics,
        findings=findings,
        protocol_deviations=protocol_deviations,
        failure_reason_codes=(failure_code,),
        failure_summary=failure_summary,
        tool_sessions=tool_sessions,
        proposals=proposals,
        proposal_store=proposal_store,
        failure_artifacts=failure_artifacts,
        failure_store=failure_store,
    )


@dataclass(frozen=True, slots=True)
class VerificationReport:
    """Evidence and findings produced by verification of one validated proposal."""

    evidence: tuple[Evidence, ...]
    findings: tuple[Finding, ...] = ()
    tool_session: ToolSession | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, tuple) or any(
            not isinstance(item, Evidence) for item in self.evidence
        ):
            raise TypeError("verification evidence must be a tuple of Evidence")
        if not isinstance(self.findings, tuple) or any(
            not isinstance(item, Finding) for item in self.findings
        ):
            raise TypeError("verification findings must be a tuple of Finding")
        if self.tool_session is not None and not isinstance(
            self.tool_session,
            ToolSession,
        ):
            raise TypeError("verification tool_session must be a ToolSession or null")


class ProposalVerifier(Protocol):
    """Narrow verification boundary used after proposal validation."""

    def verify(
        self,
        proposal: ValidatedProposal,
        snapshot: WorkspaceSnapshot,
        ledger: EvidenceLedger,
        store: ArtifactStore,
    ) -> VerificationReport: ...


@dataclass(frozen=True, slots=True)
class SingleAttemptResult:
    """Canonical output of one completed coordinator attempt."""

    record: dict[str, Any]
    digest: str
    decision: Decision
    proposal: ValidatedProposal


@dataclass(frozen=True, slots=True)
class BoundedAttemptResult:
    """Canonical output of a completed bounded coordinator run."""

    record: dict[str, Any]
    digest: str
    decision: Decision
    proposals: tuple[ValidatedProposal, ...]


def run_single_attempt(
    contract: TaskContract,
    generator: GeneratorAdapter,
    verifier: ProposalVerifier,
    snapshot: WorkspaceSnapshot,
    store: ArtifactStore,
    metadata: RunMetadata,
    budget: RunBudget,
    *,
    feedback: tuple[str, ...] = (),
    protocol_deviations: tuple[str, ...] = (),
    clock: Callable[[], str] | None = None,
    timer: Callable[[], float] = monotonic,
) -> SingleAttemptResult:
    """Run and export one proposal attempt using the existing Stage-0 boundaries."""

    generator_id = getattr(generator, "generator_id", None)
    if not isinstance(generator_id, str) or not generator_id.strip():
        raise CoordinatorError("generator must expose a non-empty generator_id")
    if generator_id != metadata.generator_id:
        raise CoordinatorError("generator identity does not match run metadata")
    if not callable(getattr(verifier, "verify", None)):
        raise CoordinatorError("verifier must expose verify(proposal)")
    if budget.max_attempts != 1:
        raise CoordinatorError("single-attempt coordinator requires max_attempts=1")

    started = timer()
    ledger = EvidenceLedger(contract.repository.revision, clock=clock)
    machine = RunStateMachine(ledger)
    proposal: ValidatedProposal | None = None
    tool_session: ToolSession | None = None
    try:
        machine.transition(RunState.CONTRACTED)
        machine.transition(RunState.TRIAGED)
        request = GenerationRequest(
            contract,
            ledger.current_revision,
            snapshot.source_digest,
            1,
            feedback,
        )
        raw_proposal = _propose(generator, request, snapshot, store)
        proposal = validate_proposal(
            request,
            raw_proposal,
            snapshot,
            store,
            generator_id,
        )
        machine.transition(RunState.PROPOSED)
        ledger.record_proposal(proposal.proposal.id, proposal.response_artifact.id)
        machine.transition(RunState.ACTION_VALIDATION)
        machine.transition(RunState.EXECUTED)

        report = verifier.verify(proposal, snapshot, ledger, store)
        if not isinstance(report, VerificationReport):
            raise CoordinatorError("verifier must return a VerificationReport")
        tool_session = report.tool_session
        if tool_session is not None:
            if tool_session.ledger is not ledger:
                raise CoordinatorError("verifier tool session uses another ledger")
            if tool_session.artifact_store is not store:
                raise CoordinatorError("verifier tool session uses another artifact store")
        for evidence in report.evidence:
            ledger.record_evidence(evidence)

        elapsed = max(0.0, timer() - started)
        findings = report.findings + (
            () if tool_session is None else tool_session.blocking_findings
        )
        deviations = protocol_deviations
        if directory_digest(snapshot.root) != proposal.result_digest:
            findings += (
                Finding(
                    id="coordinator-verification-workspace-drift",
                    category="engineering_defect",
                    severity=Severity.ESCALATION,
                    message="Verification changed the validated proposal workspace.",
                    source="policy",
                ),
            )
            deviations += ("verification changed the proposal workspace",)
        if elapsed > budget.max_wall_seconds:
            findings += (
                Finding(
                    id="coordinator-wall-time-exceeded",
                    category="other",
                    severity=Severity.ESCALATION,
                    message="The single attempt exceeded its wall-time budget.",
                    source="policy",
                ),
            )
            deviations += ("budget.max_wall_seconds exceeded",)

        machine.transition(RunState.ASSESSED)
        decision = decide(contract, ledger, findings)
        machine.apply_decision(decision)
        machine.transition(RunState.EXPORTED)
        record = build_run_record(
            contract,
            ledger,
            machine,
            decision,
            metadata,
            budget,
            RunMetrics(
                attempts=1,
                wall_seconds=elapsed,
                verified_success=decision.verdict is Verdict.ACCEPT,
            ),
            findings=findings,
            protocol_deviations=deviations,
            tool_sessions=(tool_session,),
            proposals=(proposal,),
            proposal_store=store,
        )
    except Exception as error:
        if isinstance(error, CoordinatorError) and error.record is not None:
            raise
        elapsed = max(0.0, timer() - started)
        failure_code = _coordinator_failure_code(error)
        failure_summary = str(error)
        failure_artifacts = error.artifacts if isinstance(error, GeneratorError) else ()
        findings = (
            Finding(
                id=f"coordinator-failure:{failure_code}",
                category="engineering_defect",
                severity=Severity.ESCALATION,
                message=f"single attempt failed: {failure_summary}",
                source="policy",
            ),
        )
        record = _build_failure_record(
            contract,
            ledger,
            machine,
            metadata,
            budget,
            RunMetrics(
                attempts=0 if proposal is None else 1,
                wall_seconds=elapsed,
                verified_success=False,
            ),
            failure_code=failure_code,
            failure_summary=failure_summary,
            protocol_deviations=protocol_deviations + (failure_code,),
            findings=findings,
            proposals=() if proposal is None else (proposal,),
            tool_sessions=() if tool_session is None else (tool_session,),
            proposal_store=store if proposal is not None else None,
            failure_artifacts=failure_artifacts,
            failure_store=store if failure_artifacts else None,
        )
        raise CoordinatorError(
            failure_summary,
            record=record,
            record_digest=run_record_digest(record),
            cause=error,
            failure_code=failure_code,
        ) from error
    return SingleAttemptResult(record, run_record_digest(record), decision, proposal)


def run_bounded_attempts(
    contract: TaskContract,
    generator: GeneratorAdapter,
    verifier: ProposalVerifier,
    initial_snapshot: WorkspaceSnapshot,
    stager: SnapshotStager,
    store: ArtifactStore,
    metadata: RunMetadata,
    budget: RunBudget,
    *,
    feedback: tuple[str, ...] = (),
    protocol_deviations: tuple[str, ...] = (),
    clock: Callable[[], str] | None = None,
    timer: Callable[[], float] = monotonic,
) -> BoundedAttemptResult:
    """Run bounded revision attempts and export their ordered provenance."""

    generator_id = getattr(generator, "generator_id", None)
    if not isinstance(generator_id, str) or not generator_id.strip():
        raise CoordinatorError("generator must expose a non-empty generator_id")
    if generator_id != metadata.generator_id:
        raise CoordinatorError("generator identity does not match run metadata")
    if not callable(getattr(verifier, "verify", None)):
        raise CoordinatorError("verifier must expose verify(proposal)")
    if budget.max_attempts < 2:
        raise CoordinatorError("bounded coordinator requires max_attempts >= 2")
    if not isinstance(initial_snapshot, WorkspaceSnapshot) or initial_snapshot.closed:
        raise CoordinatorError("bounded coordinator requires an active initial snapshot")
    if not isinstance(stager, SnapshotStager):
        raise CoordinatorError("stager must be a SnapshotStager")
    if initial_snapshot.root.parent != stager.root:
        raise CoordinatorError("stager must own the initial snapshot")

    started = timer()
    ledger = EvidenceLedger(contract.repository.revision, clock=clock)
    machine = RunStateMachine(ledger)
    current_snapshot = initial_snapshot
    owned_snapshots: list[WorkspaceSnapshot] = []
    proposals: list[ValidatedProposal] = []
    findings: list[Finding] = []
    deviations = list(protocol_deviations)
    tool_sessions: list[ToolSession | None] = []
    current_feedback = feedback
    failure: Exception | None = None
    failure_protocol = list(protocol_deviations)
    try:
        machine.transition(RunState.CONTRACTED)
        machine.transition(RunState.TRIAGED)
        for attempt in range(1, budget.max_attempts + 1):
            request = GenerationRequest(
                contract,
                ledger.current_revision,
                current_snapshot.source_digest,
                attempt,
                current_feedback,
            )
            raw_proposal = _propose(generator, request, current_snapshot, store)
            proposal = validate_proposal(
                request,
                raw_proposal,
                current_snapshot,
                store,
                generator_id,
            )
            machine.transition(RunState.PROPOSED)
            ledger.record_proposal(
                proposal.proposal.id,
                proposal.response_artifact.id,
            )
            machine.transition(RunState.ACTION_VALIDATION)
            machine.transition(RunState.EXECUTED)

            report = verifier.verify(proposal, current_snapshot, ledger, store)
            if not isinstance(report, VerificationReport):
                raise CoordinatorError("verifier must return a VerificationReport")
            tool_session = report.tool_session
            if tool_session is not None:
                if tool_session.ledger is not ledger:
                    raise CoordinatorError("verifier tool session uses another ledger")
                if tool_session.artifact_store is not store:
                    raise CoordinatorError(
                        "verifier tool session uses another artifact store"
                    )
            for evidence in report.evidence:
                ledger.record_evidence(evidence)

            attempt_findings = list(report.findings)
            if tool_session is not None:
                attempt_findings.extend(tool_session.blocking_findings)
            if directory_digest(current_snapshot.root) != proposal.result_digest:
                attempt_findings.append(
                    Finding(
                        id=f"coordinator-verification-workspace-drift:{attempt}",
                        category="engineering_defect",
                        severity=Severity.ESCALATION,
                        message="Verification changed the validated proposal workspace.",
                        source="policy",
                    )
                )
                deviations.append(
                    f"attempt {attempt}: verification changed the proposal workspace"
                )
            elapsed = max(0.0, timer() - started)
            if elapsed > budget.max_wall_seconds:
                attempt_findings.append(
                    Finding(
                        id="coordinator-wall-time-exceeded",
                        category="other",
                        severity=Severity.ESCALATION,
                        message="The bounded run exceeded its wall-time budget.",
                        source="policy",
                    )
                )
                deviations.append("budget.max_wall_seconds exceeded")

            existing_finding_ids = {item.id for item in findings}
            duplicate_ids = sorted(
                item.id for item in attempt_findings if item.id in existing_finding_ids
            )
            if duplicate_ids:
                raise CoordinatorError(
                    "finding IDs must be unique across attempts: "
                    + ", ".join(duplicate_ids)
                )
            machine.transition(RunState.ASSESSED)
            decision = decide(contract, ledger, attempt_findings)
            machine.apply_decision(decision)
            proposals.append(proposal)
            tool_sessions.append(tool_session)
            findings.extend(attempt_findings)

            retry = (
                decision.verdict is Verdict.REVISE
                and attempt < budget.max_attempts
            )
            if not retry:
                machine.transition(RunState.EXPORTED)
                break

            next_snapshot = stager.restage(current_snapshot)
            if next_snapshot.source_digest != proposal.result_digest:
                next_snapshot.close()
                raise CoordinatorError("retry snapshot does not match the prior result")
            owned_snapshots.append(next_snapshot)
            next_attempt = attempt + 1
            ledger.record_revision(
                f"attempt-{next_attempt}:{next_snapshot.source_digest}"
            )
            current_feedback = tuple(dict.fromkeys(decision.reason_codes))
            current_snapshot = next_snapshot

        record = build_run_record(
            contract,
            ledger,
            machine,
            decision,
            metadata,
            budget,
            RunMetrics(
                attempts=len(proposals),
                wall_seconds=elapsed,
                verified_success=decision.verdict is Verdict.ACCEPT,
            ),
            findings=findings,
            protocol_deviations=deviations,
            tool_sessions=tool_sessions,
            proposals=proposals,
            proposal_store=store,
        )
    except Exception as error:
        if isinstance(error, CoordinatorError) and error.record is not None:
            raise
        failure = error
    finally:
        cleanup_errors: list[str] = []
        for snapshot in reversed(owned_snapshots):
            try:
                snapshot.close()
            except SnapshotError as error:
                cleanup_errors.append(str(error))
        if cleanup_errors:
            failure_protocol.extend(
                f"coordinator.snapshot_cleanup_failure:{item}" for item in cleanup_errors
            )
            if failure is None:
                failure = RuntimeError("; ".join(cleanup_errors))

    if failure is not None:
        elapsed = max(0.0, timer() - started)
        if isinstance(failure, CoordinatorError) and failure.record is not None:
            raise failure
        failure_code = _coordinator_failure_code(failure)
        failure_summary = str(failure)
        failure_artifacts = failure.artifacts if isinstance(failure, GeneratorError) else ()
        failure_protocol = tuple(failure_protocol + [failure_code])
        record = _build_failure_record(
            contract,
            ledger,
            machine,
            metadata,
            budget,
            RunMetrics(
                attempts=len(proposals),
                wall_seconds=elapsed,
                verified_success=False,
            ),
            failure_code=failure_code,
            failure_summary=failure_summary,
            protocol_deviations=failure_protocol,
            findings=(
                Finding(
                    id=f"coordinator-failure:{failure_code}",
                    category="engineering_defect",
                    severity=Severity.ESCALATION,
                    message=f"bounded attempt failed: {failure_summary}",
                    source="policy",
                ),
            ),
            proposals=tuple(proposals),
            tool_sessions=tuple(tool_sessions),
            proposal_store=store if proposals else None,
            failure_artifacts=failure_artifacts,
            failure_store=store if failure_artifacts else None,
        )
        raise CoordinatorError(
            failure_summary,
            record=record,
            record_digest=run_record_digest(record),
            cause=failure,
            failure_code=failure_code,
        ) from failure
    proposals_tuple = tuple(proposals)
    return BoundedAttemptResult(
        record,
        run_record_digest(record),
        decision,
        proposals_tuple,
    )
