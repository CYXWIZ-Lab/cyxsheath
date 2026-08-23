"""Canonical run-record construction for reproducible Stage-0 research."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable

from .artifacts import ArtifactError, ArtifactStore, StoredArtifact
from .contracts import TaskContract
from .decision import Decision, Finding, Verdict
from .generator import ValidatedProposal
from .ledger import EvidenceLedger, LedgerEvent
from .patches import PatchError, _decode_record
from .state import RunState, RunStateMachine
from .tools import ToolSession


class RunRecordError(ValueError):
    """Raised when an incomplete or inconsistent run cannot be exported."""


_CONDITIONS = {
    "direct",
    "instruction",
    "self_reflection",
    "sheath_stage0",
    "sheath_learned",
}

_TERMINAL_STATE = {
    Verdict.ACCEPT: RunState.VERIFIED,
    Verdict.REVISE: RunState.REVISION_REQUIRED,
    Verdict.BLOCK: RunState.BLOCKED,
    Verdict.ESCALATE: RunState.ESCALATED,
}


def _text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RunRecordError(f"{field} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class RunMetadata:
    run_id: str
    condition: str
    generator_id: str
    runner_revision: str
    environment_digest: str
    policy_digest: str
    supervisor_id: str | None = None
    parent_run_id: str | None = None
    seed: int | None = None
    prompt_digest: str | None = None
    instruction_digest: str | None = None

    def __post_init__(self) -> None:
        for field in (
            "run_id",
            "generator_id",
            "runner_revision",
            "environment_digest",
            "policy_digest",
        ):
            _text(getattr(self, field), field)
        if self.condition not in _CONDITIONS:
            raise RunRecordError(f"unsupported condition: {self.condition}")
        if self.condition.startswith("sheath_") and not self.supervisor_id:
            raise RunRecordError("Sheath conditions require a supervisor_id")
        if self.seed is not None and not isinstance(self.seed, int):
            raise RunRecordError("seed must be an integer when set")


@dataclass(frozen=True, slots=True)
class RunBudget:
    max_attempts: int
    max_wall_seconds: float
    max_tokens: int | None = None
    max_cost: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.max_attempts, int) or self.max_attempts < 1:
            raise RunRecordError("max_attempts must be a positive integer")
        if not isinstance(self.max_wall_seconds, (int, float)) or self.max_wall_seconds <= 0:
            raise RunRecordError("max_wall_seconds must be positive")
        if self.max_tokens is not None and self.max_tokens < 1:
            raise RunRecordError("max_tokens must be positive when set")
        if self.max_cost is not None and self.max_cost < 0:
            raise RunRecordError("max_cost cannot be negative")


@dataclass(frozen=True, slots=True)
class RunMetrics:
    attempts: int
    wall_seconds: float
    verified_success: bool | None = None
    tokens: int | None = None
    estimated_cost: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.attempts, int) or self.attempts < 0:
            raise RunRecordError("attempts must be a non-negative integer")
        if not isinstance(self.wall_seconds, (int, float)) or self.wall_seconds < 0:
            raise RunRecordError("wall_seconds cannot be negative")
        if self.verified_success is not None and not isinstance(
            self.verified_success, bool
        ):
            raise RunRecordError("verified_success must be boolean or null")
        if self.tokens is not None and self.tokens < 0:
            raise RunRecordError("tokens cannot be negative")
        if self.estimated_cost is not None and self.estimated_cost < 0:
            raise RunRecordError("estimated_cost cannot be negative")


def _event_record(event: LedgerEvent, evidence_by_id: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": f"event-{event.sequence:06d}",
        "sequence": event.sequence,
        "kind": event.kind if event.kind != "revision" else "patch",
        "timestamp": event.timestamp,
        "revision": event.revision,
    }
    if event.kind == "revision":
        record["status"] = "repository_revision"
    elif event.kind == "evidence":
        evidence = evidence_by_id[event.evidence_id]
        record["evidence_id"] = event.evidence_id
        record["status"] = "passed" if evidence.passed else "failed"
    elif event.kind == "proposal":
        record["proposal_id"] = event.proposal_id
        record["content_artifact_id"] = event.content_artifact_id
        record["status"] = event.status
    elif event.kind == "state_transition":
        record["from_state"] = event.from_state
        record["to_state"] = event.to_state
        record["status"] = "transition"
    elif event.kind == "tool_request":
        record["action_id"] = event.action_id
        record["authorization_id"] = event.authorization_id
        record["status"] = event.status
    elif event.kind == "tool_observation":
        record["action_id"] = event.action_id
        record["observation_id"] = event.observation_id
        record["status"] = event.status
    elif event.kind == "error":
        record["action_id"] = event.action_id
        record["status"] = event.status
    return record


def build_run_record(
    contract: TaskContract,
    ledger: EvidenceLedger,
    machine: RunStateMachine,
    decision: Decision | None,
    metadata: RunMetadata,
    budget: RunBudget,
    metrics: RunMetrics,
    findings: Iterable[Finding] = (),
    protocol_deviations: Iterable[str] = (),
    tool_sessions: Iterable[ToolSession | None] = (),
    proposals: Iterable[ValidatedProposal] = (),
    proposal_store: ArtifactStore | None = None,
    failure_reason_codes: Iterable[str] = (),
    failure_summary: str | None = None,
    failure_artifacts: Iterable[StoredArtifact] = (),
    failure_store: ArtifactStore | None = None,
) -> dict[str, Any]:
    """Create a schema-v1.7 run record after completion or coordinator failure."""

    failure_mode = decision is None
    if machine.ledger is not ledger:
        raise RunRecordError("state machine and run record must use the same ledger")
    if not failure_mode and machine.state is not RunState.EXPORTED:
        raise RunRecordError("state machine must be exported before record construction")
    if len(machine.transitions) < 2:
        raise RunRecordError("state history is incomplete")
    if ledger.events[0].revision != contract.repository.revision:
        raise RunRecordError("initial ledger revision does not match the task contract")
    if failure_mode:
        if metrics.verified_success is True:
            raise RunRecordError(
                "verified_success cannot be true for a failed run record"
            )
    else:
        decision_state = machine.transitions[-1].from_state
        if decision_state is not _TERMINAL_STATE[decision.verdict]:
            raise RunRecordError("final state does not match decision verdict")
        if metrics.verified_success is True and decision.verdict is not Verdict.ACCEPT:
            raise RunRecordError("verified_success cannot be true for a non-accept decision")

    decision_reason_codes = []
    decision_evidence_ids = []
    decision_verdict = "failed"
    if decision is None:
        decision_reason_codes = tuple(dict.fromkeys(tuple(failure_reason_codes)))
        if not decision_reason_codes:
            decision_reason_codes = ("coordinator.failure",)
    else:
        decision_verdict = decision.verdict.value
        decision_reason_codes = decision.reason_codes
        decision_evidence_ids = decision.evidence_ids


    proposals = tuple(proposals)
    if any(not isinstance(item, ValidatedProposal) for item in proposals):
        raise RunRecordError("proposals must contain ValidatedProposal records")
    if metrics.attempts != len(proposals):
        raise RunRecordError("metrics.attempts must equal the proposal count")
    if metrics.attempts > budget.max_attempts:
        raise RunRecordError("proposal count exceeds the run attempt budget")
    attempts = tuple(item.proposal.attempt for item in proposals)
    if attempts != tuple(range(1, len(proposals) + 1)):
        raise RunRecordError("proposal attempts must be ordered and contiguous")
    proposal_ids = tuple(item.proposal.id for item in proposals)
    if len(proposal_ids) != len(set(proposal_ids)):
        raise RunRecordError("proposal IDs must be unique")
    ledger_revisions = {event.revision for event in ledger.events}
    proposal_events = {
        event.proposal_id: event for event in ledger.events if event.kind == "proposal"
    }
    if len(proposal_events) != len(proposals):
        raise RunRecordError("proposal records do not match ledger proposal events")
    for item in proposals:
        if item.request.contract != contract:
            raise RunRecordError("proposal uses another task contract")
        if item.request.revision != item.proposal.revision:
            raise RunRecordError("proposal revision does not match its request")
        if item.request.attempt != item.proposal.attempt:
            raise RunRecordError("proposal attempt does not match its request")
        if item.proposal.generator_id != metadata.generator_id:
            raise RunRecordError("proposal generator does not match run metadata")
        if item.proposal.revision not in ledger_revisions:
            raise RunRecordError("proposal revision is absent from the run ledger")
        event = proposal_events.get(item.proposal.id)
        if event is None:
            raise RunRecordError("proposal is absent from the run ledger")
        if event.revision != item.proposal.revision:
            raise RunRecordError("proposal ledger revision is inconsistent")
        if event.content_artifact_id != item.response_artifact.id:
            raise RunRecordError("proposal ledger artifact is inconsistent")

    supplied_sessions = tuple(tool_sessions)
    if any(
        item is not None and not isinstance(item, ToolSession)
        for item in supplied_sessions
    ):
        raise RunRecordError("tool_sessions must contain ToolSession records or null")
    if proposals:
        if not supplied_sessions:
            supplied_sessions = (None,) * len(proposals)
        elif len(supplied_sessions) != len(proposals):
            raise RunRecordError("tool_sessions must align with proposal attempts")
    elif len(supplied_sessions) > 1:
        raise RunRecordError("runs without proposals support at most one tool session")
    elif supplied_sessions and supplied_sessions[0] is None:
        raise RunRecordError("an unbound tool session cannot be null")

    tool_events = tuple(
        event
        for event in ledger.events
        if event.kind in {"tool_request", "tool_observation", "error"}
    )
    sessions = tuple(item for item in supplied_sessions if item is not None)
    if not sessions and tool_events:
        raise RunRecordError("tool events require their ToolSession for export")
    for session in sessions:
        if session.ledger is not ledger:
            raise RunRecordError("tool session and run record must use the same ledger")

    findings = tuple(findings)
    deviations = tuple(protocol_deviations)
    if any(not isinstance(item, str) or not item.strip() for item in deviations):
        raise RunRecordError("protocol deviations must be non-empty strings")
    if any(not isinstance(item, str) or not item.strip() for item in decision_reason_codes):
        raise RunRecordError("failure reason codes must be non-empty strings")

    evidence_by_id = {item.id: item for item in ledger.evidence}
    evidence_timestamps = {
        event.evidence_id: event.timestamp
        for event in ledger.events
        if event.evidence_id is not None
    }
    referenced_ids = {
        evidence_id
        for finding in findings
        for evidence_id in finding.evidence_ids
    } | set(decision_evidence_ids)
    missing = sorted(referenced_ids - evidence_by_id.keys())
    if missing:
        raise RunRecordError(f"run record references unknown evidence: {', '.join(missing)}")

    actions = tuple(item for session in sessions for item in session.actions)
    authorizations = tuple(
        item for session in sessions for item in session.authorizations
    )
    observations = tuple(item for session in sessions for item in session.observations)
    executables_by_id = {}
    for session in sessions:
        for executable in session.executables:
            existing = executables_by_id.get(executable.id)
            if existing is not None and existing != executable:
                raise RunRecordError("executable ID identifies conflicting records")
            executables_by_id[executable.id] = executable
    executables = tuple(executables_by_id.values())
    tool_stores = {
        id(session.artifact_store): session.artifact_store
        for session in sessions
        if session.artifact_store is not None
    }
    if len(tool_stores) > 1:
        raise RunRecordError("tool sessions must use the same artifact store")
    tool_store = next(iter(tool_stores.values()), None)
    if proposals and proposal_store is None:
        raise RunRecordError("proposals require their ArtifactStore for export")
    if not proposals and proposal_store is not None:
        raise RunRecordError("proposal_store requires proposals")
    failure_artifacts = tuple(failure_artifacts)
    if any(not isinstance(item, StoredArtifact) for item in failure_artifacts):
        raise RunRecordError("failure_artifacts must contain StoredArtifact records")
    if failure_artifacts and not failure_mode:
        raise RunRecordError("failure_artifacts require a failed run record")
    if failure_artifacts and failure_store is None:
        raise RunRecordError("failure_artifacts require their ArtifactStore")
    if not failure_artifacts and failure_store is not None:
        raise RunRecordError("failure_store requires failure_artifacts")
    stores = tuple(
        item
        for item in (tool_store, proposal_store, failure_store)
        if item is not None
    )
    if len({id(item) for item in stores}) > 1:
        raise RunRecordError("run artifacts must use the same store")
    artifact_store = stores[0] if stores else None
    if len(actions) != len({item.id for item in actions}):
        raise RunRecordError("action IDs must be unique across tool sessions")
    if len(authorizations) != len({item.id for item in authorizations}):
        raise RunRecordError("authorization IDs must be unique across tool sessions")
    if len(observations) != len({item.id for item in observations}):
        raise RunRecordError("observation IDs must be unique across tool sessions")
    action_ids = {item.id for item in actions}
    authorization_ids = {item.id for item in authorizations}
    observation_ids = {item.id for item in observations}
    executable_ids = {item.id for item in executables}
    if any(item.action_id not in action_ids for item in authorizations):
        raise RunRecordError("authorization references an unknown action")
    if any(
        item.executable_id is not None and item.executable_id not in executable_ids
        for item in authorizations
    ):
        raise RunRecordError("authorization references an unknown executable")
    if any(item.allowed and item.executable_id is None for item in authorizations):
        raise RunRecordError("allowed authorization requires an executable identity")
    if any(item.action_id not in action_ids for item in observations):
        raise RunRecordError("observation references an unknown action")
    attempt_contexts = []
    if proposals:
        context_inputs = zip(proposals, supplied_sessions)
    else:
        context_inputs = ((None, supplied_sessions[0]),) if supplied_sessions else ()
    for proposal, session in context_inputs:
        if proposal is None:
            attempt = None
            proposal_id = None
            revisions = {
                item.revision
                for item in (*session.authorizations, *session.observations)
            }
            if len(revisions) != 1:
                raise RunRecordError(
                    "an unbound tool session must contain exactly one revision"
                )
            revision = next(iter(revisions))
        else:
            attempt = proposal.proposal.attempt
            proposal_id = proposal.proposal.id
            revision = proposal.proposal.revision
            if session is not None:
                session_revisions = {
                    item.revision
                    for item in (*session.authorizations, *session.observations)
                }
                if session_revisions and session_revisions != {revision}:
                    raise RunRecordError(
                        "tool session revision does not match its proposal attempt"
                    )
        context_actions = () if session is None else session.actions
        context_authorizations = () if session is None else session.authorizations
        context_observations = () if session is None else session.observations
        attempt_contexts.append(
            {
                "attempt": attempt,
                "proposal_id": proposal_id,
                "revision": revision,
                "policy_digest": None if session is None else session.policy.digest,
                "environment_digests": sorted(
                    {item.environment_digest for item in context_observations}
                ),
                "action_ids": [item.id for item in context_actions],
                "authorization_ids": [item.id for item in context_authorizations],
                "observation_ids": [item.id for item in context_observations],
            }
        )
    for event in tool_events:
        if event.action_id not in action_ids:
            raise RunRecordError("tool event references an unknown action")
        if (
            event.authorization_id is not None
            and event.authorization_id not in authorization_ids
        ):
            raise RunRecordError("tool event references an unknown authorization")
        if event.observation_id is not None and event.observation_id not in observation_ids:
            raise RunRecordError("tool event references an unknown observation")

    if observations and artifact_store is None:
        raise RunRecordError("observations require their ArtifactStore for export")
    artifacts_by_id = {}
    if artifact_store is not None:
        try:
            for observation in observations:
                stdout = artifact_store.get(observation.stdout_artifact_id)
                stderr = artifact_store.get(observation.stderr_artifact_id)
                if stdout.kind != "stdout" or stdout.digest != observation.stdout_digest:
                    raise RunRecordError("stdout artifact does not match its observation")
                if stderr.kind != "stderr" or stderr.digest != observation.stderr_digest:
                    raise RunRecordError("stderr artifact does not match its observation")
                artifacts_by_id[stdout.id] = stdout
                artifacts_by_id[stderr.id] = stderr
            for item in proposals:
                response = artifact_store.get(item.proposal.response_artifact_id)
                patch = artifact_store.get(item.proposal.patch_artifact_id)
                if (
                    response != item.response_artifact
                    or response.kind != "response"
                    or response.size_bytes < 1
                ):
                    raise RunRecordError("proposal response artifact is inconsistent")
                if patch != item.patch_artifact or patch.kind != "patch":
                    raise RunRecordError("proposal patch artifact is inconsistent")
                patch_record, changed_paths = _decode_record(
                    (artifact_store.root / patch.path).read_bytes(),
                    item.request.source_digest,
                )
                if patch_record["result_digest"] != item.result_digest:
                    raise RunRecordError("proposal result digest is inconsistent")
                if changed_paths != item.changed_paths:
                    raise RunRecordError("proposal changed paths are inconsistent")
                artifacts_by_id[response.id] = response
                artifacts_by_id[patch.id] = patch
            for artifact in failure_artifacts:
                artifact_store.verify(artifact)
                artifacts_by_id[artifact.id] = artifact
        except (ArtifactError, OSError, PatchError) as error:
            raise RunRecordError(str(error)) from error

    events = tuple(ledger.events)
    evidence_records = [
        {
            "id": item.id,
            "check_id": item.check_id,
            "revision": item.revision,
            "passed": item.passed,
            "source": item.source,
            "recorded_at": evidence_timestamps[item.id],
            "detail": item.detail,
        }
        for item in ledger.evidence
    ]
    finding_records = [
        {
            "id": item.id,
            "category": item.category,
            "severity": item.severity.value,
            "message": item.message,
            "constraint_id": item.constraint_id,
            "location": item.location,
            "evidence_ids": list(item.evidence_ids),
            "confidence": item.confidence,
            "source": item.source,
        }
        for item in findings
    ]

    decision_record = {
        "verdict": decision_verdict,
        "reason_codes": list(decision_reason_codes),
        "evidence_ids": list(decision_evidence_ids),
    }
    if failure_summary is not None and decision is None:
        decision_record["summary"] = failure_summary

    return {
        "schema_version": "1.7.0",
        "run_id": metadata.run_id,
        "task_id": contract.task_id,
        "parent_run_id": metadata.parent_run_id,
        "condition": metadata.condition,
        "seed": metadata.seed,
        "started_at": events[0].timestamp,
        "ended_at": events[-1].timestamp,
        "system": {
            "generator_id": metadata.generator_id,
            "supervisor_id": metadata.supervisor_id,
            "runner_revision": metadata.runner_revision,
            "environment_digest": metadata.environment_digest,
            "policy_digest": metadata.policy_digest,
            "prompt_digest": metadata.prompt_digest,
            "instruction_digest": metadata.instruction_digest,
        },
        "budget": {
            "max_attempts": budget.max_attempts,
            "max_wall_seconds": budget.max_wall_seconds,
            "max_tokens": budget.max_tokens,
            "max_cost": budget.max_cost,
        },
        "events": [_event_record(event, evidence_by_id) for event in events],
        "executables": [
            {
                "id": item.id,
                "name": item.name,
                "path": item.path,
                "digest": item.digest,
                "size_bytes": item.size_bytes,
                "scope": item.scope,
                "image_digest": item.image_digest,
            }
            for item in executables
        ],
        "actions": [
            {
                "id": item.id,
                "argv": list(item.argv),
                "working_directory": item.working_directory,
                "timeout_seconds": item.timeout_seconds,
                "max_output_bytes": item.max_output_bytes,
            }
            for item in actions
        ],
        "authorizations": [
            {
                "id": item.id,
                "action_id": item.action_id,
                "revision": item.revision,
                "allowed": item.allowed,
                "reason_codes": list(item.reason_codes),
                "resolved_working_directory": item.resolved_working_directory,
                "executable_id": item.executable_id,
                "policy_digest": item.policy_digest,
            }
            for item in authorizations
        ],
        "observations": [
            {
                "id": item.id,
                "action_id": item.action_id,
                "revision": item.revision,
                "started_at": item.started_at,
                "ended_at": item.ended_at,
                "exit_code": item.exit_code,
                "timed_out": item.timed_out,
                "stdout_digest": item.stdout_digest,
                "stderr_digest": item.stderr_digest,
                "stdout_artifact_id": item.stdout_artifact_id,
                "stderr_artifact_id": item.stderr_artifact_id,
                "environment_digest": item.environment_digest,
                "sandbox_id": item.sandbox_id,
                "sandbox_version": item.sandbox_version,
                "sandbox_digest": item.sandbox_digest,
                "sandbox_guarantees": list(item.sandbox_guarantees),
                "stdout_truncated": item.stdout_truncated,
                "stderr_truncated": item.stderr_truncated,
            }
            for item in observations
        ],
        "attempt_contexts": attempt_contexts,
        "proposals": [
            {
                "id": item.proposal.id,
                "generator_id": item.proposal.generator_id,
                "revision": item.proposal.revision,
                "source_digest": item.request.source_digest,
                "result_digest": item.result_digest,
                "attempt": item.proposal.attempt,
                "feedback": list(item.request.feedback),
                "response_artifact_id": item.response_artifact.id,
                "patch_artifact_id": item.patch_artifact.id,
                "claims": list(item.proposal.claims),
                "changed_paths": list(item.changed_paths),
            }
            for item in proposals
        ],
        "evidence": evidence_records,
        "findings": finding_records,
        "decision": decision_record,
        "metrics": {
            "verified_success": metrics.verified_success,
            "attempts": metrics.attempts,
            "wall_seconds": metrics.wall_seconds,
            "tokens": metrics.tokens,
            "estimated_cost": metrics.estimated_cost,
        },
        "artifacts": [
            {
                "id": item.id,
                "kind": item.kind,
                "path": item.path,
                "digest": item.digest,
                "size_bytes": item.size_bytes,
                "redacted": item.redacted,
            }
            for item in sorted(artifacts_by_id.values(), key=lambda artifact: artifact.id)
        ],
        "protocol_deviations": list(deviations),
    }


def encode_run_record(record: dict[str, Any]) -> bytes:
    """Return stable UTF-8 JSON bytes suitable for hashing and storage."""

    return (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def run_record_digest(record: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(encode_run_record(record)).hexdigest()
