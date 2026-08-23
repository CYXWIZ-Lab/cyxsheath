"""Pure Stage-0 decision policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .contracts import TaskContract
from .ledger import EvidenceLedger


class Verdict(str, Enum):
    ACCEPT = "accept"
    REVISE = "revise"
    BLOCK = "block"
    ESCALATE = "escalate"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    REVISION = "revision"
    BLOCKING = "blocking"
    ESCALATION = "escalation"


_FINDING_CATEGORIES = {
    "epistemic_gap",
    "constraint_violation",
    "scope_violation",
    "evidence_gap",
    "impact_gap",
    "unsafe_action",
    "engineering_defect",
    "no_violation",
    "other",
}


@dataclass(frozen=True, slots=True)
class Finding:
    id: str
    category: str
    severity: Severity
    message: str
    evidence_ids: tuple[str, ...] = ()
    source: str = "rule"
    constraint_id: str | None = None
    location: str | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        for name in ("id", "category", "message"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"finding {name} must be a non-empty string")
        if not isinstance(self.severity, Severity):
            raise TypeError("finding severity must be a Severity")
        if self.category not in _FINDING_CATEGORIES:
            raise ValueError(f"unsupported finding category: {self.category}")
        if not isinstance(self.evidence_ids, tuple) or any(
            not isinstance(item, str) or not item.strip()
            for item in self.evidence_ids
        ):
            raise TypeError("finding evidence_ids must be a tuple of non-empty strings")
        if self.source not in {"policy", "tool", "rule", "critic", "human"}:
            raise ValueError(f"unsupported finding source: {self.source}")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("finding confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class Decision:
    verdict: Verdict
    reason_codes: tuple[str, ...]
    evidence_ids: tuple[str, ...]


def _finding_ids(findings: Iterable[Finding]) -> tuple[str, ...]:
    return tuple(
        evidence_id
        for finding in findings
        for evidence_id in finding.evidence_ids
    )


def decide(
    contract: TaskContract,
    ledger: EvidenceLedger,
    findings: Iterable[Finding] = (),
) -> Decision:
    """Return a verdict using hard precedence and current mandatory evidence."""

    findings = tuple(findings)
    dangling_references = tuple(
        (finding.id, evidence_id)
        for finding in findings
        for evidence_id in finding.evidence_ids
        if not ledger.has_evidence(evidence_id)
    )
    if dangling_references:
        return Decision(
            verdict=Verdict.ESCALATE,
            reason_codes=tuple(
                f"finding.unknown_evidence:{finding_id}:{evidence_id}"
                for finding_id, evidence_id in dangling_references
            ),
            evidence_ids=(),
        )

    blocking = tuple(item for item in findings if item.severity is Severity.BLOCKING)
    if blocking:
        return Decision(
            verdict=Verdict.BLOCK,
            reason_codes=tuple(f"finding.blocking:{item.id}" for item in blocking),
            evidence_ids=_finding_ids(blocking),
        )

    if contract.unresolved_questions:
        return Decision(
            verdict=Verdict.ESCALATE,
            reason_codes=("contract.unresolved_material_question",),
            evidence_ids=(),
        )

    escalations = tuple(item for item in findings if item.severity is Severity.ESCALATION)
    if escalations:
        return Decision(
            verdict=Verdict.ESCALATE,
            reason_codes=tuple(f"finding.escalation:{item.id}" for item in escalations),
            evidence_ids=_finding_ids(escalations),
        )

    if not contract.required_checks:
        return Decision(
            verdict=Verdict.ESCALATE,
            reason_codes=("contract.no_required_checks",),
            evidence_ids=(),
        )

    revisions = tuple(item for item in findings if item.severity is Severity.REVISION)
    reasons = [f"finding.revision:{item.id}" for item in revisions]
    evidence_ids = list(_finding_ids(revisions))

    for check_id in contract.required_checks:
        current = ledger.evidence_for(check_id)
        if not current:
            previous = ledger.evidence_for(check_id, current_only=False)
            state = "stale" if previous else "missing"
            reasons.append(f"mandatory_check.{state}:{check_id}")
            continue
        latest = current[-1]
        evidence_ids.append(latest.id)
        if not latest.passed:
            reasons.append(f"mandatory_check.failed:{check_id}")

    if reasons:
        return Decision(
            verdict=Verdict.REVISE,
            reason_codes=tuple(reasons),
            evidence_ids=tuple(dict.fromkeys(evidence_ids)),
        )

    return Decision(
        verdict=Verdict.ACCEPT,
        reason_codes=("mandatory_checks.current_and_passed",),
        evidence_ids=tuple(
            ledger.evidence_for(check_id)[-1].id
            for check_id in contract.required_checks
        ),
    )
