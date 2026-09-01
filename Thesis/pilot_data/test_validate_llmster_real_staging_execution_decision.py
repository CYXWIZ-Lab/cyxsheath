from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_llmster_real_staging_execution_decision import (
    LlmsterRealStagingExecutionDecisionError,
    validate,
    validate_live_preconditions,
)


EVIDENCE = (
    Path(__file__).parent
    / "review_evidence"
    / "phase6_llmster_real_staging_execution_decision.json"
)


class LlmsterRealStagingExecutionDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = validate(EVIDENCE, enforce_live_preconditions=False)

    def rejected(self, record: dict, message: str) -> None:
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".json", dir=EVIDENCE.parent, delete=False
        )
        with handle:
            json.dump(record, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with self.assertRaisesRegex(LlmsterRealStagingExecutionDecisionError, message):
            validate(Path(handle.name), enforce_live_preconditions=False)

    def test_exact_one_shot_staging_is_authorized(self) -> None:
        gate = self.record["execution_gate"]
        self.assertTrue(gate["real_archive_owned_staging_authorized_once"])
        self.assertFalse(gate["authenticode_tool_invocation_authorized"])

    def test_implementation_digest_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["reviewed_implementation"]["sha256"] = "0" * 64
        self.rejected(item, "implementation digest drift")

    def test_inventory_digest_drift_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["accepted_inventory"]["sha256"] = "0" * 64
        self.rejected(item, "inventory digest drift")

    def test_storage_reserve_weakening_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["fresh_storage_preflight"]["minimum_free_bytes_after"] -= 1
        self.rejected(item, "final reserve weakened")

    def test_second_invocation_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["one_shot_call"]["maximum_function_invocations"] = 2
        self.rejected(item, "one-shot call drift")

    def test_retry_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["execution_gate"]["automatic_retry_authorized"] = True
        self.rejected(item, "premature authorization")

    def test_signature_tooling_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["execution_gate"]["authenticode_tool_invocation_authorized"] = True
        self.rejected(item, "premature authorization")

    def test_installation_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["execution_gate"]["installation_authorized"] = True
        self.rejected(item, "premature authorization")

    def test_member_path_retention_is_rejected(self) -> None:
        item = copy.deepcopy(self.record)
        item["result_contract"]["individual_member_paths_or_contents_may_be_curated"] = True
        self.rejected(item, "result contract weakened")

    def test_live_preconditions_accept_empty_parent_and_exact_floor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / ".replay_cache" / "llmster_staging").mkdir(parents=True)
            required = self.record["fresh_storage_preflight"]["minimum_free_bytes_before"]
            validate_live_preconditions(self.record, root, lambda _path: required)

    def test_live_nonempty_parent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            parent = root / ".replay_cache" / "llmster_staging"
            parent.mkdir(parents=True)
            (parent / "unexpected.txt").write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(
                LlmsterRealStagingExecutionDecisionError,
                "live staging parent not empty",
            ):
                validate_live_preconditions(self.record, root, lambda _path: 10**12)

    def test_live_insufficient_storage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / ".replay_cache" / "llmster_staging").mkdir(parents=True)
            required = self.record["fresh_storage_preflight"]["minimum_free_bytes_before"]
            with self.assertRaisesRegex(
                LlmsterRealStagingExecutionDecisionError,
                "live storage gate failed",
            ):
                validate_live_preconditions(self.record, root, lambda _path: required - 1)


if __name__ == "__main__":
    unittest.main()
