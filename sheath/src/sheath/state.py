"""Explicit run-state transitions for the Stage-0 workflow."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .decision import Decision, Verdict
from .ledger import EvidenceLedger


class StateError(ValueError):
    """Raised when a workflow attempts an invalid state transition."""


class RunState(str, Enum):
    RECEIVED = "received"
    CONTRACTED = "contracted"
    TRIAGED = "triaged"
    PROPOSED = "proposed"
    ACTION_VALIDATION = "action_validation"
    EXECUTED = "executed"
    ASSESSED = "assessed"
    REVISION_REQUIRED = "revision_required"
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    VERIFIED = "verified"
    EXPORTED = "exported"


@dataclass(frozen=True, slots=True)
class StateTransition:
    sequence: int
    timestamp: str
    from_state: RunState | None
    to_state: RunState


_ALLOWED: dict[RunState, frozenset[RunState]] = {
    RunState.RECEIVED: frozenset({RunState.CONTRACTED}),
    RunState.CONTRACTED: frozenset({RunState.TRIAGED}),
    RunState.TRIAGED: frozenset({RunState.PROPOSED}),
    RunState.PROPOSED: frozenset({RunState.ACTION_VALIDATION}),
    RunState.ACTION_VALIDATION: frozenset({RunState.BLOCKED, RunState.EXECUTED}),
    RunState.EXECUTED: frozenset({RunState.ASSESSED}),
    RunState.ASSESSED: frozenset(
        {
            RunState.REVISION_REQUIRED,
            RunState.BLOCKED,
            RunState.ESCALATED,
            RunState.VERIFIED,
        }
    ),
    RunState.REVISION_REQUIRED: frozenset({RunState.PROPOSED, RunState.EXPORTED}),
    RunState.BLOCKED: frozenset({RunState.EXPORTED}),
    RunState.ESCALATED: frozenset({RunState.EXPORTED}),
    RunState.VERIFIED: frozenset({RunState.EXPORTED}),
    RunState.EXPORTED: frozenset(),
}

_DECISION_STATE = {
    Verdict.ACCEPT: RunState.VERIFIED,
    Verdict.REVISE: RunState.REVISION_REQUIRED,
    Verdict.BLOCK: RunState.BLOCKED,
    Verdict.ESCALATE: RunState.ESCALATED,
}


class RunStateMachine:
    """Owns workflow state while writing every transition to the audit ledger."""

    def __init__(self, ledger: EvidenceLedger) -> None:
        self._ledger = ledger
        self._state = RunState.RECEIVED
        initial = ledger.record_state_transition(None, self._state.value)
        self._transitions: list[StateTransition] = [
            StateTransition(
                sequence=initial.sequence,
                timestamp=initial.timestamp,
                from_state=None,
                to_state=self._state,
            )
        ]

    @property
    def state(self) -> RunState:
        return self._state

    @property
    def transitions(self) -> tuple[StateTransition, ...]:
        return tuple(self._transitions)

    @property
    def ledger(self) -> EvidenceLedger:
        return self._ledger

    def transition(self, to_state: RunState) -> StateTransition:
        if not isinstance(to_state, RunState):
            raise TypeError("to_state must be a RunState")
        if to_state not in _ALLOWED[self._state]:
            raise StateError(f"invalid transition: {self._state.value} -> {to_state.value}")
        from_state = self._state
        event = self._ledger.record_state_transition(from_state.value, to_state.value)
        self._state = to_state
        transition = StateTransition(
            sequence=event.sequence,
            timestamp=event.timestamp,
            from_state=from_state,
            to_state=to_state,
        )
        self._transitions.append(transition)
        return transition

    def apply_decision(self, decision: Decision) -> StateTransition:
        if self._state is not RunState.ASSESSED:
            raise StateError("a decision can be applied only from assessed")
        return self.transition(_DECISION_STATE[decision.verdict])
