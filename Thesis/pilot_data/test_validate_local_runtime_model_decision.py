from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_local_runtime_model_decision import RuntimeModelDecisionError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_local_runtime_model_decision.json"


class LocalRuntimeModelDecisionTests(unittest.TestCase):
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

    def test_exact_synthetic_selection_is_pending(self) -> None:
        self.assertEqual("Q4_K_M", self.record["model"]["quantization"])
        self.assertEqual("blocked", self.record["model"]["benchmark_use"])
        self.assertFalse(self.record["execution_gate"]["synthetic_canary_authorized_now"])

    def test_raw_benchmark_content_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["problem_statement"] = "must not be retained"
        with self.assertRaisesRegex(RuntimeModelDecisionError, "forbidden keys"):
            validate(self.write_record(mutated))

    def test_weight_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["model"]["weight_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeModelDecisionError, "weight digest drift"):
            validate(self.write_record(mutated))

    def test_benchmark_use_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["model"]["benchmark_use"] = "allowed"
        with self.assertRaisesRegex(RuntimeModelDecisionError, "benchmark model use"):
            validate(self.write_record(mutated))

    def test_context_ceiling_increase_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["resource_policy"]["context_length_tokens"] = 32768
        with self.assertRaisesRegex(RuntimeModelDecisionError, "context_length_tokens"):
            validate(self.write_record(mutated))

    def test_authentication_removal_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["api"]["authentication_required"] = False
        with self.assertRaisesRegex(RuntimeModelDecisionError, "authentication weakened"):
            validate(self.write_record(mutated))

    def test_premature_canary_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["synthetic_canary_authorized_now"] = True
        with self.assertRaisesRegex(RuntimeModelDecisionError, "before activation checks"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
