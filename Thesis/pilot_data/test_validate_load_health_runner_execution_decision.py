from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_load_health_runner_execution_decision import (
    LoadHealthRunnerExecutionDecisionError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_load_health_runner_execution_decision.json"
)


class LoadHealthRunnerExecutionDecisionTests(unittest.TestCase):
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

    def test_decision_authorizes_only_one_load_health_execution(self) -> None:
        gate = self.record["decision_gate"]
        self.assertTrue(gate["load_health_execution_authorized"])
        self.assertFalse(gate["automatic_retry_authorized"])
        self.assertFalse(gate["synthetic_canary_authorized"])

    def test_prior_decision_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["prior_blocking_decision"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(LoadHealthRunnerExecutionDecisionError, "prior decision digest drift"):
            validate(self.write_record(mutated))

    def test_runner_source_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["runner_sha256"] = "0" * 64
        with self.assertRaisesRegex(LoadHealthRunnerExecutionDecisionError, "source digest drift"):
            validate(self.write_record(mutated))

    def test_canonical_order_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["canonicalization_correction"]["rule"] = "culture_aware"
        with self.assertRaisesRegex(LoadHealthRunnerExecutionDecisionError, "canonical rule drift"):
            validate(self.write_record(mutated))

    def test_corrected_engine_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["canonicalization_correction"]["corrected_inventory"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(LoadHealthRunnerExecutionDecisionError, "corrected engine identity drift"):
            validate(self.write_record(mutated))

    def test_unclean_host_baseline_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["clean_baseline"]["matching_runtime_process_count"] = 1
        with self.assertRaisesRegex(LoadHealthRunnerExecutionDecisionError, "runtime process present"):
            validate(self.write_record(mutated))

    def test_execution_settings_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["settings"]["gpu_offload"] = "max"
        with self.assertRaisesRegex(LoadHealthRunnerExecutionDecisionError, "execution settings drift"):
            validate(self.write_record(mutated))

    def test_attempt_count_widening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["maximum_attempts"] = 2
        with self.assertRaisesRegex(LoadHealthRunnerExecutionDecisionError, "attempt count widened"):
            validate(self.write_record(mutated))

    def test_synthetic_canary_permission_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["synthetic_canary_authorized"] = True
        with self.assertRaisesRegex(LoadHealthRunnerExecutionDecisionError, "scope widened"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
