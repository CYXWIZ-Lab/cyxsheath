from dataclasses import FrozenInstanceError
import unittest

from sheath import ContractError, task_contract_from_record

from fixtures import task_record


class ContractTests(unittest.TestCase):
    def test_builds_immutable_contract(self) -> None:
        contract = task_contract_from_record(task_record())

        self.assertEqual(contract.task_id, "task-001")
        self.assertEqual(contract.required_checks, ("scope.paths", "tests.regression"))
        with self.assertRaises(FrozenInstanceError):
            contract.goal = "changed"  # type: ignore[misc]

    def test_rejects_missing_required_field(self) -> None:
        record = task_record()
        del record["raw_request"]

        with self.assertRaisesRegex(ContractError, "raw_request"):
            task_contract_from_record(record)

    def test_rejects_duplicate_required_checks(self) -> None:
        record = task_record()
        record["required_checks"].append("scope.paths")

        with self.assertRaisesRegex(ContractError, "unique"):
            task_contract_from_record(record)

    def test_rejects_unknown_risk_level(self) -> None:
        record = task_record()
        record["risk"]["level"] = "extreme"

        with self.assertRaisesRegex(ContractError, "risk.level"):
            task_contract_from_record(record)


if __name__ == "__main__":
    unittest.main()
