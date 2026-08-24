from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_local_engine_cli_recovery_result import EngineCliRecoveryResultError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_local_engine_cli_recovery_result.json"


class LocalEngineCliRecoveryResultTests(unittest.TestCase):
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

    def test_attempt_stopped_before_model_load(self) -> None:
        self.assertEqual(self.record["authorized_attempt"]["model_load_command_invocation_count"], 0)
        self.assertFalse(self.record["acceptance"]["load_health_gate_passed"])

    def test_prelaunch_block_cannot_consume_attempt(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["prelaunch_event"]["counts_as_authorized_attempt"] = True
        with self.assertRaisesRegex(EngineCliRecoveryResultError, "prelaunch overclaim"):
            validate(self.write_record(mutated))

    def test_missing_exit_cannot_be_concealed(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["authorized_attempt"]["daemon_client_numeric_exit_captured"] = True
        with self.assertRaisesRegex(EngineCliRecoveryResultError, "daemon exit overclaim"):
            validate(self.write_record(mutated))

    def test_model_activation_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["authorized_attempt"]["model_activation_observed"] = True
        with self.assertRaisesRegex(EngineCliRecoveryResultError, "model activation overclaim"):
            validate(self.write_record(mutated))

    def test_lock_resolution_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cli_lifecycle_outcome"]["extraction_lock_resolution_conclusion_allowed"] = True
        with self.assertRaisesRegex(EngineCliRecoveryResultError, "lock resolution overclaim"):
            validate(self.write_record(mutated))

    def test_forced_cleanup_concealment_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cleanup"]["forced_cleanup_required"] = False
        with self.assertRaisesRegex(EngineCliRecoveryResultError, "forced cleanup concealed"):
            validate(self.write_record(mutated))

    def test_resource_conclusion_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["resource_observation"]["resource_gate_conclusion_allowed"] = True
        with self.assertRaisesRegex(EngineCliRecoveryResultError, "resource conclusion overclaim"):
            validate(self.write_record(mutated))

    def test_automatic_retry_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["automatic_retry_authorized"] = True
        with self.assertRaisesRegex(EngineCliRecoveryResultError, "premature authorization"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
