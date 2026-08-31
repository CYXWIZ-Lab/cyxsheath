from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_extraction_staging_implementation_result import (
    LlmsterExtractionStagingImplementationError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_llmster_extraction_staging_implementation_result.json"
)


class LlmsterExtractionStagingImplementationResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def rejected(self, record: dict, message: str) -> None:
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False
        )
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with self.assertRaisesRegex(LlmsterExtractionStagingImplementationError, message):
            validate(Path(handle.name))

    def test_fixture_only_implementation_is_explicit(self) -> None:
        self.assertTrue(self.record["decision_gate"]["generated_fixture_gate_passed"])
        self.assertFalse(self.record["decision_gate"]["real_archive_extraction_authorized"])

    def test_design_digest_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["reviewed_decision"]["sha256"] = "0" * 64
        self.rejected(item, "design digest drift")

    def test_source_digest_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["source_identity"][2]["sha256"] = "0" * 64
        self.rejected(item, "source identity drift")

    def test_final_reserve_weakening_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["frozen_contract"]["minimum_free_bytes_after"] -= 1
        self.rejected(item, "final reserve weakened")

    def test_stream_chunk_growth_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["frozen_contract"]["stream_chunk_bytes_maximum"] += 1
        self.rejected(item, "stream chunk widened")

    def test_cleanup_weakening_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["verified_behaviors"]["failure_cleanup_requires_matching_parent_name_token_and_marker"] = False
        self.rejected(item, "verified behavior weakened")

    def test_overwrite_admission_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["verified_behaviors"]["existing_member_destination_never_overwritten"] = False
        self.rejected(item, "verified behavior weakened")

    def test_real_member_read_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["fixture_evidence"]["real_archive_member_content_read_count"] = 1
        self.rejected(item, "operation admitted")

    def test_real_extraction_authorization_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["decision_gate"]["real_archive_extraction_authorized"] = True
        self.rejected(item, "premature authorization")

    def test_dependency_growth_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["module_boundary"]["new_dependency_count"] = 1
        self.rejected(item, "dependency growth admitted")


if __name__ == "__main__":
    unittest.main()
