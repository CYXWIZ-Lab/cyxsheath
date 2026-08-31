from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_archive_inventory_v2_decision import (
    LlmsterArchiveInventoryV2DecisionError,
    validate,
)


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_llmster_archive_inventory_v2_decision.json"


class LlmsterArchiveInventoryV2DecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def write_record(self, record: dict) -> Path:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False)
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return Path(handle.name)

    def assert_rejected(self, record: dict, message: str) -> None:
        with self.assertRaisesRegex(LlmsterArchiveInventoryV2DecisionError, message):
            validate(self.write_record(record))

    def test_one_fresh_inventory_is_authorized_without_extraction(self) -> None:
        self.assertTrue(self.record["execution_gate"]["metadata_inventory_v2_authorized_once"])
        self.assertFalse(self.record["execution_gate"]["archive_extraction_authorized"])

    def test_prior_reuse_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["prior_consumed_result"]["reusable"] = True
        self.assert_rejected(mutated, "prior authorization reused")

    def test_correction_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["canonicalization_result"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "correction digest drift")

    def test_source_identity_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["implementation"]["module"]["bytes"] += 1
        self.assert_rejected(mutated, "implementation identity drift")

    def test_separator_policy_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["metadata_contract"]["separator_policy"] = "accept_all"
        self.assert_rejected(mutated, "separator policy drift")

    def test_second_fresh_invocation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["one_shot"]["fresh_function_invocation_count_maximum"] = 2
        self.assert_rejected(mutated, "fresh invocation drift")

    def test_retry_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["one_shot"]["automatic_retry_count_maximum"] = 1
        self.assert_rejected(mutated, "retry admitted")

    def test_member_content_read_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["metadata_contract"]["member_content_read_count_maximum"] = 1
        self.assert_rejected(mutated, "member reads admitted")

    def test_extraction_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["archive_extraction_authorized"] = True
        self.assert_rejected(mutated, "scope widened: archive_extraction_authorized")

    def test_member_path_recording_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["required_result"]["individual_raw_or_canonical_member_paths_may_be_recorded"] = True
        self.assert_rejected(mutated, "member paths exposed")


if __name__ == "__main__":
    unittest.main()
