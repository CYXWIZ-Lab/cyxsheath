from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_cli_exit_transport_decision import CliExitTransportDecisionError, validate


EVIDENCE = Path(__file__).parent / "review_evidence" / "phase6_cli_exit_transport_decision.json"


class CliExitTransportDecisionTests(unittest.TestCase):
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

    def test_fixture_transport_only_authorizes_help_probe(self) -> None:
        self.assertTrue(self.record["execution_gate"]["cli_help_probe_authorized_once"])
        self.assertFalse(self.record["execution_gate"]["load_health_retry_authorized"])

    def test_dependency_growth_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["structural_decision"]["new_dependency_count"] = 1
        with self.assertRaisesRegex(CliExitTransportDecisionError, "dependency growth admitted"):
            validate(self.write_record(mutated))

    def test_shell_execution_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["transport_contract"]["shell"] = True
        with self.assertRaisesRegex(CliExitTransportDecisionError, "transport surface widened"):
            validate(self.write_record(mutated))

    def test_streaming_limit_overclaim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["known_limit"]["streaming_memory_limit_enforced"] = True
        with self.assertRaisesRegex(CliExitTransportDecisionError, "streaming bound overclaim"):
            validate(self.write_record(mutated))

    def test_probe_attempt_widening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["authorized_cli_probe"]["maximum_attempts"] = 2
        with self.assertRaisesRegex(CliExitTransportDecisionError, "probe attempts widened"):
            validate(self.write_record(mutated))

    def test_probe_command_widening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["authorized_cli_probe"]["command"] = "temporary_lms_exe daemon up"
        with self.assertRaisesRegex(CliExitTransportDecisionError, "probe command widened"):
            validate(self.write_record(mutated))

    def test_model_load_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["security_and_research_boundary"]["model_load_command_count"] = 1
        with self.assertRaisesRegex(CliExitTransportDecisionError, "runtime operation admitted"):
            validate(self.write_record(mutated))

    def test_load_health_retry_authorization_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["execution_gate"]["load_health_retry_authorized"] = True
        with self.assertRaisesRegex(CliExitTransportDecisionError, "premature authorization"):
            validate(self.write_record(mutated))


if __name__ == "__main__":
    unittest.main()
