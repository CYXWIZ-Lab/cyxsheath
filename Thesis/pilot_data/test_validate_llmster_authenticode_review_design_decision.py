from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_authenticode_review_design_decision import (
    LlmsterAuthenticodeReviewDesignError,
    validate,
)


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_llmster_authenticode_review_design_decision.json"


class LlmsterAuthenticodeReviewDesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def rejected(self, record: dict, message: str) -> None:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False)
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with self.assertRaisesRegex(LlmsterAuthenticodeReviewDesignError, message):
            validate(Path(handle.name))

    def test_only_fixture_policy_work_is_authorized(self) -> None:
        gate = self.record["execution_gate"]
        self.assertTrue(gate["policy_source_and_generated_fixture_edits_authorized"])
        self.assertFalse(gate["retained_child_enumeration_or_content_read_authorized"])
        self.assertFalse(gate["authenticode_tool_discovery_or_invocation_authorized"])

    def test_staging_result_digest_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["accepted_staging_result"]["sha256"] = "0" * 64
        self.rejected(item, "staging result digest drift")

    def test_manifest_binding_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["owned_tree_admission"]["expected_content_manifest_sha256"] = "0" * 64
        self.rejected(item, "owned manifest drift")

    def test_candidate_digest_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["candidate_contract"]["expected_paths_sha256"] = "0" * 64
        self.rejected(item, "candidate binding drift")

    def test_validity_overclaim_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["normalization_contract"]["valid_means_syntactically_valid_not_publisher_trusted"] = False
        self.rejected(item, "validity overclaim")

    def test_unknown_cannot_collapse_into_invalid(self) -> None:
        item = copy.deepcopy(self.record)
        item["normalization_contract"]["unrecognized_status"] = "invalid"
        self.rejected(item, "unknown outcome drift")

    def test_timeout_cannot_collapse_into_tool_error(self) -> None:
        item = copy.deepcopy(self.record)
        item["normalization_contract"]["inspector_timeout"] = "tool_error"
        self.rejected(item, "timeout outcome drift")

    def test_wildcard_path_semantics_are_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["future_windows_adapter_contract"]["planned_parameter"] = "FilePath"
        self.rejected(item, "path semantics drift")

    def test_zero_egress_guard_cannot_be_disabled(self) -> None:
        item = copy.deepcopy(self.record)
        item["future_windows_adapter_contract"]["zero_egress_must_be_established_outside_the_cmdlet_before_real_execution"] = False
        self.rejected(item, "adapter guard disabled")

    def test_process_adapter_cannot_be_implemented_at_this_gate(self) -> None:
        item = copy.deepcopy(self.record)
        item["execution_gate"]["platform_adapter_implementation_authorized"] = True
        self.rejected(item, "scope widened")

    def test_retained_child_modification_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["execution_gate"]["retained_child_modification_or_removal_authorized"] = True
        self.rejected(item, "scope widened")

    def test_dependency_admission_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["module_boundary"]["new_dependencies_allowed"] = True
        self.rejected(item, "dependency admitted")


if __name__ == "__main__":
    unittest.main()
