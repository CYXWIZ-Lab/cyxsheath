from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

import run_local_model_load_health as runner


class LocalModelLoadHealthRunnerTests(unittest.TestCase):
    def valid_authorization(self) -> dict:
        return {
            "schema_version": "1.0.0",
            "status": "python_load_health_runner_execution_authorized_once",
            "decision_scope": "one_exact_load_health_execution_without_inference_or_http_server",
            "integration_decision_sha256": runner.file_sha256(runner.INTEGRATION_DECISION),
            "runner_sha256": runner.file_sha256(Path(runner.__file__)),
            "monitored_process_sha256": runner.file_sha256(
                Path(runner.__file__).parent / "monitored_process.py"
            ),
            "windows_adapter_sha256": runner.file_sha256(
                Path(runner.__file__).parent / "lm_studio_windows.py"
            ),
            "maximum_attempts": 1,
            "settings": runner._authorization_settings(),
        }

    def test_missing_execution_authorization_blocks_before_host_access(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing.json"
            cache = Path(temporary) / "cache"
            with (
                patch.object(runner, "EXECUTION_AUTHORIZATION", missing),
                patch.object(runner, "CACHE", cache),
                patch.object(runner, "host_snapshot", side_effect=AssertionError("host accessed")),
            ):
                self.assertEqual(runner.main(), 2)
            self.assertFalse(cache.exists())

    def test_exact_load_command_remains_cpu_only_and_non_serving(self) -> None:
        self.assertEqual(
            runner.LOAD_ARGS,
            (
                "load",
                "qwen2.5-coder-7b-instruct",
                "--gpu",
                "off",
                "--context-length",
                "8192",
                "--parallel",
                "1",
                "--ttl",
                "600",
                "--no-speculative-draft-mtp",
                "--identifier",
                "cyxsheath-qwen25-coder-7b-q4km",
                "--yes",
            ),
        )
        self.assertNotIn("serve", runner.LOAD_ARGS)

    def test_execution_authorization_rejects_setting_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "authorization.json"
            record = self.valid_authorization()
            record["settings"]["gpu_offload"] = "max"
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(runner.ActivationError, "settings_mismatch"):
                runner.validate_execution_authorization(path)

    def test_prior_result_blocks_before_host_access_and_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authorization = root / "authorization.json"
            authorization.write_text(json.dumps(self.valid_authorization()), encoding="utf-8")
            cache = root / "cache"
            cache.mkdir()
            output = cache / "result.json"
            original = b"immutable-prior-result\n"
            output.write_bytes(original)
            with (
                patch.object(runner, "EXECUTION_AUTHORIZATION", authorization),
                patch.object(runner, "CACHE", cache),
                patch.object(runner, "OUTPUT", output),
                patch.object(runner, "EXECUTION_CLAIM", cache / "execution_claim.json"),
                patch.object(runner, "host_snapshot", side_effect=AssertionError("host accessed")),
                patch.object(runner, "run_attempt", side_effect=AssertionError("attempt started")),
            ):
                self.assertEqual(runner.main(), 2)
            self.assertEqual(original, output.read_bytes())
            self.assertEqual([output], list(cache.iterdir()))

    def test_execution_claim_is_retained_and_blocks_second_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authorization = root / "authorization.json"
            authorization.write_text(json.dumps(self.valid_authorization()), encoding="utf-8")
            cache = root / "cache"
            claim = cache / "execution_claim.json"
            output = cache / "result.json"
            with (
                patch.object(runner, "EXECUTION_AUTHORIZATION", authorization),
                patch.object(runner, "CACHE", cache),
                patch.object(runner, "OUTPUT", output),
                patch.object(runner, "EXECUTION_CLAIM", claim),
                patch.object(runner, "run_attempt", return_value=0) as attempt,
            ):
                self.assertEqual(runner.main(), 0)
            attempt.assert_called_once()
            original_claim = claim.read_bytes()
            claim_record = json.loads(original_claim)
            self.assertEqual(runner.file_sha256(authorization), claim_record["authorization_sha256"])
            self.assertEqual(runner.file_sha256(Path(runner.__file__)), claim_record["runner_sha256"])
            self.assertEqual(runner.file_sha256(claim), attempt.call_args.args[1])
            with (
                patch.object(runner, "EXECUTION_AUTHORIZATION", authorization),
                patch.object(runner, "CACHE", cache),
                patch.object(runner, "OUTPUT", output),
                patch.object(runner, "EXECUTION_CLAIM", claim),
                patch.object(runner, "run_attempt", side_effect=AssertionError("attempt repeated")),
            ):
                self.assertEqual(runner.main(), 2)
            self.assertEqual(original_claim, claim.read_bytes())
            self.assertFalse(output.exists())

    def test_unexpected_existing_cache_blocks_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authorization = root / "authorization.json"
            authorization.write_text(json.dumps(self.valid_authorization()), encoding="utf-8")
            cache = root / "cache"
            cache.mkdir()
            marker = cache / "unrelated.bin"
            marker.write_bytes(b"preserve")
            with (
                patch.object(runner, "EXECUTION_AUTHORIZATION", authorization),
                patch.object(runner, "CACHE", cache),
                patch.object(runner, "OUTPUT", cache / "result.json"),
                patch.object(runner, "EXECUTION_CLAIM", cache / "execution_claim.json"),
                patch.object(runner, "host_snapshot", side_effect=AssertionError("host accessed")),
            ):
                self.assertEqual(runner.main(), 2)
            self.assertEqual(b"preserve", marker.read_bytes())

    def test_process_tree_uses_exact_root_identity(self) -> None:
        processes = (
            runner.ProcessEntry(10, 1, "a", "LM Studio.exe", "--run-as-service", 1, 2),
            runner.ProcessEntry(11, 10, "b", "child.exe", "", 3, 4),
            runner.ProcessEntry(12, 11, "c", "grandchild.exe", "", 5, 6),
            runner.ProcessEntry(20, 1, "d", "unowned.exe", "", 7, 8),
        )
        snapshot = runner.HostSnapshot(30_000_000_000, False, processes)
        tree = runner.process_tree(snapshot, runner.OwnedRoot(10, "a"))
        self.assertEqual({10, 11, 12}, {item.pid for item in tree})
        with self.assertRaisesRegex(runner.WindowsHostError, "identity_missing"):
            runner.process_tree(snapshot, runner.OwnedRoot(10, "wrong"))

    def test_inventory_parser_keeps_only_frozen_identity_fields(self) -> None:
        payload = json.dumps(
            [
                {
                    "identifier": runner.IDENTIFIER,
                    "modelKey": runner.MODEL_KEY,
                    "contextLength": 8192,
                    "unused": "not retained",
                }
            ]
        ).encode()
        self.assertEqual(
            runner.parse_inventory(payload),
            [
                {
                    "identifier": runner.IDENTIFIER,
                    "modelKey": runner.MODEL_KEY,
                    "contextLength": 8192,
                }
            ],
        )

    def test_engine_inventory_digest_is_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "b.bin").write_bytes(b"b")
            (root / "a.bin").write_bytes(b"a")
            entries = [
                {
                    "path": "a.bin",
                    "bytes": 1,
                    "sha256": hashlib.sha256(b"a").hexdigest(),
                },
                {
                    "path": "b.bin",
                    "bytes": 1,
                    "sha256": hashlib.sha256(b"b").hexdigest(),
                },
            ]
            expected = hashlib.sha256(
                json.dumps(entries, separators=(",", ":")).encode()
            ).hexdigest()
            self.assertEqual((2, 2, expected), runner.engine_identity(root))


if __name__ == "__main__":
    unittest.main()
