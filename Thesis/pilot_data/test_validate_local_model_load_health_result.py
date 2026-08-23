from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_local_model_load_health_result import LoadHealthResultError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_local_model_load_health_result.json"


class LocalModelLoadHealthResultTests(unittest.TestCase):
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

    def test_activation_is_observed_but_not_accepted(self) -> None:
        self.assertTrue(self.record["acceptance"]["model_activation_observed"])
        self.assertFalse(self.record["acceptance"]["load_health_gate_passed"])

    def test_engine_drift_concealment_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["runtime_drift"]["engine_identity_matches_decision"] = True
        with self.assertRaisesRegex(LoadHealthResultError, "engine drift concealed"):
            validate(self.write_record(mutated))

    def test_load_exit_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["attempt_3"]["load_command_exit_zero"] = True
        with self.assertRaisesRegex(LoadHealthResultError, "load-client failure concealed"):
            validate(self.write_record(mutated))

    def test_observation_window_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["acceptance"]["observation_window_gate_passed"] = True
        with self.assertRaisesRegex(LoadHealthResultError, "protocol acceptance overclaim"):
            validate(self.write_record(mutated))

    def test_cleanup_failure_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cleanup"]["activation_processes_absent_after"] = False
        with self.assertRaisesRegex(LoadHealthResultError, "cleanup failed"):
            validate(self.write_record(mutated))

    def test_retry_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["automatic_retry_authorized"] = True
        with self.assertRaisesRegex(LoadHealthResultError, "premature authorization"):
            validate(self.write_record(mutated))

    def test_premature_canary_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["synthetic_canary_authorized"] = True
        with self.assertRaisesRegex(LoadHealthResultError, "premature authorization"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
