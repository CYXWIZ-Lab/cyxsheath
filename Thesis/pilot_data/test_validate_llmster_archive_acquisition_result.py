from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_archive_acquisition_result import (
    LlmsterArchiveAcquisitionResultError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_llmster_archive_acquisition_result.json"
)


class LlmsterArchiveAcquisitionResultTests(unittest.TestCase):
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
        with self.assertRaisesRegex(LlmsterArchiveAcquisitionResultError, message):
            validate(self.write_record(record))

    def test_exact_acquisition_is_accepted_with_no_follow_on_permission(self) -> None:
        self.assertTrue(self.record["result_gate"]["archive_acquisition_accepted"])
        self.assertFalse(self.record["result_gate"]["another_archive_request_authorized"])
        self.assertFalse(self.record["result_gate"]["archive_inventory_authorized"])

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

    def test_archive_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["request_result"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "archive sha256 drift")

    def test_final_storage_reserve_weakening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["post_request_storage"]["minimum_free_bytes_after"] -= 1
        self.assert_rejected(mutated, "final reserve drift")

    def test_partial_presence_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["request_result"]["partial_absent_after"] = False
        self.assert_rejected(mutated, "request result concealed")

    def test_extraction_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["result_gate"]["archive_extraction_authorized"] = True
        self.assert_rejected(mutated, "scope widened")

    def test_benchmark_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["result_gate"]["benchmark_input_authorized"] = True
        self.assert_rejected(mutated, "scope widened")


if __name__ == "__main__":
    unittest.main()
