from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_shutdown_observation_implementation_result import (
    ShutdownObservationImplementationError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_shutdown_observation_implementation_result.json"
)


class ShutdownObservationImplementationResultTests(unittest.TestCase):
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
        with self.assertRaisesRegex(ShutdownObservationImplementationError, message):
            validate(self.write_record(record))

    def test_fixture_only_implementation_is_explicit(self) -> None:
        gate = self.record["decision_gate"]
        self.assertTrue(gate["shutdown_observation_implementation_complete"])
        self.assertFalse(gate["lm_studio_runtime_execution_authorized"])

    def test_review_decision_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["reviewed_decision"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "decision digest drift")

    def test_lifecycle_source_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["source_transition"][1]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "source identity drift")

    def test_dependency_growth_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["module_boundary"]["new_dependency_count"] = 1
        self.assert_rejected(mutated, "dependency growth admitted")

    def test_desktop_mode_load_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["startup_contract"]["desktop_service_action"] = "continue_to_model_load"
        self.assert_rejected(mutated, "desktop mode widened")

    def test_status_postcondition_removal_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["shutdown_contract"]["final_status_not_running_required"] = False
        self.assert_rejected(mutated, "shutdown acceptance weakened")

    def test_raw_control_output_retention_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["control_evidence_contract"]["raw_control_output_retained"] = True
        self.assert_rejected(mutated, "raw control output retained")

    def test_runtime_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["lm_studio_runtime_execution_authorized"] = True
        self.assert_rejected(mutated, "premature authorization")

    def test_standalone_installation_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["standalone_llmster_installation_authorized"] = True
        self.assert_rejected(mutated, "premature authorization")


if __name__ == "__main__":
    unittest.main()
