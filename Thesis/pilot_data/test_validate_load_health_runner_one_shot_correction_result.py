from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_load_health_runner_one_shot_correction_result import (
    LoadHealthRunnerOneShotCorrectionError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_load_health_runner_one_shot_correction_result.json"
)


class LoadHealthRunnerOneShotCorrectionTests(unittest.TestCase):
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

    def test_correction_passes_while_runtime_remains_blocked(self) -> None:
        gate = self.record["execution_gate"]
        self.assertTrue(gate["one_shot_gate_correction_complete"])
        self.assertFalse(gate["load_health_execution_authorized"])

    def test_blocking_review_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["blocking_review"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(LoadHealthRunnerOneShotCorrectionError, "digest drift"):
            validate(self.write_record(mutated))

    def test_historical_runner_linkage_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["code_transition"][0]["previous"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(LoadHealthRunnerOneShotCorrectionError, "historical linkage drift"):
            validate(self.write_record(mutated))

    def test_corrected_runner_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["code_transition"][0]["corrected"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(LoadHealthRunnerOneShotCorrectionError, "corrected identity drift"):
            validate(self.write_record(mutated))

    def test_nonexclusive_claim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["corrected_one_shot_contract"]["claim_primitive"] = "ordinary_overwrite"
        with self.assertRaisesRegex(LoadHealthRunnerOneShotCorrectionError, "claim primitive weakened"):
            validate(self.write_record(mutated))

    def test_prior_result_preservation_weakening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["corrected_one_shot_contract"]["prior_result_bytes_preserved"] = False
        with self.assertRaisesRegex(LoadHealthRunnerOneShotCorrectionError, "one-shot gate weakened"):
            validate(self.write_record(mutated))

    def test_automatic_retry_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["corrected_one_shot_contract"]["automatic_retry_count"] = 1
        with self.assertRaisesRegex(LoadHealthRunnerOneShotCorrectionError, "automatic retry admitted"):
            validate(self.write_record(mutated))

    def test_lm_studio_fixture_invocation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["fixture_evidence"]["lm_studio_invocation_count"] = 1
        with self.assertRaisesRegex(LoadHealthRunnerOneShotCorrectionError, "runtime fixture operation admitted"):
            validate(self.write_record(mutated))

    def test_execution_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["load_health_execution_authorized"] = True
        with self.assertRaisesRegex(LoadHealthRunnerOneShotCorrectionError, "premature authorization"):
            validate(self.write_record(mutated))

    def test_synthetic_canary_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["synthetic_canary_authorized"] = True
        with self.assertRaisesRegex(LoadHealthRunnerOneShotCorrectionError, "premature authorization"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
