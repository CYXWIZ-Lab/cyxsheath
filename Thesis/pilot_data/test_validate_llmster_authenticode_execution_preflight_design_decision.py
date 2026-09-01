from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_authenticode_execution_preflight_design_decision import (
    LlmsterAuthenticodeExecutionPreflightDesignError,
    validate,
)


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_llmster_authenticode_execution_preflight_design_decision.json"


class LlmsterAuthenticodeExecutionPreflightDesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def rejected(self, record: dict, message: str) -> None:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False)
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with self.assertRaisesRegex(LlmsterAuthenticodeExecutionPreflightDesignError, message):
            validate(Path(handle.name))

    def test_fixture_only_preflight_is_authorized(self) -> None:
        gate = self.record["execution_gate"]
        self.assertTrue(gate["preflight_source_and_generated_fixture_edits_authorized"])
        self.assertFalse(gate["firewall_state_read_create_modify_or_remove_authorized"])
        self.assertFalse(gate["authenticode_tool_invocation_authorized"])

    def test_adapter_digest_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["accepted_inputs"]["adapter_implementation"]["sha256"] = "0" * 64
        self.rejected(item, "input digest drift")

    def test_candidate_count_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["batch_contract"]["candidate_count"] = 92
        self.rejected(item, "batch candidate drift")

    def test_firewall_direction_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["external_containment_contract"]["direction"] = "Inbound"
        self.rejected(item, "firewall direction drift")

    def test_firewall_scope_weakening_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["external_containment_contract"]["rule_program_path_must_equal_observed_powershell_path"] = False
        self.rejected(item, "containment guard weakened")

    def test_deadline_widening_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["batch_contract"]["overall_deadline_seconds"] = 301
        self.rejected(item, "batch deadline drift")

    def test_adapter_call_widening_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["batch_contract"]["maximum_adapter_calls"] = 92
        self.rejected(item, "adapter call bound widened")

    def test_one_shot_widening_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["one_shot_contract"]["maximum_runner_invocations"] = 2
        self.rejected(item, "runner count widened")

    def test_retry_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["one_shot_contract"]["automatic_retry_count_maximum"] = 1
        self.rejected(item, "one-shot retry admitted")

    def test_absolute_path_publication_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["output_contract"]["curated_preflight_record_excludes_absolute_paths_rule_names_raw_firewall_objects_and_events"] = False
        self.rejected(item, "output guard weakened")

    def test_real_firewall_access_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["execution_gate"]["firewall_state_read_create_modify_or_remove_authorized"] = True
        self.rejected(item, "scope widened")

    def test_signature_tool_authority_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["execution_gate"]["authenticode_tool_invocation_authorized"] = True
        self.rejected(item, "scope widened")


if __name__ == "__main__":
    unittest.main()
