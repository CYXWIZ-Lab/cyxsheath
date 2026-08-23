from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_candidate_events import LedgerError, current_events, load_and_validate


LEDGER = Path(__file__).with_name("candidate_events.jsonl")


class CandidateLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events = load_and_validate(LEDGER)

    def write_events(self, events: list[dict]) -> Path:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        with handle:
            for event in events:
                handle.write(json.dumps(event) + "\n")
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return Path(handle.name)

    def test_calibration_inventory_is_balanced_and_unadmitted(self) -> None:
        current = current_events(self.events)
        self.assertEqual(20, len(current))
        self.assertEqual(
            {"C": 7, "C++": 6, "Python": 7},
            {
                language: sum(event["source"]["language"] == language for event in current)
                for language in ("C", "C++", "Python")
            },
        )
        self.assertEqual({"quarantined"}, {event["disposition"] for event in current})
        self.assertEqual(3, sum(event["replay"]["status"] == "passed" for event in current))

    def test_sequence_gap_fails(self) -> None:
        mutated = copy.deepcopy(self.events)
        mutated[1]["sequence"] = 3
        with self.assertRaisesRegex(LedgerError, "expected sequence"):
            load_and_validate(self.write_events(mutated))

    def test_admission_with_unknown_analysis_rights_fails(self) -> None:
        mutated = copy.deepcopy(self.events)
        event = mutated[0]
        event["disposition"] = "admitted"
        event["reason_codes"] = []
        event["license"]["file_scope_review"] = "passed"
        event["replay"]["status"] = "passed"
        event["replay"]["image_digest"] = "0" * 64
        event["reviews"] = {key: "passed" for key in event["reviews"]}
        with self.assertRaisesRegex(LedgerError, "research_analysis=allowed"):
            load_and_validate(self.write_events(mutated))

    def test_rejection_reason_on_quarantine_fails(self) -> None:
        mutated = copy.deepcopy(self.events)
        mutated[0]["reason_codes"] = ["license.denied"]
        with self.assertRaisesRegex(LedgerError, "reason does not match"):
            load_and_validate(self.write_events(mutated))

    def test_review_must_supersede_latest_event(self) -> None:
        mutated = copy.deepcopy(self.events)
        review = copy.deepcopy(mutated[-1])
        review["sequence"] = len(mutated) + 1
        review["event_id"] = "phase6-cal-review-invalid"
        review["action"] = "reviewed"
        review["supersedes_event_id"] = "wrong-event"
        mutated.append(review)
        with self.assertRaisesRegex(LedgerError, "non-latest supersession"):
            load_and_validate(self.write_events(mutated))


if __name__ == "__main__":
    unittest.main()
