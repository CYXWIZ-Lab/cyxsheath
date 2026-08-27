from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_runtime_lifecycle_selection_decision import (
    RuntimeLifecycleSelectionDecisionError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_runtime_lifecycle_selection_decision.json"
)


class RuntimeLifecycleSelectionDecisionTests(unittest.TestCase):
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
        with self.assertRaisesRegex(RuntimeLifecycleSelectionDecisionError, message):
            validate(self.write_record(record))

    def test_standalone_selection_is_explicit_and_runtime_blocked(self) -> None:
        self.assertEqual("standalone_llmster", self.record["selection"]["selected_family"])
        self.assertFalse(self.record["decision_gate"]["standalone_llmster_installation_authorized"])

    def test_prior_implementation_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["reviewed_evidence"]["shutdown_implementation"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "digest drift")

    def test_desktop_service_selection_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["selection"]["selected_family"] = "lm_studio_desktop_headless_service"
        self.assert_rejected(mutated, "incompatible lifecycle selected")

    def test_forced_cleanup_success_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["rejected_alternatives"][1]["decision"] = "accepted_shutdown"
        self.assert_rejected(mutated, "forced cleanup accepted")

    def test_mutable_shell_pipeline_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["windows_installer_review"]["official_shell_pipeline_authorized"] = True
        self.assert_rejected(mutated, "mutable shell pipeline authorized")

    def test_checksum_skip_concealment_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["windows_installer_review"]["missing_checksum_can_skip_verification"] = False
        self.assert_rejected(mutated, "installer risk concealed")

    def test_installation_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["standalone_llmster_installation_authorized"] = True
        self.assert_rejected(mutated, "premature authorization")

    def test_artifact_download_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["installer_or_archive_download_authorized"] = True
        self.assert_rejected(mutated, "premature authorization")

    def test_runtime_health_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["selection"]["runtime_health_status"] = "passed"
        self.assert_rejected(mutated, "runtime health overclaim")

    def test_model_change_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["selection"]["model_or_quantization_change_required"] = True
        self.assert_rejected(mutated, "model drift admitted")


if __name__ == "__main__":
    unittest.main()
