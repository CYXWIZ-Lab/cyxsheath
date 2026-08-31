from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_separator_canonicalization_result import (
    LlmsterSeparatorCanonicalizationResultError,
    validate,
)


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_llmster_separator_canonicalization_result.json"


class LlmsterSeparatorCanonicalizationResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def write_record(self, record: dict) -> Path:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False)
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return Path(handle.name)

    def assert_rejected(self, record: dict, message: str) -> None:
        with self.assertRaisesRegex(LlmsterSeparatorCanonicalizationResultError, message):
            validate(self.write_record(record))

    def test_fixture_result_is_accepted_without_real_inventory_permission(self) -> None:
        self.assertTrue(self.record["result_gate"]["fixture_implementation_accepted"])
        self.assertFalse(self.record["result_gate"]["fresh_real_inventory_authorized"])

    def test_decision_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "decision digest drift")

    def test_source_identity_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["corrected_sources"]["inventory_module"]["bytes"] += 1
        self.assert_rejected(mutated, "corrected source identity drift")

    def test_digest_equivalence_concealment_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["implemented_contract"]["forward_and_backslash_spellings_produce_same_canonical_inventory_digest"] = False
        self.assert_rejected(mutated, "contract outcome concealed")

    def test_raw_name_retention_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["implemented_contract"]["raw_member_names_retained_in_result"] = True
        self.assert_rejected(mutated, "raw names retained")

    def test_dependency_expansion_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["implemented_contract"]["new_dependencies"] = 1
        self.assert_rejected(mutated, "implementation scope widened: new_dependencies")

    def test_real_archive_read_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["real_archive_operations"]["central_directory_reads"] = 1
        self.assert_rejected(mutated, "real archive operation admitted")

    def test_fresh_inventory_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["result_gate"]["fresh_real_inventory_authorized"] = True
        self.assert_rejected(mutated, "scope widened: fresh_real_inventory_authorized")

    def test_extraction_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["result_gate"]["archive_extraction_authorized"] = True
        self.assert_rejected(mutated, "scope widened: archive_extraction_authorized")

    def test_suite_count_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["validation"]["pre_result_complete_suite_python_3_12"] = "397_passed"
        self.assert_rejected(mutated, "Python 3.12 suite drift")


if __name__ == "__main__":
    unittest.main()
