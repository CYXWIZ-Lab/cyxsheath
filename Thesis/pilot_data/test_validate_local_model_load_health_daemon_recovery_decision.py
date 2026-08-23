from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_local_model_load_health_daemon_recovery_decision import DaemonRecoveryDecisionError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_local_model_load_health_daemon_recovery_decision.json"


class LocalModelLoadHealthDaemonRecoveryDecisionTests(unittest.TestCase):
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

    def test_attempt_two_ended_before_model_load(self) -> None:
        self.assertFalse(self.record["attempt_2"]["load_command_started"])
        self.assertTrue(self.record["manual_cleanup"]["activation_processes_absent_after"])

    def test_model_health_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["attempt_2"]["classification"] = "model_failed"
        with self.assertRaisesRegex(DaemonRecoveryDecisionError, "model-health overclaim"):
            validate(self.write_record(mutated))

    def test_nonzero_exit_cannot_prove_readiness(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["correction"]["nonzero_daemon_cli_exit_alone_proves_readiness"] = True
        with self.assertRaisesRegex(DaemonRecoveryDecisionError, "treated as readiness"):
            validate(self.write_record(mutated))

    def test_root_count_widening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["correction"]["readiness_requires_exact_service_root_count"] = 2
        with self.assertRaisesRegex(DaemonRecoveryDecisionError, "root-count gate drift"):
            validate(self.write_record(mutated))

    def test_manual_cleanup_failure_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["manual_cleanup"]["activation_processes_absent_after"] = False
        with self.assertRaisesRegex(DaemonRecoveryDecisionError, "manual cleanup failed"):
            validate(self.write_record(mutated))

    def test_load_setting_change_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["correction"]["all_original_model_resource_and_security_settings_unchanged"] = False
        with self.assertRaisesRegex(DaemonRecoveryDecisionError, "correction weakened"):
            validate(self.write_record(mutated))

    def test_premature_canary_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["authorization"]["synthetic_canary_authorized"] = True
        with self.assertRaisesRegex(DaemonRecoveryDecisionError, "authorization widened"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
