from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_load_health_runner_execution_review import (
    LoadHealthRunnerExecutionReviewError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_load_health_runner_execution_review.json"
)


class LoadHealthRunnerExecutionReviewTests(unittest.TestCase):
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

    def test_review_blocks_execution_and_authorizes_only_correction(self) -> None:
        gate = self.record["decision_gate"]
        self.assertFalse(gate["load_health_execution_authorized"])
        self.assertTrue(gate["narrow_one_shot_gate_correction_authorized"])

    def test_implementation_evidence_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["reviewed_evidence"]["implementation_result"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(LoadHealthRunnerExecutionReviewError, "digest drift"):
            validate(self.write_record(mutated))

    def test_runner_linkage_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["reviewed_evidence"]["runner"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(LoadHealthRunnerExecutionReviewError, "implementation linkage drift"):
            validate(self.write_record(mutated))

    def test_overwrite_path_concealment_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["blocking_finding"]["observed_control_flow"]["finally_writes_result_after_catch"] = False
        with self.assertRaisesRegex(LoadHealthRunnerExecutionReviewError, "overwrite path concealed"):
            validate(self.write_record(mutated))

    def test_preservation_fixture_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["blocking_finding"]["observed_control_flow"]["existing_result_preservation_fixture_present"] = True
        with self.assertRaisesRegex(LoadHealthRunnerExecutionReviewError, "fixture overclaim"):
            validate(self.write_record(mutated))

    def test_one_shot_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["blocking_finding"]["one_shot_contract_satisfied"] = True
        with self.assertRaisesRegex(LoadHealthRunnerExecutionReviewError, "one-shot overclaim"):
            validate(self.write_record(mutated))

    def test_retry_widening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["frozen_execution_contract"]["automatic_retry_count"] = 1
        with self.assertRaisesRegex(LoadHealthRunnerExecutionReviewError, "execution contract drift"):
            validate(self.write_record(mutated))

    def test_inference_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["security_and_research_boundary"]["inference_request_count"] = 1
        with self.assertRaisesRegex(LoadHealthRunnerExecutionReviewError, "operation admitted"):
            validate(self.write_record(mutated))

    def test_authorization_record_creation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["execution_authorization_record_creation_authorized"] = True
        with self.assertRaisesRegex(LoadHealthRunnerExecutionReviewError, "premature authorization"):
            validate(self.write_record(mutated))

    def test_synthetic_canary_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["synthetic_canary_authorized"] = True
        with self.assertRaisesRegex(LoadHealthRunnerExecutionReviewError, "premature authorization"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
