from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_archive_inventory_decision import (
    LlmsterArchiveInventoryDecisionError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_llmster_archive_inventory_decision.json"
)


class LlmsterArchiveInventoryDecisionTests(unittest.TestCase):
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
        with self.assertRaisesRegex(LlmsterArchiveInventoryDecisionError, message):
            validate(self.write_record(record))

    def test_exact_metadata_only_scope_is_authorized(self) -> None:
        self.assertTrue(self.record["execution_gate"]["metadata_inventory_authorized_once"])
        self.assertFalse(self.record["execution_gate"]["archive_extraction_authorized"])

    def test_acquisition_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["acquisition_result"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "acquisition digest drift")

    def test_module_identity_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["implementation"]["module"]["bytes"] += 1
        self.assert_rejected(mutated, "module identity drift")

    def test_archive_identity_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["archive_identity"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "archive sha256 drift")

    def test_second_invocation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["one_shot"]["maximum_function_invocations"] = 2
        self.assert_rejected(mutated, "invocation count drift")

    def test_retry_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["one_shot"]["automatic_retry_count_maximum"] = 1
        self.assert_rejected(mutated, "retry admitted")

    def test_member_content_read_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["metadata_contract"]["member_content_read_count_maximum"] = 1
        self.assert_rejected(mutated, "member reads admitted")

    def test_weakened_entry_ceiling_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["metadata_contract"]["maximum_entries"] += 1
        self.assert_rejected(mutated, "maximum_entries drift")

    def test_extraction_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["archive_extraction_authorized"] = True
        self.assert_rejected(mutated, "scope widened: archive_extraction_authorized")

    def test_signature_scope_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["deferred_review"]["authenticode_verification"] = "verified"
        self.assert_rejected(mutated, "signature scope concealed")


if __name__ == "__main__":
    unittest.main()
