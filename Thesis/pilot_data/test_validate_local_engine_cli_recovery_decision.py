from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_local_engine_cli_recovery_decision import EngineCliRecoveryDecisionError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_local_engine_cli_recovery_decision.json"


class LocalEngineCliRecoveryDecisionTests(unittest.TestCase):
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

    def test_exact_engine_and_single_retry_are_authorized(self) -> None:
        self.assertEqual(self.record["engine_decision"]["version"], "2.29.1")
        self.assertTrue(self.record["execution_gate"]["fresh_load_health_execution_authorized_once"])

    def test_engine_downgrade_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["engine_decision"]["version"] = "2.28.2"
        with self.assertRaisesRegex(EngineCliRecoveryDecisionError, "engine version drift"):
            validate(self.write_record(mutated))

    def test_runtime_installation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["engine_decision"]["installation_or_download_authorized"] = True
        with self.assertRaisesRegex(EngineCliRecoveryDecisionError, "runtime mutation admitted"):
            validate(self.write_record(mutated))

    def test_canonical_cli_invocation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cli_decision"]["invoke_canonical_copy_after_staging"] = True
        with self.assertRaisesRegex(EngineCliRecoveryDecisionError, "unsafe CLI behavior admitted"):
            validate(self.write_record(mutated))

    def test_unverified_temporary_cli_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cli_decision"]["copy_must_match_sha256_before_each_invocation"] = False
        with self.assertRaisesRegex(EngineCliRecoveryDecisionError, "CLI identity or cleanup weakened"):
            validate(self.write_record(mutated))

    def test_attempt_count_widening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_contract"]["maximum_attempts"] = 2
        with self.assertRaisesRegex(EngineCliRecoveryDecisionError, "execution contract drift"):
            validate(self.write_record(mutated))

    def test_inference_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_contract"]["inference_request_count"] = 1
        with self.assertRaisesRegex(EngineCliRecoveryDecisionError, "execution contract drift"):
            validate(self.write_record(mutated))

    def test_premature_canary_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["synthetic_canary_authorized"] = True
        with self.assertRaisesRegex(EngineCliRecoveryDecisionError, "premature authorization"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
