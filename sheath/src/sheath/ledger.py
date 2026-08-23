"""Append-only, revision-aware evidence storage."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock


class LedgerError(ValueError):
    """Raised when an append would violate a ledger invariant."""


_EVIDENCE_SOURCES = {"policy", "tool", "rule", "critic", "human"}


@dataclass(frozen=True, slots=True)
class Evidence:
    id: str
    check_id: str
    revision: str
    passed: bool
    source: str
    detail: str = ""

    def __post_init__(self) -> None:
        for name in ("id", "check_id", "revision", "source"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise LedgerError(f"evidence {name} must be a non-empty string")
        if not isinstance(self.passed, bool):
            raise LedgerError("evidence passed must be boolean")
        if self.source not in _EVIDENCE_SOURCES:
            raise LedgerError(f"unsupported evidence source: {self.source}")


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    sequence: int
    kind: str
    timestamp: str
    revision: str
    evidence_id: str | None = None
    proposal_id: str | None = None
    content_artifact_id: str | None = None
    action_id: str | None = None
    authorization_id: str | None = None
    observation_id: str | None = None
    from_state: str | None = None
    to_state: str | None = None
    status: str | None = None


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class EvidenceLedger:
    """Records revisions and evidence without destructive updates."""

    def __init__(
        self,
        initial_revision: str,
        *,
        clock: Callable[[], str] | None = None,
    ) -> None:
        if not isinstance(initial_revision, str) or not initial_revision.strip():
            raise LedgerError("initial revision must be a non-empty string")
        self._lock = RLock()
        self._clock = clock or _utc_timestamp
        self._revision = initial_revision
        self._evidence: list[Evidence] = []
        self._evidence_ids: set[str] = set()
        self._proposal_ids: set[str] = set()
        self._events: list[LedgerEvent] = [
            LedgerEvent(
                sequence=0,
                kind="revision",
                timestamp=self._clock(),
                revision=initial_revision,
            )
        ]

    @property
    def current_revision(self) -> str:
        with self._lock:
            return self._revision

    @property
    def events(self) -> tuple[LedgerEvent, ...]:
        with self._lock:
            return tuple(self._events)

    @property
    def evidence(self) -> tuple[Evidence, ...]:
        with self._lock:
            return tuple(self._evidence)

    def has_evidence(self, evidence_id: str) -> bool:
        with self._lock:
            return evidence_id in self._evidence_ids

    def record_revision(self, revision: str) -> LedgerEvent:
        if not isinstance(revision, str) or not revision.strip():
            raise LedgerError("revision must be a non-empty string")
        with self._lock:
            if revision == self._revision:
                raise LedgerError("new revision must differ from current revision")
            self._revision = revision
            event = LedgerEvent(
                sequence=len(self._events),
                kind="revision",
                timestamp=self._clock(),
                revision=revision,
            )
            self._events.append(event)
            return event

    def record_evidence(self, evidence: Evidence) -> LedgerEvent:
        with self._lock:
            if evidence.id in self._evidence_ids:
                raise LedgerError(f"duplicate evidence ID: {evidence.id}")
            if evidence.revision != self._revision:
                raise LedgerError(
                    "evidence revision must equal the ledger's current revision"
                )
            self._evidence.append(evidence)
            self._evidence_ids.add(evidence.id)
            event = LedgerEvent(
                sequence=len(self._events),
                kind="evidence",
                timestamp=self._clock(),
                revision=evidence.revision,
                evidence_id=evidence.id,
            )
            self._events.append(event)
            return event

    def record_proposal(
        self,
        proposal_id: str,
        response_artifact_id: str,
    ) -> LedgerEvent:
        for value, field in (
            (proposal_id, "proposal_id"),
            (response_artifact_id, "response_artifact_id"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise LedgerError(f"{field} must be a non-empty string")
        with self._lock:
            if proposal_id in self._proposal_ids:
                raise LedgerError(f"duplicate proposal ID: {proposal_id}")
            event = LedgerEvent(
                sequence=len(self._events),
                kind="proposal",
                timestamp=self._clock(),
                revision=self._revision,
                proposal_id=proposal_id,
                content_artifact_id=response_artifact_id,
                status="recorded",
            )
            self._proposal_ids.add(proposal_id)
            self._events.append(event)
            return event

    def record_state_transition(
        self,
        from_state: str | None,
        to_state: str,
    ) -> LedgerEvent:
        if from_state is not None and (not isinstance(from_state, str) or not from_state):
            raise LedgerError("from_state must be null or a non-empty string")
        if not isinstance(to_state, str) or not to_state:
            raise LedgerError("to_state must be a non-empty string")
        with self._lock:
            event = LedgerEvent(
                sequence=len(self._events),
                kind="state_transition",
                timestamp=self._clock(),
                revision=self._revision,
                from_state=from_state,
                to_state=to_state,
            )
            self._events.append(event)
            return event

    def record_tool_request(
        self,
        action_id: str,
        authorization_id: str,
        *,
        allowed: bool,
    ) -> LedgerEvent:
        for value, field in (
            (action_id, "action_id"),
            (authorization_id, "authorization_id"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise LedgerError(f"{field} must be a non-empty string")
        if not isinstance(allowed, bool):
            raise LedgerError("allowed must be boolean")
        with self._lock:
            event = LedgerEvent(
                sequence=len(self._events),
                kind="tool_request",
                timestamp=self._clock(),
                revision=self._revision,
                action_id=action_id,
                authorization_id=authorization_id,
                status="allowed" if allowed else "blocked",
            )
            self._events.append(event)
            return event

    def record_tool_observation(
        self,
        action_id: str,
        observation_id: str,
        *,
        passed: bool,
    ) -> LedgerEvent:
        for value, field in (
            (action_id, "action_id"),
            (observation_id, "observation_id"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise LedgerError(f"{field} must be a non-empty string")
        if not isinstance(passed, bool):
            raise LedgerError("passed must be boolean")
        with self._lock:
            event = LedgerEvent(
                sequence=len(self._events),
                kind="tool_observation",
                timestamp=self._clock(),
                revision=self._revision,
                action_id=action_id,
                observation_id=observation_id,
                status="passed" if passed else "failed",
            )
            self._events.append(event)
            return event

    def record_tool_error(self, action_id: str, status: str) -> LedgerEvent:
        for value, field in ((action_id, "action_id"), (status, "status")):
            if not isinstance(value, str) or not value.strip():
                raise LedgerError(f"{field} must be a non-empty string")
        with self._lock:
            event = LedgerEvent(
                sequence=len(self._events),
                kind="error",
                timestamp=self._clock(),
                revision=self._revision,
                action_id=action_id,
                status=status,
            )
            self._events.append(event)
            return event

    def evidence_for(self, check_id: str, *, current_only: bool = True) -> tuple[Evidence, ...]:
        with self._lock:
            return tuple(
                item
                for item in self._evidence
                if item.check_id == check_id
                and (not current_only or item.revision == self._revision)
            )
