from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_download_execution_decision import (
    LlmsterDownloadExecutionDecisionError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_llmster_download_execution_decision.json"
)


class LlmsterDownloadExecutionDecisionTests(unittest.TestCase):
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

    def assert_rejected(self, record: dict, message: str) -> None:
        with self.assertRaisesRegex(LlmsterDownloadExecutionDecisionError, message):
            validate(self.write_record(record))

    def test_only_one_archive_request_is_authorized(self) -> None:
        gate = self.record["decision_gate"]
        self.assertTrue(gate["archive_download_authorized"])
        self.assertEqual(1, gate["maximum_authorized_archive_requests"])
        self.assertFalse(gate["archive_extraction_authorized"])

    def test_blocking_decision_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["reviewed_blocking_decision"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "digest drift")

    def test_implementation_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["reviewed_implementation"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "digest drift")

    def test_module_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["module_identity"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "module identity drift")

    def test_storage_floor_weakening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["fresh_storage_baseline"]["minimum_free_bytes_after"] = 0
        self.assert_rejected(mutated, "storage reserve drift")

    def test_storage_margin_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["fresh_storage_baseline"]["margin_bytes"] = 0
        self.assert_rejected(mutated, "storage margin arithmetic drift")

    def test_destination_contamination_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["fresh_storage_baseline"]["destination_present"] = True
        self.assert_rejected(mutated, "unclean destination baseline")

    def test_second_attempt_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["frozen_request"]["maximum_attempts"] = 2
        self.assert_rejected(mutated, "request contract drift")

    def test_archive_extraction_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["archive_extraction_authorized"] = True
        self.assert_rejected(mutated, "scope widened")

    def test_benchmark_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["benchmark_input_authorized"] = True
        self.assert_rejected(mutated, "scope widened")


if __name__ == "__main__":
    unittest.main()
