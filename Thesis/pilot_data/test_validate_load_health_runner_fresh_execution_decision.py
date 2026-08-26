from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_load_health_runner_fresh_execution_decision import (
    LoadHealthRunnerFreshExecutionDecisionError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_load_health_runner_fresh_execution_decision.json"
)


class LoadHealthRunnerFreshExecutionDecisionTests(unittest.TestCase):
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

    def test_decision_blocks_execution_and_authorizes_only_identity_correction(self) -> None:
        gate = self.record["decision_gate"]
        self.assertFalse(gate["load_health_execution_authorized"])
        self.assertTrue(gate["narrow_engine_identity_canonicalization_correction_authorized"])

    def test_correction_evidence_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["reviewed_evidence"]["one_shot_correction"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(LoadHealthRunnerFreshExecutionDecisionError, "digest drift"):
            validate(self.write_record(mutated))

    def test_runner_source_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["reviewed_evidence"]["runner"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(LoadHealthRunnerFreshExecutionDecisionError, "source digest drift"):
            validate(self.write_record(mutated))

    def test_inventory_mismatch_concealment_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["identity_checkpoint"]["runner_computed_inventory_sha256"] = mutated[
            "identity_checkpoint"
        ]["recorded_inventory_sha256"]
        with self.assertRaisesRegex(LoadHealthRunnerFreshExecutionDecisionError, "runner engine digest drift"):
            validate(self.write_record(mutated))

    def test_ordering_witness_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["identity_checkpoint"]["ordering_witness"]["runner_prefix_after_metadata"][0] = (
            "ggml_llamacpp.dll"
        )
        with self.assertRaisesRegex(LoadHealthRunnerFreshExecutionDecisionError, "ordering witness drift"):
            validate(self.write_record(mutated))

    def test_claim_ordering_concealment_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["blocking_finding"]["execution_claim_created_before_engine_identity_check"] = False
        with self.assertRaisesRegex(LoadHealthRunnerFreshExecutionDecisionError, "claim ordering concealed"):
            validate(self.write_record(mutated))

    def test_execution_contract_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["blocking_finding"]["execution_contract_satisfied"] = True
        with self.assertRaisesRegex(LoadHealthRunnerFreshExecutionDecisionError, "execution contract overclaim"):
            validate(self.write_record(mutated))

    def test_authorization_record_creation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["execution_authorization_record_creation_authorized"] = True
        with self.assertRaisesRegex(LoadHealthRunnerFreshExecutionDecisionError, "premature authorization"):
            validate(self.write_record(mutated))

    def test_runtime_invocation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["security_and_research_boundary"]["lm_studio_invocation_count_at_review"] = 1
        with self.assertRaisesRegex(LoadHealthRunnerFreshExecutionDecisionError, "operation admitted"):
            validate(self.write_record(mutated))

    def test_synthetic_canary_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["synthetic_canary_authorized"] = True
        with self.assertRaisesRegex(LoadHealthRunnerFreshExecutionDecisionError, "premature authorization"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
