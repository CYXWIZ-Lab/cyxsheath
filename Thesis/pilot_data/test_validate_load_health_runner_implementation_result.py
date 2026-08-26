from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_load_health_runner_implementation_result import (
    LoadHealthRunnerImplementationResultError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_load_health_runner_implementation_result.json"
)


class LoadHealthRunnerImplementationResultTests(unittest.TestCase):
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

    def test_implementation_passes_while_runtime_stays_blocked(self) -> None:
        self.assertTrue(self.record["execution_gate"]["runner_implementation_complete"])
        self.assertFalse(self.record["execution_gate"]["load_health_execution_authorized"])

    def test_module_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["implementation_identity"]["modules"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(LoadHealthRunnerImplementationResultError, "file digest drift"):
            validate(self.write_record(mutated))

    def test_dependency_growth_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["implementation_identity"]["new_dependency_count"] = 1
        with self.assertRaisesRegex(LoadHealthRunnerImplementationResultError, "dependency growth admitted"):
            validate(self.write_record(mutated))

    def test_threaded_monitoring_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["implementation_identity"]["thread_count"] = 1
        with self.assertRaisesRegex(LoadHealthRunnerImplementationResultError, "concurrency surface widened"):
            validate(self.write_record(mutated))

    def test_fixture_count_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["fixture_evidence"]["python_3_12"]["tests_passed"] = 15
        with self.assertRaisesRegex(LoadHealthRunnerImplementationResultError, "fixture evidence drift"):
            validate(self.write_record(mutated))

    def test_lm_studio_fixture_invocation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["fixture_evidence"]["lm_studio_invocation_count"] = 1
        with self.assertRaisesRegex(LoadHealthRunnerImplementationResultError, "runtime operation admitted"):
            validate(self.write_record(mutated))

    def test_unrecorded_execution_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["runtime_gate"]["execution_authorization_present_at_checkpoint"] = True
        with self.assertRaisesRegex(LoadHealthRunnerImplementationResultError, "unrecorded authorization admitted"):
            validate(self.write_record(mutated))

    def test_runtime_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["load_health_execution_authorized"] = True
        with self.assertRaisesRegex(LoadHealthRunnerImplementationResultError, "premature authorization"):
            validate(self.write_record(mutated))

    def test_inference_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["security_and_research_boundary"]["inference_request_count"] = 1
        with self.assertRaisesRegex(LoadHealthRunnerImplementationResultError, "runtime operation admitted"):
            validate(self.write_record(mutated))

    def test_live_adapter_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["known_limits"]["windows_host_adapter_exercised_live_at_checkpoint"] = True
        with self.assertRaisesRegex(LoadHealthRunnerImplementationResultError, "implementation overclaim"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
