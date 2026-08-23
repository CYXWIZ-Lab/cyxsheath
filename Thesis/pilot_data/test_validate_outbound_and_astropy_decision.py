from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_outbound_and_astropy_decision import OutboundDecisionError, validate


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_outbound_and_astropy_decision.json"
)


class OutboundAndAstropyDecisionTests(unittest.TestCase):
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

    def test_astropy_is_retained_for_analysis_but_not_training(self) -> None:
        astropy = next(
            case
            for case in self.record["case_decisions"]
            if case["candidate_id"] == "phase6-cal-014"
        )
        self.assertEqual("retained", astropy["case_selection"])
        self.assertEqual("allowed", astropy["research_analysis"])
        self.assertEqual("unknown", astropy["model_training"])
        self.assertEqual("NOASSERTION", astropy["exact_card_license"])

    def test_free_mimo_cannot_receive_benchmark_input(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["case_decisions"][0]["free_mimo_outbound"] = "allowed"
        with self.assertRaisesRegex(OutboundDecisionError, "unsafe free route"):
            validate(self.write_record(mutated))

    def test_unknown_training_right_cannot_be_overclaimed(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["case_decisions"][1]["model_training"] = "allowed"
        with self.assertRaisesRegex(OutboundDecisionError, "training-right overclaim"):
            validate(self.write_record(mutated))

    def test_local_path_cannot_claim_readiness(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["design_decision"]["implementation_status"] = "benchmark_ready"
        with self.assertRaisesRegex(OutboundDecisionError, "premature local readiness"):
            validate(self.write_record(mutated))

    def test_raw_benchmark_content_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["case_decisions"][0]["problem_statement"] = "must not be retained"
        with self.assertRaisesRegex(OutboundDecisionError, "forbidden raw-content"):
            validate(self.write_record(mutated))

    def test_astropy_exact_card_license_cannot_be_rewritten(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["sources"]["exact_dataset_cards"]["verified_declared_license"] = "MIT"
        with self.assertRaisesRegex(OutboundDecisionError, "exact-card license overclaim"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
