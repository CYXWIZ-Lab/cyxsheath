from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_cyxcode_synthetic_canary import (
    MODEL,
    PROHIBITED_MARKERS,
    assert_synthetic_boundary,
    build_parser,
    cyxcode_config,
    task_record,
)


class SyntheticCanaryRunnerTests(unittest.TestCase):
    def test_route_is_free_and_explicitly_configured(self) -> None:
        config = cyxcode_config()
        model = config["provider"]["opencode"]["models"]["mimo-v2.5-free"]
        self.assertEqual("opencode/mimo-v2.5-free", MODEL)
        self.assertEqual({"input": 0, "output": 0}, model["cost"])
        self.assertEqual("public", config["provider"]["opencode"]["options"]["apiKey"])

    def test_cli_has_no_benchmark_input_parameters(self) -> None:
        destinations = {action.dest for action in build_parser()._actions}
        self.assertTrue({"artifact_root", "output", "recorded_at", "timeout_seconds"} <= destinations)
        self.assertTrue({"candidate", "ledger", "multilingual", "verified"}.isdisjoint(destinations))

    def test_generated_fixture_passes_boundary_check(self) -> None:
        source = Path(__file__).parent / "__nonexistent_synthetic_fixture__"
        record = task_record("sha256:synthetic")
        assert_synthetic_boundary(source, record)
        combined = json.dumps(record).lower()
        self.assertFalse(any(marker in combined for marker in PROHIBITED_MARKERS))

    def test_benchmark_marker_is_rejected(self) -> None:
        source = Path(__file__).parent / "__nonexistent_synthetic_fixture__"
        record = task_record("sha256:synthetic")
        record["raw_request"] = "Use a SWE-bench task."
        with self.assertRaisesRegex(ValueError, "prohibited marker"):
            assert_synthetic_boundary(source, record)


if __name__ == "__main__":
    unittest.main()
