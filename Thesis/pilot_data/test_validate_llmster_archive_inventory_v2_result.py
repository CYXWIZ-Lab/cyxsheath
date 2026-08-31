from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from validate_llmster_archive_inventory_v2_result import LlmsterArchiveInventoryV2ResultError, validate

EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_llmster_archive_inventory_v2_result.json"


class LlmsterArchiveInventoryV2ResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def rejected(self, record: dict, message: str) -> None:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False)
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with self.assertRaisesRegex(LlmsterArchiveInventoryV2ResultError, message):
            validate(Path(handle.name))

    def test_accepted_without_extraction_permission(self) -> None:
        self.assertTrue(self.record["result_gate"]["inventory_v2_accepted"])
        self.assertFalse(self.record["result_gate"]["archive_extraction_authorized"])

    def test_digest_drift_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["authorization"]["sha256"] = "0" * 64
        self.rejected(item, "authorization digest drift")

    def test_second_invocation_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["authorization"]["fresh_function_invocation_count"] = 2
        self.rejected(item, "invocation drift")

    def test_retry_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["authorization"]["automatic_retry_count"] = 1
        self.rejected(item, "retry admitted")

    def test_entry_drift_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["aggregate_inventory"]["entry_count"] += 1
        self.rejected(item, "entry count drift")

    def test_inventory_digest_drift_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["aggregate_inventory"]["canonical_inventory_sha256"] = "0" * 64
        self.rejected(item, "inventory digest drift")

    def test_member_read_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["operation_counts"]["member_content_reads"] = 1
        self.rejected(item, "operation admitted")

    def test_signature_overclaim_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["interpretation"]["authenticode_verified_claimed"] = True
        self.rejected(item, "overclaim")

    def test_extraction_authorization_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["result_gate"]["archive_extraction_authorized"] = True
        self.rejected(item, "scope widened")

    def test_staging_gate_concealment_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["result_gate"]["separate_owned_extraction_staging_decision_required"] = False
        self.rejected(item, "staging decision not required")


if __name__ == "__main__":
    unittest.main()
