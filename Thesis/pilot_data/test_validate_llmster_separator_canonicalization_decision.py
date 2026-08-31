from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_separator_canonicalization_decision import (
    LlmsterSeparatorCanonicalizationDecisionError,
    validate,
)


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_llmster_separator_canonicalization_decision.json"


class LlmsterSeparatorCanonicalizationDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def write_record(self, record: dict) -> Path:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False)
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return Path(handle.name)

    def assert_rejected(self, record: dict, message: str) -> None:
        with self.assertRaisesRegex(LlmsterSeparatorCanonicalizationDecisionError, message):
            validate(self.write_record(record))

    def test_fixture_only_scope_is_accepted(self) -> None:
        self.assertTrue(self.record["execution_gate"]["generated_fixture_execution_authorized"])
        self.assertFalse(self.record["execution_gate"]["fresh_real_inventory_authorized"])

    def test_prior_result_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["prior_result"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "prior result digest drift")

    def test_source_identity_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["current_sources"]["module"]["bytes"] += 1
        self.assert_rejected(mutated, "module identity drift")

    def test_dependency_expansion_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["boundary_decision"]["new_dependency_allowed"] = True
        self.assert_rejected(mutated, "dependency admitted")

    def test_separator_meaning_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["boundary_decision"]["backslash_meaning"] = "literal"
        self.assert_rejected(mutated, "separator meaning drift")

    def test_unicode_normalization_widening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["boundary_decision"]["unicode_policy"] = "silently_normalize"
        self.assert_rejected(mutated, "unicode policy drift")

    def test_raw_name_retention_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["boundary_decision"]["canonical_output_retains_raw_member_name"] = True
        self.assert_rejected(mutated, "raw name retention admitted")

    def test_fixture_requirement_weakening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["fixture_requirements"]["reject_backslash_parent_traversal"] = False
        self.assert_rejected(mutated, "fixture requirement disabled")

    def test_real_inventory_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["fresh_real_inventory_authorized"] = True
        self.assert_rejected(mutated, "scope widened: fresh_real_inventory_authorized")

    def test_extraction_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["archive_extraction_authorized"] = True
        self.assert_rejected(mutated, "scope widened: archive_extraction_authorized")


if __name__ == "__main__":
    unittest.main()
