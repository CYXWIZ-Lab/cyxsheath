from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_load_health_transport_integration_decision import (
    LoadHealthTransportIntegrationDecisionError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_load_health_transport_integration_decision.json"
)


class LoadHealthTransportIntegrationDecisionTests(unittest.TestCase):
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

    def test_only_implementation_and_fixtures_are_authorized(self) -> None:
        gate = self.record["execution_gate"]
        self.assertTrue(gate["activation_runner_implementation_authorized"])
        self.assertFalse(gate["lm_studio_runtime_execution_authorized"])

    def test_dependency_growth_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["structural_decision"]["new_dependency_count"] = 1
        with self.assertRaisesRegex(LoadHealthTransportIntegrationDecisionError, "dependency growth admitted"):
            validate(self.write_record(mutated))

    def test_threaded_monitoring_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["structural_decision"]["thread_count"] = 1
        with self.assertRaisesRegex(LoadHealthTransportIntegrationDecisionError, "concurrency surface widened"):
            validate(self.write_record(mutated))

    def test_synchronous_load_mapping_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["monitored_load_contract"]["implementation"] = "python_standard_library_subprocess_run"
        with self.assertRaisesRegex(LoadHealthTransportIntegrationDecisionError, "load transport drift"):
            validate(self.write_record(mutated))

    def test_load_command_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["command_mapping"]["monitored_transport"] += " --gpu max"
        with self.assertRaisesRegex(LoadHealthTransportIntegrationDecisionError, "load command drift"):
            validate(self.write_record(mutated))

    def test_output_bound_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["monitored_load_contract"]["output_limit_kind"] = "strict_zero_overshoot_disk_limit"
        with self.assertRaisesRegex(LoadHealthTransportIntegrationDecisionError, "output-bound overclaim"):
            validate(self.write_record(mutated))

    def test_service_root_count_widening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["service_ownership_contract"]["readiness_requires_exact_service_root_count"] = 2
        with self.assertRaisesRegex(LoadHealthTransportIntegrationDecisionError, "service-root count widened"):
            validate(self.write_record(mutated))

    def test_automatic_retry_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["command_mapping"]["automatic_retry_count"] = 1
        with self.assertRaisesRegex(LoadHealthTransportIntegrationDecisionError, "automatic retry admitted"):
            validate(self.write_record(mutated))

    def test_cleanup_weakening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cleanup_contract"]["force_only_captured_owned_tree_if_graceful_cleanup_fails"] = False
        with self.assertRaisesRegex(LoadHealthTransportIntegrationDecisionError, "cleanup gate weakened"):
            validate(self.write_record(mutated))

    def test_runtime_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["lm_studio_runtime_execution_authorized"] = True
        with self.assertRaisesRegex(LoadHealthTransportIntegrationDecisionError, "premature authorization"):
            validate(self.write_record(mutated))

    def test_model_identity_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["identity_contract"]["weight_bytes"] += 1
        with self.assertRaisesRegex(LoadHealthTransportIntegrationDecisionError, "weight size drift"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
