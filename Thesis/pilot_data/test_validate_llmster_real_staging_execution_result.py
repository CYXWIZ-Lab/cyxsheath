from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_real_staging_execution_result import (
    LlmsterRealStagingExecutionResultError,
    validate,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_llmster_real_staging_execution_result.json"
)


class LlmsterRealStagingExecutionResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE)

    def rejected(self, record: dict, message: str) -> None:
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False
        )
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with self.assertRaisesRegex(LlmsterRealStagingExecutionResultError, message):
            validate(Path(handle.name))

    def test_accepted_staging_and_closed_follow_on_gates_are_explicit(self) -> None:
        self.assertTrue(self.record["result_gate"]["real_staging_accepted"])
        self.assertFalse(self.record["result_gate"]["authenticode_tool_invocation_authorized"])

    def test_authorization_digest_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["authorization"]["sha256"] = "0" * 64
        self.rejected(item, "authorization digest drift")

    def test_unconsumed_authorization_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["authorization"]["consumed"] = False
        self.rejected(item, "authorization state concealed")

    def test_second_function_invocation_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["authorization"]["stage_archive_function_invocation_count"] = 2
        self.rejected(item, "invocation count drift")

    def test_retry_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["authorization"]["automatic_retry_count"] = 1
        self.rejected(item, "retry admitted")

    def test_pre_function_deviation_concealment_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["pre_function_command_deviation"]["occurred"] = False
        self.rejected(item, "pre-function deviation concealed")

    def test_manifest_digest_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["staging_result"]["content_manifest_sha256"] = "0" * 64
        self.rejected(item, "manifest digest drift")

    def test_signature_candidate_count_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["staging_result"]["signature_candidate_count"] = 90
        self.rejected(item, "candidate count drift")

    def test_marker_mismatch_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["owned_staging"]["ownership_marker_matches"] = False
        self.rejected(item, "owned state concealed")

    def test_signature_tool_authorization_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["result_gate"]["authenticode_tool_invocation_authorized"] = True
        self.rejected(item, "premature authorization")


if __name__ == "__main__":
    unittest.main()
