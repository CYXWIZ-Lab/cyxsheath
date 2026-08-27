from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_acquisition_preflight_decision import (
    LlmsterAcquisitionPreflightDecisionError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_llmster_acquisition_preflight_decision.json"
)


class LlmsterAcquisitionPreflightDecisionTests(unittest.TestCase):
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
        with self.assertRaisesRegex(LlmsterAcquisitionPreflightDecisionError, message):
            validate(self.write_record(record))

    def test_runner_fixtures_are_authorized_while_download_is_blocked(self) -> None:
        gate = self.record["decision_gate"]
        self.assertTrue(gate["acquisition_runner_implementation_and_fixtures_authorized"])
        self.assertFalse(gate["archive_download_authorized"])

    def test_lifecycle_selection_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["reviewed_evidence"]["lifecycle_selection"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "digest drift")

    def test_published_checksum_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["official_release_metadata"]["published_sha512"] = "0" * 128
        self.assert_rejected(mutated, "checksum linkage drift")

    def test_mutable_installer_use_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["acquisition_strategy"]["mutable_installer_used"] = True
        self.assert_rejected(mutated, "mutable installer admitted")

    def test_redirect_permission_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["acquisition_strategy"]["redirects_allowed"] = True
        self.assert_rejected(mutated, "redirect admitted")

    def test_second_attempt_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["acquisition_strategy"]["maximum_attempts"] = 2
        self.assert_rejected(mutated, "attempt count widened")

    def test_storage_reserve_weakening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["acquisition_strategy"]["minimum_free_bytes_after"] = 0
        self.assert_rejected(mutated, "storage reserve weakened")

    def test_lmstudio_home_mutation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["existing_state_to_preserve"]["acquisition_may_modify_lmstudio_home"] = True
        self.assert_rejected(mutated, "acquisition side effect admitted")

    def test_archive_extraction_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["archive_extraction_authorized"] = True
        self.assert_rejected(mutated, "premature authorization")

    def test_archive_download_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["archive_download_authorized"] = True
        self.assert_rejected(mutated, "premature authorization")

    def test_runtime_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["lm_studio_runtime_execution_authorized"] = True
        self.assert_rejected(mutated, "premature authorization")


if __name__ == "__main__":
    unittest.main()
