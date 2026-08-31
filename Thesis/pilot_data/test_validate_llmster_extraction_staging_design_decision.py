from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from validate_llmster_extraction_staging_design_decision import LlmsterExtractionStagingDesignError, validate

EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_llmster_extraction_staging_design_decision.json"


class LlmsterExtractionStagingDesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def rejected(self, record: dict, message: str) -> None:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False)
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with self.assertRaisesRegex(LlmsterExtractionStagingDesignError, message):
            validate(Path(handle.name))

    def test_fixture_implementation_only(self) -> None:
        self.assertTrue(self.record["execution_gate"]["generated_fixture_extraction_authorized"])
        self.assertFalse(self.record["execution_gate"]["real_archive_extraction_authorized"])

    def test_inventory_digest_drift_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["accepted_inventory"]["sha256"] = "0" * 64
        self.rejected(item, "inventory digest drift")

    def test_dependency_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["module_boundary"]["new_dependencies_allowed"] = True
        self.rejected(item, "dependency admitted")

    def test_parent_guard_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["ownership_contract"]["parent_must_exist_be_absolute_and_not_be_symlink"] = False
        self.rejected(item, "ownership guard disabled")

    def test_rollback_scope_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["ownership_contract"]["rollback_may_remove_only_the_owned_child"] = False
        self.rejected(item, "ownership guard disabled")

    def test_reserve_weakening_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["storage_and_write_contract"]["minimum_free_bytes_after"] -= 1
        self.rejected(item, "final reserve drift")

    def test_overwrite_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["storage_and_write_contract"]["existing_destination_overwrite_count_maximum"] = 1
        self.rejected(item, "overwrite admitted")

    def test_cleanup_concealment_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["success_and_failure_contract"]["cleanup_failure_must_be_reported_and_cannot_be_concealed"] = False
        self.rejected(item, "cleanup failure concealed")

    def test_signature_execution_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["signature_review_boundary"]["signature_tool_may_not_execute_target_binaries"] = False
        self.rejected(item, "signature guard disabled")

    def test_real_extraction_rejected(self) -> None:
        item = copy.deepcopy(self.record); item["execution_gate"]["real_archive_extraction_authorized"] = True
        self.rejected(item, "scope widened")


if __name__ == "__main__":
    unittest.main()
