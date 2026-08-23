from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_synthetic_canary_gate import SyntheticCanaryGateError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_synthetic_canary_gate.json"


class SyntheticCanaryGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def write_record(self, record: dict) -> Path:
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False
        )
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return Path(handle.name)

    def test_free_synthetic_route_is_bounded(self) -> None:
        self.assertEqual("free", self.record["provider"]["cost_class"])
        self.assertEqual(1, self.record["execution_gate"]["maximum_attempts"])
        self.assertFalse(self.record["execution_gate"]["benchmark_input_authorized"])
        self.assertTrue(self.record["outcome"]["synthetic_canary_executed"])

    def test_raw_content_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["prompt"] = "must not be retained"
        with self.assertRaisesRegex(SyntheticCanaryGateError, "forbidden raw-content"):
            validate(self.write_record(mutated))

    def test_benchmark_classification_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["input_classification"]["contains_benchmark_data"] = True
        with self.assertRaisesRegex(SyntheticCanaryGateError, "contains_benchmark_data"):
            validate(self.write_record(mutated))

    def test_paid_route_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["provider"]["cost_class"] = "paid"
        with self.assertRaisesRegex(SyntheticCanaryGateError, "paid route"):
            validate(self.write_record(mutated))

    def test_benchmark_admission_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["provider"]["benchmark_submission"] = "approved"
        with self.assertRaisesRegex(SyntheticCanaryGateError, "unsafe benchmark admission"):
            validate(self.write_record(mutated))

    def test_second_attempt_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["maximum_attempts"] = 2
        with self.assertRaisesRegex(SyntheticCanaryGateError, "attempt limit"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
