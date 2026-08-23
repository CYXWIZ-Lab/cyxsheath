from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_local_model_load_health_decision import LoadHealthDecisionError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_local_model_load_health_decision.json"


class LocalModelLoadHealthDecisionTests(unittest.TestCase):
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

    def test_one_load_without_inference_is_authorized(self) -> None:
        self.assertEqual(1, self.record["authorization"]["maximum_attempts"])
        self.assertFalse(self.record["security_and_retention"]["inference_request_authorized"])

    def test_inference_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["security_and_retention"]["inference_request_authorized"] = True
        with self.assertRaisesRegex(LoadHealthDecisionError, "security boundary widened"):
            validate(self.write_record(mutated))

    def test_http_server_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["security_and_retention"]["http_server_start_authorized"] = True
        with self.assertRaisesRegex(LoadHealthDecisionError, "security boundary widened"):
            validate(self.write_record(mutated))

    def test_gpu_offload_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["load_contract"]["gpu_offload"] = "max"
        with self.assertRaisesRegex(LoadHealthDecisionError, "GPU offload admitted"):
            validate(self.write_record(mutated))

    def test_memory_ceiling_increase_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["observation_contract"]["maximum_activation_tree_private_bytes"] = 25769803776
        with self.assertRaisesRegex(LoadHealthDecisionError, "maximum_activation_tree_private_bytes"):
            validate(self.write_record(mutated))

    def test_cleanup_weakening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cleanup_contract"]["activation_process_tree_absent_after"] = False
        with self.assertRaisesRegex(LoadHealthDecisionError, "cleanup weakened"):
            validate(self.write_record(mutated))

    def test_premature_canary_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["synthetic_canary_authorized"] = True
        with self.assertRaisesRegex(LoadHealthDecisionError, "premature authorization"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
