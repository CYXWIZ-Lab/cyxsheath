from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_windows_authenticode_adapter_implementation_result import (
    LlmsterWindowsAuthenticodeAdapterImplementationError,
    validate,
)


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_llmster_windows_authenticode_adapter_implementation_result.json"


class LlmsterWindowsAuthenticodeAdapterImplementationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def rejected(self, record: dict, message: str) -> None:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False)
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with self.assertRaisesRegex(LlmsterWindowsAuthenticodeAdapterImplementationError, message):
            validate(Path(handle.name))

    def test_fixture_adapter_complete_while_real_tool_is_blocked(self) -> None:
        gate = self.record["decision_gate"]
        self.assertTrue(gate["windows_adapter_implementation_complete"])
        self.assertFalse(gate["real_powershell_discovery_identity_read_or_invocation_authorized"])
        self.assertFalse(gate["authenticode_tool_invocation_authorized"])

    def test_design_digest_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["reviewed_decision"]["sha256"] = "0" * 64
        self.rejected(item, "design digest drift")

    def test_adapter_source_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["source_identity"][3]["sha256"] = "0" * 64
        self.rejected(item, "source identity drift")

    def test_transport_source_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["source_identity"][0]["bytes"] -= 1
        self.rejected(item, "source identity drift")

    def test_literal_path_behavior_cannot_be_removed(self) -> None:
        item = copy.deepcopy(self.record)
        item["verified_behaviors"]["script_calls_get_authenticode_signature_with_literal_path"] = False
        self.rejected(item, "verified behavior weakened")

    def test_real_transport_invocation_overclaim_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["fixture_evidence"]["real_powershell_invocation_count"] = 1
        self.rejected(item, "operation admitted")

    def test_full_fixture_count_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["fixture_evidence"]["python_3_14"]["tests_passed"] = 566
        self.rejected(item, "full fixture drift")

    def test_retained_child_access_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["decision_gate"]["retained_child_enumeration_or_content_read_authorized"] = True
        self.rejected(item, "premature authorization")

    def test_signature_tool_authority_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["decision_gate"]["authenticode_tool_invocation_authorized"] = True
        self.rejected(item, "premature authorization")

    def test_raw_output_retention_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["raw_stdout"] = "private"
        self.rejected(item, "forbidden keys")


if __name__ == "__main__":
    unittest.main()
