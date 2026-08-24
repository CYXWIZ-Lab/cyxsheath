from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_cli_exit_transport_result import CliExitTransportResultError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_cli_exit_transport_result.json"


class CliExitTransportResultTests(unittest.TestCase):
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

    def test_numeric_help_probe_passed_without_runtime(self) -> None:
        self.assertEqual(self.record["cli_probe"]["numeric_exit_code"], 0)
        self.assertFalse(self.record["acceptance"]["load_health_gate_passed"])

    def test_numeric_exit_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cli_probe"]["numeric_exit_code"] = 1
        with self.assertRaisesRegex(CliExitTransportResultError, "numeric exit overclaim"):
            validate(self.write_record(mutated))

    def test_output_size_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["output_evidence"]["stdout_bytes"] += 1
        with self.assertRaisesRegex(CliExitTransportResultError, "stdout size drift"):
            validate(self.write_record(mutated))

    def test_raw_output_retention_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["output_evidence"]["raw_output_retained"] = True
        with self.assertRaisesRegex(CliExitTransportResultError, "raw output retained"):
            validate(self.write_record(mutated))

    def test_daemon_command_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["runtime_boundary"]["daemon_command_count"] = 1
        with self.assertRaisesRegex(CliExitTransportResultError, "runtime boundary failed"):
            validate(self.write_record(mutated))

    def test_forced_cleanup_concealment_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cleanup"]["forced_cleanup_required"] = True
        with self.assertRaisesRegex(CliExitTransportResultError, "forced cleanup concealed"):
            validate(self.write_record(mutated))

    def test_model_health_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["acceptance"]["model_health_conclusion_allowed"] = True
        with self.assertRaisesRegex(CliExitTransportResultError, "acceptance overclaim"):
            validate(self.write_record(mutated))

    def test_load_health_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["load_health_retry_authorized"] = True
        with self.assertRaisesRegex(CliExitTransportResultError, "premature authorization"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
