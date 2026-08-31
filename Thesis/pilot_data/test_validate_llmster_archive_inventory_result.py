from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_archive_inventory_result import (
    LlmsterArchiveInventoryResultError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_llmster_archive_inventory_result.json"
)


class LlmsterArchiveInventoryResultTests(unittest.TestCase):
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
        with self.assertRaisesRegex(LlmsterArchiveInventoryResultError, message):
            validate(self.write_record(record))

    def test_exact_rejection_is_preserved_without_follow_on_permission(self) -> None:
        self.assertFalse(self.record["inventory_observation"]["accepted"])
        self.assertEqual("member_backslash_rejected", self.record["inventory_observation"]["error_code"])
        self.assertFalse(self.record["result_gate"]["archive_extraction_authorized"])

    def test_authorization_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["authorization"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "authorization digest drift")

    def test_unconsumed_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["authorization"]["consumed"] = False
        self.assert_rejected(mutated, "authorization state concealed")

    def test_second_invocation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["authorization"]["function_invocation_count"] = 2
        self.assert_rejected(mutated, "invocation count drift")

    def test_retry_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["authorization"]["automatic_retry_count"] = 1
        self.assert_rejected(mutated, "retry admitted")

    def test_rejection_concealment_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["inventory_observation"]["accepted"] = True
        self.assert_rejected(mutated, "rejection concealed")

    def test_error_code_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["inventory_observation"]["error_code"] = "accepted"
        self.assert_rejected(mutated, "error code drift")

    def test_member_content_read_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["operation_counts"]["member_content_reads"] = 1
        self.assert_rejected(mutated, "operation count widened: member_content_reads")

    def test_safe_to_extract_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["security_and_research_conclusion"]["archive_safe_to_extract_claimed"] = True
        self.assert_rejected(mutated, "conclusion overclaimed: archive_safe_to_extract_claimed")

    def test_extraction_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["result_gate"]["archive_extraction_authorized"] = True
        self.assert_rejected(mutated, "scope widened: archive_extraction_authorized")


if __name__ == "__main__":
    unittest.main()
