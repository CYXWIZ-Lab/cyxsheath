from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_windows_authenticode_adapter_design_decision import (
    LlmsterWindowsAuthenticodeAdapterDesignError,
    validate,
)


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_llmster_windows_authenticode_adapter_design_decision.json"


class LlmsterWindowsAuthenticodeAdapterDesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def rejected(self, record: dict, message: str) -> None:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False)
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with self.assertRaisesRegex(LlmsterWindowsAuthenticodeAdapterDesignError, message):
            validate(Path(handle.name))

    def test_only_fixture_adapter_work_is_authorized(self) -> None:
        gate = self.record["execution_gate"]
        self.assertTrue(gate["fake_transport_calls_authorized"])
        self.assertFalse(gate["real_powershell_discovery_identity_read_or_invocation_authorized"])
        self.assertFalse(gate["retained_child_enumeration_or_content_read_authorized"])

    def test_policy_digest_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["accepted_policy_result"]["sha256"] = "0" * 64
        self.rejected(item, "policy digest drift")

    def test_transport_source_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["module_boundary"]["existing_cli_transport_sha256"] = "0" * 64
        self.rejected(item, "transport source drift")

    def test_shell_admission_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["powershell_contract"]["shell"] = True
        self.rejected(item, "unsafe PowerShell behavior admitted")

    def test_execution_policy_override_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["powershell_contract"]["execution_policy_override_added"] = True
        self.rejected(item, "unsafe PowerShell behavior admitted")

    def test_candidate_source_interpolation_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["powershell_contract"]["candidate_path_interpolated_into_powershell_source"] = True
        self.rejected(item, "unsafe PowerShell behavior admitted")

    def test_retry_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["candidate_contract"]["automatic_retry_count_maximum"] = 1
        self.rejected(item, "retry admitted")

    def test_timeout_widening_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["transport_contract"]["timeout_seconds"] = 11
        self.rejected(item, "timeout drift")

    def test_output_widening_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["transport_contract"]["combined_retained_output_bytes_maximum"] = 4097
        self.rejected(item, "output bound drift")

    def test_duplicate_json_key_acceptance_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["response_contract"]["duplicate_json_keys_rejected"] = False
        self.rejected(item, "response guard disabled")

    def test_zero_egress_guard_is_rejected_if_disabled(self) -> None:
        item = copy.deepcopy(self.record)
        item["network_boundary"]["external_zero_egress_containment_required_before_real_invocation"] = False
        self.rejected(item, "network guard disabled")

    def test_real_signature_invocation_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["execution_gate"]["authenticode_tool_invocation_authorized"] = True
        self.rejected(item, "scope widened")


if __name__ == "__main__":
    unittest.main()
