from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from cli_transport import CliTransportResult
from lm_studio_lifecycle import (
    LifecycleError,
    observe_control,
    observe_standalone_shutdown,
    parse_daemon_status,
    parse_daemon_up,
    require_standalone_start,
)


def result(returncode: int, stdout: bytes = b"", stderr: bytes = b"") -> CliTransportResult:
    return CliTransportResult(returncode, stdout, stderr, 7)


def encoded(value: dict) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode()


class LmStudioLifecycleTests(unittest.TestCase):
    def test_startup_json_proves_standalone_mode_and_owned_pid(self) -> None:
        payload = encoded(
            {"status": "running", "pid": 42, "isDaemon": True, "version": "0.4.21+2"}
        )
        info = parse_daemon_up(result(0, payload))
        require_standalone_start(info, owned_root_pid=42)
        self.assertTrue(info.is_daemon)
        self.assertEqual("0.4.21+2", info.version)

    def test_desktop_service_mode_is_rejected_before_load(self) -> None:
        info = parse_daemon_up(
            result(
                0,
                encoded(
                    {"status": "running", "pid": 42, "isDaemon": False, "version": "0.4.21+2"}
                ),
            )
        )
        with self.assertRaisesRegex(LifecycleError, "desktop_service_mode_incompatible"):
            require_standalone_start(info, owned_root_pid=42)

    def test_startup_pid_must_match_owned_root(self) -> None:
        info = parse_daemon_up(
            result(
                0,
                encoded(
                    {"status": "running", "pid": 42, "isDaemon": True, "version": "0.4.21+2"}
                ),
            )
        )
        with self.assertRaisesRegex(LifecycleError, "owned_root_mismatch"):
            require_standalone_start(info, owned_root_pid=43)

    def test_invalid_json_and_status_shapes_are_rejected(self) -> None:
        with self.assertRaisesRegex(LifecycleError, "daemon_up_json_invalid"):
            parse_daemon_up(result(0, b"not-json"))
        with self.assertRaisesRegex(LifecycleError, "daemon_status_mode_invalid"):
            parse_daemon_status(result(0, encoded({"status": "running", "pid": 4})))

    def test_control_observation_retains_only_bounded_metadata(self) -> None:
        stdout = b'{"status":"not-running"}'
        observation = observe_control("daemon_status_json", result(0, stdout, b""))
        record = observation.to_record()
        self.assertEqual(len(stdout), record["stdout_bytes"])
        self.assertEqual(hashlib.sha256(stdout).hexdigest(), record["stdout_sha256"])
        self.assertEqual("json_payload", record["diagnostic_code"])
        self.assertNotIn("stdout", record)
        self.assertNotIn("stderr", record)

    def test_known_desktop_refusal_is_allowlisted(self) -> None:
        message = (
            b"The daemon is currently running as part of LM Studio. "
            b"Please exit LM Studio to stop it.\n"
        )
        observation = observe_control("daemon_down", result(1, message))
        self.assertEqual("desktop_service_refusal", observation.diagnostic_code)
        self.assertEqual(1, observation.returncode)

    def test_successful_shutdown_requires_status_not_running(self) -> None:
        calls: list[str] = []
        statuses = iter(
            [
                result(0, encoded({"status": "running", "pid": 42, "isDaemon": True})),
                result(0, encoded({"status": "not-running"})),
            ]
        )

        def read_status() -> CliTransportResult:
            calls.append("status")
            return next(statuses)

        def run_down() -> CliTransportResult:
            calls.append("down")
            return result(0, b"Shutting down llmster...\nDone.\n")

        observation = observe_standalone_shutdown(
            status_reader=read_status,
            down_runner=run_down,
            expected_pid=42,
            timeout_seconds=10,
            poll_interval_seconds=0.25,
        )
        self.assertEqual(["status", "down", "status"], calls)
        self.assertEqual("not-running", observation.status_after.status)
        self.assertEqual(1, observation.status_poll_count)
        self.assertEqual("shutdown_requested", observation.daemon_down_control.diagnostic_code)

    def test_nonzero_down_exit_is_retained_even_if_status_stops(self) -> None:
        statuses = iter(
            [
                result(0, encoded({"status": "running", "pid": 42, "isDaemon": True})),
                result(0, encoded({"status": "not-running"})),
            ]
        )
        observation = observe_standalone_shutdown(
            status_reader=lambda: next(statuses),
            down_runner=lambda: result(1, b"unexpected"),
            expected_pid=42,
            timeout_seconds=10,
            poll_interval_seconds=0.25,
        )
        self.assertEqual(1, observation.daemon_down_control.returncode)
        self.assertEqual("not-running", observation.status_after.status)

    def test_desktop_status_blocks_down_command(self) -> None:
        down_calls = 0

        def run_down() -> CliTransportResult:
            nonlocal down_calls
            down_calls += 1
            return result(0)

        with self.assertRaisesRegex(LifecycleError, "target_not_standalone"):
            observe_standalone_shutdown(
                status_reader=lambda: result(
                    0, encoded({"status": "running", "pid": 42, "isDaemon": False})
                ),
                down_runner=run_down,
                expected_pid=42,
                timeout_seconds=10,
                poll_interval_seconds=0.25,
            )
        self.assertEqual(0, down_calls)

    def test_status_pid_mismatch_blocks_down_command(self) -> None:
        down_calls = 0

        def run_down() -> CliTransportResult:
            nonlocal down_calls
            down_calls += 1
            return result(0)

        with self.assertRaisesRegex(LifecycleError, "target_pid_mismatch"):
            observe_standalone_shutdown(
                status_reader=lambda: result(
                    0, encoded({"status": "running", "pid": 41, "isDaemon": True})
                ),
                down_runner=run_down,
                expected_pid=42,
                timeout_seconds=10,
                poll_interval_seconds=0.25,
            )
        self.assertEqual(0, down_calls)


if __name__ == "__main__":
    unittest.main()
