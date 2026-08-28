from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_download_execution_review import (
    LlmsterDownloadExecutionReviewError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_llmster_download_execution_review.json"
)


class LlmsterDownloadExecutionReviewTests(unittest.TestCase):
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
        with self.assertRaisesRegex(LlmsterDownloadExecutionReviewError, message):
            validate(self.write_record(record))

    def test_storage_failure_blocks_archive_download(self) -> None:
        gate = self.record["decision_gate"]
        self.assertFalse(gate["storage_gate_passed"])
        self.assertFalse(gate["archive_download_authorized"])

    def test_implementation_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["reviewed_implementation"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "implementation digest drift")

    def test_module_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["module_identity"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "module identity drift")

    def test_observed_storage_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["storage_observation"]["observed_free_bytes"] = 35433480192
        self.assert_rejected(mutated, "observed storage drift")

    def test_storage_deficit_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["storage_observation"]["deficit_bytes"] = 0
        self.assert_rejected(mutated, "storage deficit arithmetic drift")

    def test_storage_gate_pass_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["storage_gate_passed"] = True
        self.assert_rejected(mutated, "premature authorization")

    def test_destination_presence_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["storage_observation"]["destination_present"] = True
        self.assert_rejected(mutated, "unclean or passing storage baseline")

    def test_network_activity_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["security_and_research_boundary"]["archive_request_count"] = 1
        self.assert_rejected(mutated, "operation admitted")

    def test_archive_download_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["archive_download_authorized"] = True
        self.assert_rejected(mutated, "premature authorization")

    def test_archive_extraction_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["archive_extraction_authorized"] = True
        self.assert_rejected(mutated, "premature authorization")


if __name__ == "__main__":
    unittest.main()
