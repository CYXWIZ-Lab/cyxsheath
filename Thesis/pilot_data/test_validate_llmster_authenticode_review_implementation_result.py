from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_authenticode_review_implementation_result import (
    LlmsterAuthenticodeReviewImplementationError,
    validate,
)


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_llmster_authenticode_review_implementation_result.json"


class LlmsterAuthenticodeReviewImplementationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def rejected(self, record: dict, message: str) -> None:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False)
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with self.assertRaisesRegex(LlmsterAuthenticodeReviewImplementationError, message):
            validate(Path(handle.name))

    def test_fixture_policy_is_complete_while_real_review_is_blocked(self) -> None:
        gate = self.record["decision_gate"]
        self.assertTrue(gate["platform_independent_review_policy_complete"])
        self.assertFalse(gate["retained_child_enumeration_or_content_read_authorized"])
        self.assertFalse(gate["authenticode_tool_discovery_or_invocation_authorized"])

    def test_design_digest_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["reviewed_decision"]["sha256"] = "0" * 64
        self.rejected(item, "design digest drift")

    def test_policy_source_digest_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["source_identity"][1]["sha256"] = "0" * 64
        self.rejected(item, "source identity drift")

    def test_staging_ownership_source_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["source_identity"][0]["bytes"] -= 1
        self.rejected(item, "source identity drift")

    def test_platform_adapter_admission_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["module_boundary"]["windows_process_adapter_added"] = True
        self.rejected(item, "module expansion admitted")

    def test_normalization_collapse_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["normalization_contract"]["inspector_timeout"] = "tool_error"
        self.rejected(item, "normalization drift")

    def test_full_fixture_count_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["fixture_evidence"]["python_3_14"]["tests_passed"] = 524
        self.rejected(item, "full fixture drift")

    def test_retained_child_access_authorization_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["decision_gate"]["retained_child_enumeration_or_content_read_authorized"] = True
        self.rejected(item, "premature authorization")

    def test_signature_tool_authorization_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["decision_gate"]["authenticode_tool_discovery_or_invocation_authorized"] = True
        self.rejected(item, "premature authorization")

    def test_candidate_path_retention_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["candidate_paths"] = ["private.exe"]
        self.rejected(item, "forbidden keys")


if __name__ == "__main__":
    unittest.main()
