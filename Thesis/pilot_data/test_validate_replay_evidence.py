from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_replay_evidence import ReplayEvidenceError, validate


EVIDENCE = Path(__file__).parent / "replay_evidence" / "phase6_vertical_slice.json"


class ReplayEvidenceTests(unittest.TestCase):
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

    def test_three_language_replay_is_valid_but_unadmitted(self) -> None:
        self.assertEqual(3, len(self.record["cases"]))
        self.assertEqual(0, self.record["admission"]["admitted_count"])

    def test_unresolved_gold_fails(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cases"][0]["gold"]["resolved"] = False
        with self.assertRaisesRegex(ReplayEvidenceError, "gold did not resolve"):
            validate(self.write_record(mutated))

    def test_control_count_mismatch_fails(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cases"][1]["gold"]["pass_to_pass_succeeded"] = 41
        with self.assertRaisesRegex(ReplayEvidenceError, "pass-to-pass count mismatch"):
            validate(self.write_record(mutated))

    def test_report_digest_mismatch_fails(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cases"][2]["gold"]["report_sha256"] = "0" * 64
        with self.assertRaisesRegex(ReplayEvidenceError, "report digest mismatch"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
