from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from cli_transport import CliTransportError, CliTransportResult, CliTransportTimeout
import llmster_windows_authenticode as adapter


class LlmsterWindowsAuthenticodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.powershell = self.root / "powershell.exe"
        self.powershell.write_bytes(b"generated fake executable")
        self.powershell_sha256 = hashlib.sha256(self.powershell.read_bytes()).hexdigest()
        self.candidate = self.root / "candidate.exe"
        self.candidate.write_bytes(b"generated candidate")
        self.calls: list[tuple[tuple[str, ...], Path, float, int]] = []

    def result(self, *, returncode: int = 0, stdout: bytes | None = None, stderr: bytes = b"") -> CliTransportResult:
        if stdout is None:
            stdout = json.dumps({"schema_version": "1.0.0", "status": "Valid"}, separators=(",", ":")).encode()
        return CliTransportResult(returncode=returncode, stdout=stdout, stderr=stderr, elapsed_milliseconds=1)

    def transport(self, argv: tuple[str, ...], *, cwd: Path, timeout_seconds: float, max_output_bytes: int) -> CliTransportResult:
        self.calls.append((argv, cwd, timeout_seconds, max_output_bytes))
        return self.result()

    def inspect(self, transport=None):
        return adapter.inspect_candidate(
            self.candidate,
            powershell_path=self.powershell,
            expected_powershell_sha256=self.powershell_sha256,
            transport=transport or self.transport,
        )

    def test_valid_status_uses_exact_literal_noninteractive_request(self) -> None:
        observation = self.inspect()
        self.assertEqual(("status", "Valid"), (observation.kind, observation.signature_status))
        self.assertEqual(1, len(self.calls))
        argv, cwd, timeout, maximum = self.calls[0]
        self.assertEqual(
            (
                str(self.powershell),
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(adapter.SCRIPT_PATH),
                "-CandidatePath",
                str(self.candidate),
            ),
            argv,
        )
        self.assertEqual(adapter.SCRIPT_PATH.parent, cwd)
        self.assertEqual(10.0, timeout)
        self.assertEqual(4096, maximum)

    def test_special_candidate_characters_remain_one_argument(self) -> None:
        self.candidate = self.root / "literal & '[brackets].ps1"
        self.candidate.write_bytes(b"generated script")
        self.inspect()
        self.assertEqual(str(self.candidate), self.calls[0][0][-1])
        self.assertEqual("-CandidatePath", self.calls[0][0][-2])

    def test_unknown_status_remains_typed_status_for_policy(self) -> None:
        def unknown(*args, **kwargs):
            return self.result(stdout=b'{"schema_version":"1.0.0","status":"FutureStatus"}')

        observation = self.inspect(unknown)
        self.assertEqual(("status", "FutureStatus"), (observation.kind, observation.signature_status))

    def test_timeout_is_distinct(self) -> None:
        def timeout(*args, **kwargs):
            raise CliTransportTimeout("fixture")

        self.assertEqual("timeout", self.inspect(timeout).kind)

    def test_transport_error_maps_to_tool_error(self) -> None:
        def failed(*args, **kwargs):
            raise CliTransportError("fixture")

        self.assertEqual("tool_error", self.inspect(failed).kind)

    def test_nonzero_exit_maps_to_tool_error(self) -> None:
        self.assertEqual("tool_error", self.inspect(lambda *args, **kwargs: self.result(returncode=1)).kind)

    def test_stderr_on_zero_exit_maps_to_tool_error(self) -> None:
        self.assertEqual("tool_error", self.inspect(lambda *args, **kwargs: self.result(stderr=b"unexpected")).kind)

    def test_malformed_json_maps_to_tool_error(self) -> None:
        self.assertEqual("tool_error", self.inspect(lambda *args, **kwargs: self.result(stdout=b"not-json")).kind)

    def test_duplicate_json_keys_map_to_tool_error(self) -> None:
        output = b'{"schema_version":"1.0.0","status":"Valid","status":"NotSigned"}'
        self.assertEqual("tool_error", self.inspect(lambda *args, **kwargs: self.result(stdout=output)).kind)

    def test_extra_json_key_maps_to_tool_error(self) -> None:
        output = b'{"schema_version":"1.0.0","status":"Valid","subject":"private"}'
        self.assertEqual("tool_error", self.inspect(lambda *args, **kwargs: self.result(stdout=output)).kind)

    def test_wrong_schema_maps_to_tool_error(self) -> None:
        output = b'{"schema_version":"2.0.0","status":"Valid"}'
        self.assertEqual("tool_error", self.inspect(lambda *args, **kwargs: self.result(stdout=output)).kind)

    def test_invalid_or_oversized_status_maps_to_tool_error(self) -> None:
        invalid = b'{"schema_version":"1.0.0","status":"not valid"}'
        self.assertEqual("tool_error", self.inspect(lambda *args, **kwargs: self.result(stdout=invalid)).kind)
        oversized = b"{" + b" " * adapter.MAX_STDOUT_JSON_BYTES + b"}"
        self.assertEqual("tool_error", self.inspect(lambda *args, **kwargs: self.result(stdout=oversized)).kind)

    def test_optional_utf8_bom_is_accepted(self) -> None:
        output = b'\xef\xbb\xbf{"schema_version":"1.0.0","status":"NotSigned"}\r\n'
        observation = self.inspect(lambda *args, **kwargs: self.result(stdout=output))
        self.assertEqual(("status", "NotSigned"), (observation.kind, observation.signature_status))

    def test_wrong_executable_name_or_digest_rejects_before_transport(self) -> None:
        wrong_name = self.root / "pwsh.exe"
        wrong_name.write_bytes(self.powershell.read_bytes())
        with self.assertRaisesRegex(adapter.WindowsAuthenticodeAdapterError, "powershell_name_rejected"):
            adapter.inspect_candidate(wrong_name, powershell_path=wrong_name, expected_powershell_sha256=self.powershell_sha256, transport=self.transport)
        with self.assertRaisesRegex(adapter.WindowsAuthenticodeAdapterError, "powershell_digest_mismatch"):
            adapter.inspect_candidate(self.candidate, powershell_path=self.powershell, expected_powershell_sha256="0" * 64, transport=self.transport)
        self.assertEqual([], self.calls)

    def test_relative_or_unsupported_candidate_rejects_before_transport(self) -> None:
        with self.assertRaisesRegex(adapter.WindowsAuthenticodeAdapterError, "candidate_must_be_absolute"):
            adapter.inspect_candidate(Path("relative.exe"), powershell_path=self.powershell, expected_powershell_sha256=self.powershell_sha256, transport=self.transport)
        self.candidate = self.root / "candidate.txt"
        self.candidate.write_bytes(b"not supported")
        with self.assertRaisesRegex(adapter.WindowsAuthenticodeAdapterError, "candidate_suffix_rejected"):
            self.inspect()
        self.assertEqual([], self.calls)

    def test_executable_mutation_during_transport_is_rejected(self) -> None:
        def mutate(*args, **kwargs):
            self.powershell.write_bytes(b"changed executable")
            return self.result()

        with self.assertRaisesRegex(adapter.WindowsAuthenticodeAdapterError, "powershell_changed_during_transport"):
            self.inspect(mutate)

    def test_candidate_mutation_during_transport_is_rejected(self) -> None:
        def mutate(*args, **kwargs):
            self.candidate.write_bytes(b"changed candidate")
            return self.result()

        with self.assertRaisesRegex(adapter.WindowsAuthenticodeAdapterError, "candidate_changed_during_transport"):
            self.inspect(mutate)

    def test_script_digest_drift_rejects_before_transport(self) -> None:
        with patch.object(adapter, "SCRIPT_SHA256", "0" * 64):
            with self.assertRaisesRegex(adapter.WindowsAuthenticodeAdapterError, "script_digest_mismatch"):
                self.inspect()
        self.assertEqual([], self.calls)

    def test_unexpected_transport_exception_is_not_concealed(self) -> None:
        def broken(*args, **kwargs):
            raise RuntimeError("adapter bug")

        with self.assertRaisesRegex(RuntimeError, "adapter bug"):
            self.inspect(broken)

    def test_fixed_script_has_literal_path_and_no_execution_policy_change(self) -> None:
        source = adapter.SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("Get-AuthenticodeSignature -LiteralPath $CandidatePath", source)
        self.assertNotIn("Invoke-Expression", source)
        self.assertNotIn("Set-ExecutionPolicy", source)
        self.assertNotIn("Start-Process", source)


if __name__ == "__main__":
    unittest.main()
