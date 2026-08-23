"""Tool-backed verification adapter for a validated generator proposal."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from .artifacts import ArtifactStore
from .coordinator import CoordinatorError, VerificationReport
from .decision import Finding, Severity
from .generator import ValidatedProposal
from .ledger import EvidenceLedger
from .runner import ConstrainedRunner, RunnerError, SandboxBackend
from .snapshots import WorkspaceSnapshot
from .tools import CommandAction, CommandPolicy, ToolSession


@dataclass(frozen=True, slots=True)
class ToolCheck:
    """One authorized command and the mandatory checks it can observe."""

    action: CommandAction
    check_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.action, CommandAction):
            raise TypeError("tool check action must be a CommandAction")
        if not isinstance(self.check_ids, tuple) or not self.check_ids:
            raise TypeError("tool check check_ids must be a non-empty tuple")
        if any(not isinstance(item, str) or not item.strip() for item in self.check_ids):
            raise ValueError("tool check IDs must be non-empty strings")
        if len(self.check_ids) != len(set(self.check_ids)):
            raise ValueError("tool check IDs must be unique")


class ToolBackedVerifier:
    """Execute fixed checks through a backend or per-snapshot backend factory."""

    def __init__(
        self,
        policy: CommandPolicy,
        backend: SandboxBackend | Callable[[WorkspaceSnapshot], SandboxBackend],
        checks: tuple[ToolCheck, ...],
    ) -> None:
        if not isinstance(policy, CommandPolicy):
            raise TypeError("policy must be a CommandPolicy")
        if not isinstance(checks, tuple) or not checks:
            raise TypeError("checks must be a non-empty tuple")
        if any(not isinstance(item, ToolCheck) for item in checks):
            raise TypeError("checks must contain ToolCheck values")
        action_ids = tuple(item.action.id for item in checks)
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("tool check action IDs must be unique")
        self._policy = policy
        self._backend = backend
        self._checks = checks

    def verify(
        self,
        proposal: ValidatedProposal,
        snapshot: WorkspaceSnapshot,
        ledger: EvidenceLedger,
        store: ArtifactStore,
    ) -> VerificationReport:
        if not isinstance(proposal, ValidatedProposal):
            raise CoordinatorError("tool verification requires a validated proposal")
        if not isinstance(snapshot, WorkspaceSnapshot) or snapshot.closed:
            raise CoordinatorError("tool verification requires an active snapshot")
        if not isinstance(ledger, EvidenceLedger):
            raise CoordinatorError("tool verification requires an EvidenceLedger")
        if not isinstance(store, ArtifactStore):
            raise CoordinatorError("tool verification requires an ArtifactStore")

        policy = replace(self._policy, workspace_root=snapshot.root)
        try:
            backend = self._backend(snapshot) if callable(self._backend) else self._backend
        except Exception as error:
            raise CoordinatorError("tool backend factory failed") from error
        session = ToolSession(policy, ledger, store)
        runner = ConstrainedRunner(session, backend)
        findings: list[Finding] = []
        for check in self._checks:
            action = check.action
            if proposal.request.attempt > 1:
                action = replace(
                    action,
                    id=f"{action.id}:attempt-{proposal.request.attempt}",
                )
            try:
                outcome = runner.execute(action, check.check_ids)
            except RunnerError as error:
                findings.append(
                    Finding(
                        id=f"finding:runner:{action.id}",
                        category="other",
                        severity=Severity.ESCALATION,
                        message=f"Runner could not complete {action.id}: {error}",
                        source="tool",
                    )
                )
                break
            if not outcome.authorization.allowed:
                break
        return VerificationReport((), tuple(findings), session)
