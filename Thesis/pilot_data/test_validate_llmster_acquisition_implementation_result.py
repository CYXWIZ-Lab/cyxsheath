from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_acquisition_implementation_result import (
    LlmsterAcquisitionImplementationError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_llmster_acquisition_implementation_result.json"
)


class LlmsterAcquisitionImplementationResultTests(unittest.TestCase):
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
        with self.assertRaisesRegex(LlmsterAcquisitionImplementationError, message):
            validate(self.write_record(record))

    def test_fixture_only_implementation_is_explicit(self) -> None:
        gate = self.record["decision_gate"]
        self.assertTrue(gate["acquisition_module_implementation_complete"])
        self.assertFalse(gate["archive_download_authorized"])

    def test_preflight_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["reviewed_decision"]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "decision digest drift")

    def test_module_source_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["source_identity"][0]["sha256"] = "0" * 64
        self.assert_rejected(mutated, "source identity drift")

    def test_redirect_permission_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["acquisition_contract"]["redirects_allowed"] = True
        self.assert_rejected(mutated, "redirect admitted")

    def test_second_attempt_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["acquisition_contract"]["maximum_attempts"] = 2
        self.assert_rejected(mutated, "attempt count widened")

    def test_storage_reserve_weakening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["acquisition_contract"]["minimum_free_bytes_after"] = 0
        self.assert_rejected(mutated, "storage reserve weakened")

    def test_partial_ownership_cleanup_weakening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["verified_behaviors"][
            "delete_only_partial_created_by_current_invocation_on_failure"
        ] = False
        self.assert_rejected(mutated, "verified behavior weakened")

    def test_fixture_network_request_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["fixture_evidence"]["fixture_network_request_count"] = 1
        self.assert_rejected(mutated, "operation admitted")

    def test_archive_download_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["decision_gate"]["archive_download_authorized"] = True
        self.assert_rejected(mutated, "premature authorization")

    def test_dependency_growth_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["module_boundary"]["new_dependency_count"] = 1
        self.assert_rejected(mutated, "dependency growth admitted")


if __name__ == "__main__":
    unittest.main()
