from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_non_replay_review import ReviewEvidenceError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_non_replay_review.json"


class NonReplayReviewTests(unittest.TestCase):
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

    def test_three_cases_are_reviewed_but_quarantined(self) -> None:
        self.assertEqual(3, len(self.record["cases"]))
        self.assertTrue(all(case["manual_review"]["disposition"] == "quarantined" for case in self.record["cases"]))

    def test_raw_task_field_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cases"][0]["problem_statement"] = "must not be retained"
        with self.assertRaisesRegex(ReviewEvidenceError, "forbidden raw-content"):
            validate(self.write_record(mutated))

    def test_secret_signal_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cases"][0]["automated_scan"]["signal_counts"]["private_key"] = 1
        with self.assertRaisesRegex(ReviewEvidenceError, "secret signal"):
            validate(self.write_record(mutated))

    def test_research_right_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cases"][2]["review_boundaries"]["research_analysis"] = "allowed"
        with self.assertRaisesRegex(ReviewEvidenceError, "rights overclaim"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
