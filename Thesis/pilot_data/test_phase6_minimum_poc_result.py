from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from validate_phase6_minimum_poc_result import PocResultError, validate_result


RESULT = Path(__file__).parent / "poc_evidence" / "phase6_minimum_poc_v1.json"


class MinimumPocResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads(RESULT.read_text(encoding="utf-8"))

    def _reject(self, mutate, message: str) -> None:
        record = copy.deepcopy(self.record)
        mutate(record)
        with TemporaryDirectory(dir=Path(__file__).parent) as name:
            path = Path(name) / "result.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(PocResultError, message):
                validate_result(path)

    def test_committed_result_is_valid(self) -> None:
        validated = validate_result(RESULT)
        self.assertEqual(5, validated["summary"]["infrastructure_failures"])
        self.assertFalse(validated["summary"]["inferential_claim_authorized"])

    def test_unknown_or_raw_fields_are_rejected(self) -> None:
        self._reject(lambda value: value.update({"prompt": "raw"}), "fields invalid|raw artifact")

    def test_schedule_drift_is_rejected(self) -> None:
        self._reject(lambda value: value["runs"].reverse(), "run order drift")

    def test_summary_drift_is_rejected(self) -> None:
        self._reject(lambda value: value["summary"].update({"infrastructure_failures": 4}), "summary mismatch")

    def test_failure_cannot_be_presented_as_task_completion(self) -> None:
        self._reject(lambda value: value["runs"][1].update({"status": "completed"}), "completion inconsistent")

    def test_record_digest_must_be_unique(self) -> None:
        self._reject(
            lambda value: value["runs"][1].update({"record_digest": value["runs"][0]["record_digest"]}),
            "digest duplicated",
        )

    def test_source_binding_is_enforced(self) -> None:
        self._reject(lambda value: value.update({"runner_sha256": "0" * 64}), "runner digest drift")


if __name__ == "__main__":
    unittest.main()
