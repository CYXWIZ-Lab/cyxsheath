from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_local_model_activation_preflight import ActivationPreflightError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_local_model_activation_preflight.json"


class LocalModelActivationPreflightTests(unittest.TestCase):
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

    def test_verified_weight_remains_non_benchmark(self) -> None:
        self.assertTrue(self.record["download"]["digest_verified_before_import"])
        self.assertFalse(self.record["execution_gate"]["benchmark_input_authorized"])

    def test_weight_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["download"]["actual_sha256"] = "0" * 64
        with self.assertRaisesRegex(ActivationPreflightError, "actual weight digest drift"):
            validate(self.write_record(mutated))

    def test_duplicate_weight_copy_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["import"]["duplicate_weight_copy_created"] = True
        with self.assertRaisesRegex(ActivationPreflightError, "duplicate weight copy"):
            validate(self.write_record(mutated))

    def test_tool_use_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["inventory"]["trained_for_tool_use"] = True
        with self.assertRaisesRegex(ActivationPreflightError, "tool-use capability overclaim"):
            validate(self.write_record(mutated))

    def test_context_ceiling_increase_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["inventory"]["effective_canary_ceiling_tokens"] = 32768
        with self.assertRaisesRegex(ActivationPreflightError, "context ceiling widened"):
            validate(self.write_record(mutated))

    def test_estimator_anomaly_concealment_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["estimate"]["gpu_label_conflict_retained"] = False
        with self.assertRaisesRegex(ActivationPreflightError, "anomaly concealed"):
            validate(self.write_record(mutated))

    def test_premature_canary_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["synthetic_canary_authorized"] = True
        with self.assertRaisesRegex(ActivationPreflightError, "premature authorization"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
