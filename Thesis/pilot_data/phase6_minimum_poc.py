"""Frozen task loading and isolated verification for the minimum paired POC."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
from typing import Callable

from sheath import (
    ArtifactStore,
    CommandAction,
    CommandPolicy,
    ConstrainedRunner,
    CoordinatorError,
    Evidence,
    EvidenceLedger,
    RunnerError,
    ToolSession,
    ValidatedProposal,
    VerificationReport,
    WorkspaceSnapshot,
    task_contract_from_record,
)


class MinimumPocError(ValueError):
    """Raised when the frozen task or verification boundary is invalid."""


@dataclass(frozen=True, slots=True)
class PocTask:
    task_id: str
    directory: str
    request: str
    source_root: Path
    hidden_script: str
    allowed_changed_paths: tuple[str, ...]
    condition_order: tuple[str, ...]


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise MinimumPocError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_tasks(manifest_path: Path) -> tuple[PocTask, ...]:
    """Load exactly the committed task files while keeping hidden tests unstaged."""

    manifest_path = Path(manifest_path).resolve(strict=True)
    record = json.loads(manifest_path.read_text(encoding="utf-8"))
    _expect(record["schema_version"] == "1.0.0", "unsupported task schema")
    _expect(record["pilot_id"] == "phase6-minimum-poc-v1", "pilot identity drift")
    _expect(record["model"] == "opencode/mimo-v2.5-free", "model drift")
    _expect(record["conditions"] == ["A", "D0"], "condition drift")
    _expect(record["model_timeout_seconds"] == 180, "model timeout drift")
    _expect(record["verification_timeout_seconds"] == 30, "verification timeout drift")
    rows = record["tasks"]
    _expect(isinstance(rows, list) and len(rows) == 3, "task count drift")

    tasks: list[PocTask] = []
    base = manifest_path.parent
    for row in rows:
        task_id = row["task_id"]
        directory = row["directory"]
        _expect(isinstance(task_id, str) and task_id.startswith("phase6-poc-"), "task ID invalid")
        _expect(isinstance(directory, str) and Path(directory).name == directory, "task directory invalid")
        task_root = (base / directory).resolve(strict=True)
        _expect(task_root.parent == base, "task directory escaped manifest root")
        source = (task_root / "source").resolve(strict=True)
        hidden = (task_root / "hidden_tests.py").resolve(strict=True)
        _expect(source.is_dir() and hidden.is_file(), "task files missing")
        _expect(hidden.parent == task_root and not hidden.is_relative_to(source), "hidden tests entered source")
        expected_files = row["source_files"]
        actual_files = tuple(sorted(path.name for path in source.iterdir() if path.is_file()))
        _expect(actual_files == tuple(sorted(expected_files)), "source file set drift")
        _expect(not any(path.is_dir() for path in source.iterdir()), "source directory contamination")
        for name, digest in expected_files.items():
            _expect(_sha256(source / name) == digest, f"source digest drift: {task_id}:{name}")
        _expect(_sha256(hidden) == row["hidden_tests_sha256"], f"hidden digest drift: {task_id}")
        allowed = tuple(row["allowed_changed_paths"])
        order = tuple(row["condition_order"])
        _expect(len(allowed) == 1 and allowed[0] in expected_files, "allowed path drift")
        _expect(order in (("A", "D0"), ("D0", "A")), "condition order invalid")
        request = row["request"]
        _expect(isinstance(request, str) and request.strip(), "task request invalid")
        tasks.append(
            PocTask(
                task_id=task_id,
                directory=directory,
                request=request,
                source_root=source,
                hidden_script=hidden.read_text(encoding="utf-8"),
                allowed_changed_paths=allowed,
                condition_order=order,
            )
        )
    _expect(len({task.task_id for task in tasks}) == len(tasks), "duplicate task ID")
    return tuple(tasks)


def build_contract(task: PocTask, snapshot_digest: str):
    return task_contract_from_record(
        {
            "schema_version": "1.0.0",
            "task_id": task.task_id,
            "raw_request": task.request,
            "repository": {
                "source": f"synthetic://cyxsheath/{task.task_id}",
                "revision": f"{task.task_id}-v1",
                "snapshot_digest": snapshot_digest,
            },
            "goal": "Produce the smallest correct repair for the declared behavior.",
            "constraints": [
                {
                    "id": "constraint-scope",
                    "kind": "scope",
                    "text": f"Modify only {task.allowed_changed_paths[0]}.",
                    "hard": True,
                    "source": "phase6 minimum POC protocol",
                },
                {
                    "id": "constraint-no-external-context",
                    "kind": "authorization",
                    "text": "Use only the staged task files; do not seek external solutions.",
                    "hard": True,
                    "source": "phase6 minimum POC protocol",
                },
            ],
            "success_criteria": [
                {"id": "criterion-visible", "text": "Visible tests pass.", "verification": "tests.visible"},
                {"id": "criterion-hidden", "text": "Blinded edge-case tests pass.", "verification": "tests.hidden"},
            ],
            "out_of_scope": ["Dependency changes", "External repositories", "Hidden test discovery"],
            "unresolved_questions": [],
            "risk": {"level": "light"},
            "allowed_tools": ["read", "search", "edit", "shell"],
            "required_checks": ["scope.paths", "tests.visible", "tests.hidden"],
        }
    )


class PocVerifier:
    """Score scope and fixed visible/hidden checks in an injected sandbox."""

    def __init__(
        self,
        task: PocTask,
        policy: CommandPolicy,
        backend: object | Callable[[WorkspaceSnapshot], object],
    ) -> None:
        _expect(isinstance(task, PocTask), "verifier task invalid")
        _expect(isinstance(policy, CommandPolicy), "verifier policy invalid")
        self._task = task
        self._policy = policy
        self._backend = backend

    def verify(
        self,
        proposal: ValidatedProposal,
        snapshot: WorkspaceSnapshot,
        ledger: EvidenceLedger,
        store: ArtifactStore,
    ) -> VerificationReport:
        if not isinstance(proposal, ValidatedProposal):
            raise CoordinatorError("POC verification requires a validated proposal")
        policy = replace(self._policy, workspace_root=snapshot.root)
        backend = self._backend(snapshot) if callable(self._backend) else self._backend
        session = ToolSession(policy, ledger, store)
        runner = ConstrainedRunner(session, backend)  # type: ignore[arg-type]
        attempt = proposal.request.attempt
        scope = Evidence(
            id=f"evidence:scope:{attempt}",
            check_id="scope.paths",
            revision=proposal.request.revision,
            passed=bool(proposal.changed_paths)
            and set(proposal.changed_paths).issubset(self._task.allowed_changed_paths),
            source="rule",
            detail=f"changed_path_count={len(proposal.changed_paths)}",
        )
        checks = (
            (
                CommandAction(
                    id=f"poc-visible:attempt-{attempt}",
                    argv=("python", "-m", "unittest", "-v"),
                    timeout_seconds=30,
                    max_output_bytes=65_536,
                ),
                ("tests.visible",),
            ),
            (
                CommandAction(
                    id=f"poc-hidden:attempt-{attempt}",
                    argv=("python", "-c", self._task.hidden_script),
                    timeout_seconds=30,
                    max_output_bytes=65_536,
                ),
                ("tests.hidden",),
            ),
        )
        findings = []
        for action, check_ids in checks:
            try:
                outcome = runner.execute(action, check_ids)
            except RunnerError as error:
                raise CoordinatorError(f"POC verification failed: {error}") from error
            if not outcome.authorization.allowed:
                break
        return VerificationReport((scope,), tuple(findings), session)


def curate_run(record: dict, record_digest: str, condition: str) -> dict[str, object]:
    """Reduce one canonical run record to public task-level measurements."""

    metrics = record["metrics"]
    decision = record["decision"]
    failed = decision["verdict"] == "failed"
    return {
        "condition": condition,
        "status": "infrastructure_failure" if failed else "completed",
        "verified_success": bool(metrics["verified_success"]),
        "verdict": decision["verdict"],
        "attempts": metrics["attempts"],
        "wall_seconds": metrics["wall_seconds"],
        "recovered_after_first_attempt": condition == "D0" and metrics["attempts"] == 2 and bool(metrics["verified_success"]),
        "record_digest": record_digest,
        "failure_reason_codes": list(decision["reason_codes"]) if failed else [],
    }
