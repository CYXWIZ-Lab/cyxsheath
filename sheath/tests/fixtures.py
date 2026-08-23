"""Small records shared by Stage-0 tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


BASE_TASK: dict[str, Any] = {
    "schema_version": "1.0.0",
    "task_id": "task-001",
    "raw_request": "Fix the parser regression without changing the public API.",
    "language": "python",
    "task_type": "bug_fix",
    "repository": {
        "source": "fixture/repository",
        "revision": "r1",
        "snapshot_digest": "sha256:fixture-r1",
        "license": "MIT",
        "collected_at": None,
    },
    "goal": "Restore parsing of escaped delimiters.",
    "constraints": [
        {
            "id": "constraint-api",
            "kind": "compatibility",
            "text": "Preserve the public API.",
            "hard": True,
            "source": "raw_request",
        }
    ],
    "success_criteria": [
        {
            "id": "criterion-tests",
            "text": "Regression and existing tests pass.",
            "verification": "python -m unittest",
        }
    ],
    "out_of_scope": ["Unrelated parser refactoring"],
    "unresolved_questions": [],
    "risk": {"level": "standard", "score": None, "reasons": ["behavior change"]},
    "allowed_tools": ["python"],
    "required_checks": ["scope.paths", "tests.regression"],
    "provenance": ["fixture"],
}


def task_record() -> dict[str, Any]:
    return deepcopy(BASE_TASK)
