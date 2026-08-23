from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_source_snapshots import SourceSnapshotError, validate


EVIDENCE = Path(__file__).parent / "proposal_evidence" / "phase6_source_snapshots.json"


class SourceSnapshotTests(unittest.TestCase):
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

    def test_three_snapshots_pass_with_proposals_pending(self) -> None:
        self.assertEqual(3, len(self.record["cases"]))
        self.assertTrue(all(case["snapshot_gate"] == "passed" for case in self.record["cases"]))

    def test_non_commit_base_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cases"][0]["base_object_type"] = "tree"
        with self.assertRaisesRegex(SourceSnapshotError, "base is not a commit"):
            validate(self.write_record(mutated))

    def test_replay_image_mismatch_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cases"][1]["image_linux_amd64_digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(SourceSnapshotError, "image digest mismatch"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
