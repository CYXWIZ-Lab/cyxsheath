from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_rights_and_provider_exposure import RightsEvidenceError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_rights_and_provider_exposure.json"


class RightsEvidenceTests(unittest.TestCase):
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

    def test_two_multilingual_cases_gain_analysis_rights_only(self) -> None:
        allowed = [case for case in self.record["cases"] if case["rights"]["research_analysis"] == "allowed"]
        self.assertEqual({"phase6-cal-001", "phase6-cal-008"}, {case["candidate_id"] for case in allowed})
        self.assertTrue(all(case["disposition"] == "quarantined" for case in self.record["cases"]))

    def test_raw_task_content_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cases"][0]["problem_statement"] = "must not be retained"
        with self.assertRaisesRegex(RightsEvidenceError, "forbidden raw-content"):
            validate(self.write_record(mutated))

    def test_verified_license_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["sources"]["dataset_cards"]["verified"]["declared_license"] = "MIT"
        with self.assertRaisesRegex(RightsEvidenceError, "verified license overclaim"):
            validate(self.write_record(mutated))

    def test_downstream_right_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cases"][0]["rights"]["model_training"] = "allowed"
        with self.assertRaisesRegex(RightsEvidenceError, "downstream-right overclaim"):
            validate(self.write_record(mutated))

    def test_big_pickle_cannot_be_admitted_for_more_tasks(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["provider_assessment"]["further_benchmark_submission"] = "allowed"
        with self.assertRaisesRegex(RightsEvidenceError, "unsafe provider admission"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
