import json
from pathlib import Path
import unittest

from sheath import Evidence, EvidenceLedger, Finding, Severity, Verdict, decide
from sheath import task_contract_from_record

from fixtures import task_record


SCENARIO_PATH = Path(__file__).parent / "data" / "stage0_scenarios.json"


def load_scenarios() -> list[dict]:
    with SCENARIO_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


def execute_scenario(scenario: dict):
    record = task_record()
    record["task_id"] = scenario["id"]
    record.update(scenario.get("task_overrides", {}))
    contract = task_contract_from_record(record)
    ledger = EvidenceLedger(contract.repository.revision)

    for operation in scenario.get("operations", []):
        if operation["kind"] == "revision":
            ledger.record_revision(operation["revision"])
        elif operation["kind"] == "evidence":
            ledger.record_evidence(
                Evidence(
                    id=operation["id"],
                    check_id=operation["check_id"],
                    revision=ledger.current_revision,
                    passed=operation["passed"],
                    source=operation["source"],
                    detail=operation.get("detail", ""),
                )
            )
        else:
            raise AssertionError(f"unsupported fixture operation: {operation['kind']}")

    findings = tuple(
        Finding(
            id=item["id"],
            category=item["category"],
            severity=Severity(item["severity"]),
            message=item["message"],
            evidence_ids=tuple(item.get("evidence_ids", [])),
            source=item.get("source", "rule"),
        )
        for item in scenario.get("findings", [])
    )
    return contract, ledger, decide(contract, ledger, findings)


class ScenarioTests(unittest.TestCase):
    def test_fixture_inventory_is_frozen_and_balanced(self) -> None:
        scenarios = load_scenarios()
        ids = [item["id"] for item in scenarios]
        verdicts = [item["expected"]["verdict"] for item in scenarios]

        self.assertEqual(len(scenarios), 20)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            {verdict: verdicts.count(verdict) for verdict in Verdict},
            {
                Verdict.ACCEPT: 5,
                Verdict.REVISE: 10,
                Verdict.BLOCK: 1,
                Verdict.ESCALATE: 4,
            },
        )
        self.assertTrue(all(item["description"].strip() for item in scenarios))

    def test_all_scenarios_produce_exact_expected_decisions(self) -> None:
        for scenario in load_scenarios():
            with self.subTest(scenario=scenario["id"]):
                contract, ledger, decision = execute_scenario(scenario)
                expected = scenario["expected"]

                self.assertEqual(decision.verdict.value, expected["verdict"])
                self.assertEqual(list(decision.reason_codes), expected["reason_codes"])
                self.assertTrue(
                    all(ledger.has_evidence(item) for item in decision.evidence_ids)
                )
                if decision.verdict is Verdict.ACCEPT:
                    self.assertEqual(
                        len(decision.evidence_ids),
                        len(contract.required_checks),
                    )


if __name__ == "__main__":
    unittest.main()
