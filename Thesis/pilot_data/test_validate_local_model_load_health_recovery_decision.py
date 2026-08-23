from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_local_model_load_health_recovery_decision import LoadHealthRecoveryDecisionError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_local_model_load_health_recovery_decision.json"


class LocalModelLoadHealthRecoveryDecisionTests(unittest.TestCase):
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

    def test_attempt_one_ended_before_model_activation(self) -> None:
        self.assertFalse(self.record["attempt_1"]["load_command_started"])
        self.assertTrue(self.record["execution_gate"]["recovery_load_health_check_authorized_once"])

    def test_model_failure_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["attempt_1"]["classification"] = "model_failure"
        with self.assertRaisesRegex(LoadHealthRecoveryDecisionError, "classification drift"):
            validate(self.write_record(mutated))

    def test_measurement_attempt_widening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["retry_delta"]["gpu_measurement_attempts_per_sample"] = 10
        with self.assertRaisesRegex(LoadHealthRecoveryDecisionError, "retries widened"):
            validate(self.write_record(mutated))

    def test_missing_gpu_measurement_fallback_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["retry_delta"]["fallback_without_gpu_measurement_allowed"] = True
        with self.assertRaisesRegex(LoadHealthRecoveryDecisionError, "missing GPU measurement admitted"):
            validate(self.write_record(mutated))

    def test_cleanup_failure_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["attempt_1"]["activation_processes_absent_after"] = False
        with self.assertRaisesRegex(LoadHealthRecoveryDecisionError, "attempt cleanup failed"):
            validate(self.write_record(mutated))

    def test_load_setting_change_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["retry_delta"]["all_original_model_and_resource_settings_unchanged"] = False
        with self.assertRaisesRegex(LoadHealthRecoveryDecisionError, "original contract changed"):
            validate(self.write_record(mutated))

    def test_premature_canary_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["authorization"]["synthetic_canary_authorized"] = True
        with self.assertRaisesRegex(LoadHealthRecoveryDecisionError, "authorization widened"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
