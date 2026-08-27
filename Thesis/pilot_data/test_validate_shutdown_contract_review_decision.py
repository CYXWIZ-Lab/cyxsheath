from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_shutdown_contract_review_decision import (
    ShutdownContractReviewDecisionError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_shutdown_contract_review_decision.json"
)


class ShutdownContractReviewDecisionTests(unittest.TestCase):
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
        with self.assertRaisesRegex(ShutdownContractReviewDecisionError, message):
            validate(self.write_record(record))

    def test_fixture_only_decision_is_explicit(self) -> None:
        gate = self.record["decision_gate"]
        self.assertTrue(gate["shutdown_observation_implementation_and_fixtures_authorized"])
        self.assertFalse(gate["lm_studio_runtime_execution_authorized"])

    def test_prior_result_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["reviewed_evidence"]["load_health_result"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "digest drift")

    def test_exact_exit_message_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["finding"]["exact_daemon_down_message_observed"] = True
        self.assert_rejected(mutated, "exact-message overclaim")

    def test_timing_only_correction_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["finding"]["longer_root_wait_alone_is_an_authorized_correction"] = True
        self.assert_rejected(mutated, "unsafe timing correction")

    def test_desktop_mode_preload_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["approved_correction_contract"]["preload_gate"]["required_is_daemon"] = False
        self.assert_rejected(mutated, "daemon-mode gate weakened")

    def test_status_postcondition_removal_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["approved_correction_contract"]["acceptance"]["final_daemon_status_must_be_not_running"] = False
        self.assert_rejected(mutated, "acceptance weakened")

    def test_forced_cleanup_acceptance_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["approved_correction_contract"]["acceptance"]["forced_cleanup_allowed_as_success"] = True
        self.assert_rejected(mutated, "forced cleanup accepted")

    def test_runtime_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["lm_studio_runtime_execution_authorized"] = True
        self.assert_rejected(mutated, "premature authorization")

    def test_synthetic_canary_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["synthetic_canary_authorized"] = True
        self.assert_rejected(mutated, "premature authorization")


if __name__ == "__main__":
    unittest.main()
