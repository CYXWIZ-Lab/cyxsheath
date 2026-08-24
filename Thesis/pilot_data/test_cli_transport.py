from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from cli_transport import CliTransportError, CliTransportTimeout, run_cli


PYTHON = str(Path(sys.executable).resolve())


class CliTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cwd = Path.cwd().resolve()

    def run_python(self, source: str, *args: str, timeout: float = 5, maximum: int = 4096):
        return run_cli(
            (PYTHON, "-c", source, *args),
            cwd=self.cwd,
            timeout_seconds=timeout,
            max_output_bytes=maximum,
        )

    def test_zero_exit_and_separate_outputs_are_observed(self) -> None:
        result = self.run_python(
            "import sys; print('out'); print('err', file=sys.stderr)"
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), b"out")
        self.assertEqual(result.stderr.strip(), b"err")
        self.assertGreaterEqual(result.elapsed_milliseconds, 0)

    def test_nonzero_exit_is_numeric_and_not_raised(self) -> None:
        result = self.run_python("raise SystemExit(7)")
        self.assertEqual(result.returncode, 7)

    def test_argument_is_not_interpreted_by_a_shell(self) -> None:
        marker = "literal&whoami|still-literal"
        result = self.run_python("import sys; print(sys.argv[1])", marker)
        self.assertEqual(result.stdout.decode().strip(), marker)

    def test_timeout_fails_without_an_exit_claim(self) -> None:
        with self.assertRaisesRegex(CliTransportTimeout, "frozen timeout"):
            self.run_python("import time; time.sleep(2)", timeout=0.05)

    def test_combined_output_above_bound_is_rejected(self) -> None:
        with self.assertRaisesRegex(CliTransportError, "retention bound"):
            self.run_python("print('x' * 64)", maximum=32)

    def test_relative_executable_is_rejected(self) -> None:
        with self.assertRaisesRegex(CliTransportError, "absolute executable"):
            run_cli(
                ("python", "--version"),
                cwd=self.cwd,
                timeout_seconds=5,
                max_output_bytes=1024,
            )

    def test_invalid_limits_are_rejected(self) -> None:
        with self.assertRaisesRegex(CliTransportError, "positive and finite"):
            self.run_python("pass", timeout=0)
        with self.assertRaisesRegex(CliTransportError, "positive integer"):
            self.run_python("pass", maximum=0)

    def test_os_start_failure_is_normalized(self) -> None:
        missing = self.cwd / "missing.exe"
        with self.assertRaisesRegex(CliTransportError, "existing absolute executable"):
            run_cli(
                (str(missing),),
                cwd=self.cwd,
                timeout_seconds=5,
                max_output_bytes=1024,
            )


if __name__ == "__main__":
    unittest.main()
