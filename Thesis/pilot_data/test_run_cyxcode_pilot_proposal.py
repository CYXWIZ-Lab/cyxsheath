from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_cyxcode_pilot_proposal import MODEL, MODEL_RECORD, PROVIDER_SUBMISSION_APPROVED, task_record


class CyxCodePilotProposalTests(unittest.TestCase):
    def test_pinned_free_model_is_text_and_tool_capable(self) -> None:
        self.assertEqual("opencode/big-pickle", MODEL)
        self.assertEqual(0, MODEL_RECORD["input_cost"])
        self.assertEqual(0, MODEL_RECORD["output_cost"])
        self.assertTrue(MODEL_RECORD["tool_call"])
        self.assertEqual("text", MODEL_RECORD["input_modality"])
        self.assertEqual("text", MODEL_RECORD["output_modality"])

    def test_data_collecting_stealth_provider_is_blocked(self) -> None:
        self.assertFalse(PROVIDER_SUBMISSION_APPROVED)

    def test_task_record_excludes_benchmark_oracles(self) -> None:
        event = {
            "benchmark": {"instance_id": "repo__name-1"},
            "source": {
                "repository": "repo/name",
                "base_revision": "a" * 40,
            },
        }
        row = {
            "problem_statement": "Fix the reported behavior.",
            "patch": "GOLD-SOLUTION",
            "test_patch": "BLINDED-TEST",
            "eval_script": "BLINDED-SCRIPT",
        }
        record = task_record(event, row, "sha256:" + "b" * 64)
        encoded = str(record)
        self.assertIn(row["problem_statement"], encoded)
        self.assertNotIn(row["patch"], encoded)
        self.assertNotIn(row["test_patch"], encoded)
        self.assertNotIn(row["eval_script"], encoded)


if __name__ == "__main__":
    unittest.main()
