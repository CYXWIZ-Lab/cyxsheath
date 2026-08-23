from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_host_capacity_and_connectivity import HostCapacityError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_host_capacity_and_connectivity.json"


class HostCapacityAndConnectivityTests(unittest.TestCase):
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

    def test_record_preserves_pending_decision_boundary(self) -> None:
        self.assertEqual("not_ready", self.record["capacity_assessment"]["runtime_readiness"])
        self.assertFalse(self.record["execution_boundary"]["model_selected"])
        self.assertFalse(self.record["execution_boundary"]["benchmark_input_authorized"])

    def test_sensitive_host_key_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["host"]["hostname"] = "not-for-evidence"
        with self.assertRaisesRegex(HostCapacityError, "forbidden sensitive keys"):
            validate(self.write_record(mutated))

    def test_failed_tcp_connection_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["docker"]["connectivity"]["tcp_connected"] = False
        with self.assertRaisesRegex(HostCapacityError, "tcp_connected"):
            validate(self.write_record(mutated))

    def test_residual_probe_container_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["docker"]["connectivity"]["container_absent_after"] = False
        with self.assertRaisesRegex(HostCapacityError, "container_absent_after"):
            validate(self.write_record(mutated))

    def test_model_selection_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_boundary"]["model_selected"] = True
        with self.assertRaisesRegex(HostCapacityError, "model_selected"):
            validate(self.write_record(mutated))

    def test_runtime_readiness_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["runtimes"]["lm_studio_cli"]["ready"] = True
        with self.assertRaisesRegex(HostCapacityError, "ready"):
            validate(self.write_record(mutated))

    def test_large_gpu_fit_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["capacity_assessment"]["gpu_model_fit"] = "large_gpu_model_supported"
        with self.assertRaisesRegex(HostCapacityError, "GPU fit overclaim"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
