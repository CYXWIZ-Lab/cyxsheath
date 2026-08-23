"""Minimal, side-effect-free use of the Sheath Stage-0 decision boundary."""

from __future__ import annotations

import json

from sheath import Evidence, EvidenceLedger, decide, task_contract_from_record


def main() -> None:
    contract = task_contract_from_record(
        {
            "schema_version": "1.0.0",
            "task_id": "usage-stage0-decision",
            "raw_request": "Change one in-scope file and run its regression test.",
            "repository": {
                "source": "fixture/repository",
                "revision": "r1",
                "snapshot_digest": "sha256:usage-r1",
            },
            "goal": "Demonstrate a fail-closed Stage-0 decision.",
            "constraints": [
                {
                    "id": "constraint-scope",
                    "kind": "scope",
                    "text": "Only arithmetic.py may change.",
                    "hard": True,
                    "source": "usage example",
                }
            ],
            "success_criteria": [
                {
                    "id": "criterion-tests",
                    "text": "The regression test passes.",
                    "verification": "python -m unittest",
                }
            ],
            "out_of_scope": ["Network access", "Dependency changes"],
            "unresolved_questions": [],
            "risk": {"level": "light"},
            "allowed_tools": ["python"],
            "required_checks": ["scope.paths", "tests.regression"],
        }
    )

    ledger = EvidenceLedger(contract.repository.revision)
    ledger.record_evidence(
        Evidence(
            id="evidence-scope",
            check_id="scope.paths",
            revision="r1",
            passed=True,
            source="rule",
            detail="Only arithmetic.py changed.",
        )
    )
    ledger.record_evidence(
        Evidence(
            id="evidence-tests",
            check_id="tests.regression",
            revision="r1",
            passed=True,
            source="tool",
            detail="The regression test exited successfully.",
        )
    )

    decision = decide(contract, ledger)
    print(
        json.dumps(
            {
                "evidence_ids": list(decision.evidence_ids),
                "reason_codes": list(decision.reason_codes),
                "verdict": decision.verdict.value,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
