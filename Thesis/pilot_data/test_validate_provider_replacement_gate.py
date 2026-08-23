from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_provider_replacement_gate import ProviderGateError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_provider_replacement_gate.json"


class ProviderGateTests(unittest.TestCase):
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

    def test_two_candidates_are_fail_closed(self) -> None:
        self.assertEqual(2, len(self.record["candidates"]))
        self.assertTrue(all(item["benchmark_submission"] == "blocked" for item in self.record["candidates"]))
        self.assertFalse(self.record["outcome"]["synthetic_canary_executed"])

    def test_raw_prompt_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["prompt"] = "must not be retained"
        with self.assertRaisesRegex(ProviderGateError, "forbidden raw-content"):
            validate(self.write_record(mutated))

    def test_free_training_use_cannot_be_approved(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["candidates"][0]["decision"] = "approved"
        with self.assertRaisesRegex(ProviderGateError, "unsafe free admission"):
            validate(self.write_record(mutated))

    def test_unknown_exposure_cannot_pass_benchmark(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["candidates"][1]["benchmark_submission"] = "approved"
        with self.assertRaisesRegex(ProviderGateError, "unsafe benchmark admission"):
            validate(self.write_record(mutated))

    def test_missing_credential_cannot_claim_canary(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["outcome"]["synthetic_canary_executed"] = True
        with self.assertRaisesRegex(ProviderGateError, "unrecorded model execution"):
            validate(self.write_record(mutated))

    def test_stale_catalog_cannot_claim_current_model(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["candidates"][1]["pinned_local_catalog_listing"] = True
        with self.assertRaisesRegex(ProviderGateError, "catalog support overclaim"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
