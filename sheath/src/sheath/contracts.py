"""Typed task-contract boundary for the Stage-0 supervisor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class ContractError(ValueError):
    """Raised when a task record cannot form a safe, auditable contract."""


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    source: str
    revision: str
    snapshot_digest: str


@dataclass(frozen=True, slots=True)
class Constraint:
    id: str
    kind: str
    text: str
    hard: bool
    source: str | None = None


@dataclass(frozen=True, slots=True)
class SuccessCriterion:
    id: str
    text: str
    verification: str


@dataclass(frozen=True, slots=True)
class TaskContract:
    schema_version: str
    task_id: str
    raw_request: str
    repository: RepositorySnapshot
    goal: str
    constraints: tuple[Constraint, ...]
    success_criteria: tuple[SuccessCriterion, ...]
    out_of_scope: tuple[str, ...]
    unresolved_questions: tuple[str, ...]
    risk_level: str
    allowed_tools: tuple[str, ...]
    required_checks: tuple[str, ...]

    def __post_init__(self) -> None:
        tuple_fields = (
            "constraints",
            "success_criteria",
            "out_of_scope",
            "unresolved_questions",
            "allowed_tools",
            "required_checks",
        )
        for name in tuple_fields:
            if not isinstance(getattr(self, name), tuple):
                raise TypeError(f"{name} must be a tuple")


_REQUIRED_FIELDS = {
    "schema_version",
    "task_id",
    "raw_request",
    "repository",
    "goal",
    "constraints",
    "success_criteria",
    "out_of_scope",
    "risk",
    "allowed_tools",
}

_CONSTRAINT_KINDS = {
    "scope",
    "architecture",
    "compatibility",
    "security",
    "safety",
    "performance",
    "style",
    "authorization",
    "other",
}

_RISK_LEVELS = {"light", "standard", "deep"}


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{field} must be an object")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a non-empty string")
    return value


def _string_tuple(value: Any, field: str, *, unique: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ContractError(f"{field} must be an array")
    items = tuple(_text(item, f"{field}[]") for item in value)
    if unique and len(items) != len(set(items)):
        raise ContractError(f"{field} must contain unique values")
    return items


def _unique_ids(items: tuple[Any, ...], field: str) -> None:
    ids = tuple(item.id for item in items)
    if len(ids) != len(set(ids)):
        raise ContractError(f"{field} IDs must be unique")


def task_contract_from_record(record: Mapping[str, Any]) -> TaskContract:
    """Build an immutable contract from a task-record-shaped mapping.

    JSON Schema remains the complete interchange specification. This function
    enforces the fields needed by the Stage-0 decision boundary and fails
    closed when they are missing or malformed.
    """

    record = _mapping(record, "task record")
    missing = sorted(_REQUIRED_FIELDS - record.keys())
    if missing:
        raise ContractError(f"missing required fields: {', '.join(missing)}")

    schema_version = _text(record["schema_version"], "schema_version")
    if schema_version != "1.0.0":
        raise ContractError(f"unsupported schema_version: {schema_version}")

    repository_record = _mapping(record["repository"], "repository")
    repository = RepositorySnapshot(
        source=_text(repository_record.get("source"), "repository.source"),
        revision=_text(repository_record.get("revision"), "repository.revision"),
        snapshot_digest=_text(
            repository_record.get("snapshot_digest"),
            "repository.snapshot_digest",
        ),
    )

    constraints: list[Constraint] = []
    raw_constraints = record["constraints"]
    if not isinstance(raw_constraints, list):
        raise ContractError("constraints must be an array")
    for index, raw in enumerate(raw_constraints):
        item = _mapping(raw, f"constraints[{index}]")
        hard = item.get("hard")
        if not isinstance(hard, bool):
            raise ContractError(f"constraints[{index}].hard must be boolean")
        kind = _text(item.get("kind"), f"constraints[{index}].kind")
        if kind not in _CONSTRAINT_KINDS:
            raise ContractError(f"constraints[{index}].kind is unsupported: {kind}")
        source = item.get("source")
        if source is not None:
            source = _text(source, f"constraints[{index}].source")
        constraints.append(
            Constraint(
                id=_text(item.get("id"), f"constraints[{index}].id"),
                kind=kind,
                text=_text(item.get("text"), f"constraints[{index}].text"),
                hard=hard,
                source=source,
            )
        )

    criteria: list[SuccessCriterion] = []
    raw_criteria = record["success_criteria"]
    if not isinstance(raw_criteria, list) or not raw_criteria:
        raise ContractError("success_criteria must be a non-empty array")
    for index, raw in enumerate(raw_criteria):
        item = _mapping(raw, f"success_criteria[{index}]")
        criteria.append(
            SuccessCriterion(
                id=_text(item.get("id"), f"success_criteria[{index}].id"),
                text=_text(item.get("text"), f"success_criteria[{index}].text"),
                verification=_text(
                    item.get("verification"),
                    f"success_criteria[{index}].verification",
                ),
            )
        )

    constraints_tuple = tuple(constraints)
    criteria_tuple = tuple(criteria)
    _unique_ids(constraints_tuple, "constraint")
    _unique_ids(criteria_tuple, "success criterion")

    risk_record = _mapping(record["risk"], "risk")
    risk_level = _text(risk_record.get("level"), "risk.level")
    if risk_level not in _RISK_LEVELS:
        raise ContractError(f"unsupported risk.level: {risk_level}")

    return TaskContract(
        schema_version=schema_version,
        task_id=_text(record["task_id"], "task_id"),
        raw_request=_text(record["raw_request"], "raw_request"),
        repository=repository,
        goal=_text(record["goal"], "goal"),
        constraints=constraints_tuple,
        success_criteria=criteria_tuple,
        out_of_scope=_string_tuple(record["out_of_scope"], "out_of_scope"),
        unresolved_questions=_string_tuple(
            record.get("unresolved_questions", []),
            "unresolved_questions",
        ),
        risk_level=risk_level,
        allowed_tools=_string_tuple(record["allowed_tools"], "allowed_tools", unique=True),
        required_checks=_string_tuple(
            record.get("required_checks", []),
            "required_checks",
            unique=True,
        ),
    )
