from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_load_health_runner_execution_result import (
    LoadHealthRunnerExecutionResultError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_load_health_runner_execution_result.json"
)


class LoadHealthRunnerExecutionResultTests(unittest.TestCase):
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

    def test_result_preserves_partial_success_and_overall_failure(self) -> None:
        acceptance = self.record["acceptance"]
        self.assertTrue(acceptance["model_load_observed"])
        self.assertTrue(acceptance["resource_gate_passed"])
        self.assertFalse(acceptance["graceful_shutdown_gate_passed"])
        self.assertFalse(acceptance["load_health_gate_passed"])

    def test_execution_decision_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_decision"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(LoadHealthRunnerExecutionResultError, "decision digest drift"):
            validate(self.write_record(mutated))

    def test_retained_result_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["retained_local_artifacts"]["runtime_result_sha256"] = "0" * 64
        with self.assertRaisesRegex(LoadHealthRunnerExecutionResultError, "result artifact drift"):
            validate(self.write_record(mutated))

    def test_successful_load_concealment_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["attempt"]["load_exit_code"] = 1
        with self.assertRaisesRegex(LoadHealthRunnerExecutionResultError, "load result drift"):
            validate(self.write_record(mutated))

    def test_shutdown_failure_concealment_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["attempt"]["daemon_down_exit_code"] = 0
        with self.assertRaisesRegex(LoadHealthRunnerExecutionResultError, "daemon-down result drift"):
            validate(self.write_record(mutated))

    def test_resource_ceiling_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["observed_resources"]["allowed_available_memory_drop_bytes"] = 1
        with self.assertRaisesRegex(LoadHealthRunnerExecutionResultError, "memory-drop ceiling failed"):
            validate(self.write_record(mutated))

    def test_forced_cleanup_concealment_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["identity_and_cleanup"]["forced_cleanup_required"] = False
        with self.assertRaisesRegex(LoadHealthRunnerExecutionResultError, "cleanup fact drift"):
            validate(self.write_record(mutated))

    def test_overall_acceptance_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["acceptance"]["load_health_gate_passed"] = True
        with self.assertRaisesRegex(LoadHealthRunnerExecutionResultError, "acceptance overclaim"):
            validate(self.write_record(mutated))

    def test_retry_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["automatic_retry_authorized"] = True
        with self.assertRaisesRegex(LoadHealthRunnerExecutionResultError, "premature authorization"):
            validate(self.write_record(mutated))

    def test_inference_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["security_and_research_boundary"]["inference_request_count"] = 1
        with self.assertRaisesRegex(LoadHealthRunnerExecutionResultError, "operation or retry admitted"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
