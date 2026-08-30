from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_storage_policy_superseding_decision import (
    LlmsterStoragePolicyDecisionError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_llmster_storage_policy_superseding_decision.json"
)


class LlmsterStoragePolicySupersedingDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def write_record(self, record: dict) -> Path:
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False
        )
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return Path(handle.name)

    def assert_rejected(self, record: dict, message: str) -> None:
        with self.assertRaisesRegex(LlmsterStoragePolicyDecisionError, message):
            validate(self.write_record(record))

    def test_prior_authorization_is_superseded_by_one_current_request(self) -> None:
        one_shot = self.record["one_shot_contract"]
        self.assertEqual(0, one_shot["prior_module_maximum_invocations_after_supersession"])
        self.assertEqual(1, one_shot["current_module_maximum_invocations"])
        self.assertEqual(1, one_shot["maximum_combined_archive_requests"])

    def test_prior_decision_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["reviewed_prior_decision"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "digest drift")

    def test_revised_module_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["revised_policy_module_identity"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "identity drift")

    def test_archive_ceiling_increase_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["storage_policy_decision"]["maximum_archive_bytes"] += 1
        self.assert_rejected(mutated, "archive ceiling drift")

    def test_final_reserve_weakening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["storage_policy_decision"]["minimum_free_bytes_after"] -= 1
        self.assert_rejected(mutated, "revised reserve drift")

    def test_storage_margin_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["fresh_storage_baseline"]["margin_bytes"] = 0
        self.assert_rejected(mutated, "storage margin arithmetic drift")

    def test_prior_authorization_retention_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["one_shot_contract"]["prior_module_maximum_invocations_after_supersession"] = 1
        self.assert_rejected(mutated, "prior authorization retained")

    def test_retry_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["one_shot_contract"]["automatic_retry_count"] = 1
        self.assert_rejected(mutated, "automatic retry admitted")

    def test_extraction_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["archive_extraction_authorized"] = True
        self.assert_rejected(mutated, "scope widened")

    def test_benchmark_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["benchmark_input_authorized"] = True
        self.assert_rejected(mutated, "scope widened")


if __name__ == "__main__":
    unittest.main()
