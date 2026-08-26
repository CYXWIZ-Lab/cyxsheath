from __future__ import annotations

import csv
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from monitored_process import (
    MonitoredProcessCheckFailed,
    MonitoredProcessOutputLimit,
    MonitoredProcessTimeout,
    run_monitored_process,
)


PYTHON = str(Path(sys.executable).resolve())


class MonitoredProcessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.stdout = self.root / "stdout.bin"
        self.stderr = self.root / "stderr.bin"

    def run_python(
        self,
        source: str,
        *args: str,
        timeout: float = 3,
        interval: float = 0.01,
        maximum: int = 4096,
        monitor=lambda _pid: None,
    ):
        return run_monitored_process(
            (PYTHON, "-c", source, *args),
            cwd=self.root,
            timeout_seconds=timeout,
            sample_interval_seconds=interval,
            max_output_file_bytes=maximum,
            stdout_path=self.stdout,
            stderr_path=self.stderr,
            monitor=monitor,
        )

    def assert_outputs_absent(self) -> None:
        self.assertFalse(self.stdout.exists())
        self.assertFalse(self.stderr.exists())

    def process_exists(self, pid: int) -> bool:
        completed = subprocess.run(
            ("tasklist.exe", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            check=False,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        rows = csv.reader(io.StringIO(completed.stdout.decode("utf-8", errors="replace")))
        return any(len(row) > 1 and row[1].strip() == str(pid) for row in rows)

    def test_numeric_zero_and_nonzero_exits_are_observed(self) -> None:
        zero = self.run_python("print('ok')")
        self.assertEqual(zero.returncode, 0)
        self.assertGreater(zero.stdout_bytes, 0)
        self.assert_outputs_absent()
        nonzero = self.run_python("raise SystemExit(7)")
        self.assertEqual(nonzero.returncode, 7)
        self.assert_outputs_absent()

    def test_timeout_terminates_the_owned_direct_child(self) -> None:
        marker = self.root / "pid.txt"
        source = "import os,time,sys; open(sys.argv[1],'w').write(str(os.getpid())); time.sleep(30)"
        with self.assertRaisesRegex(MonitoredProcessTimeout, "frozen timeout"):
            self.run_python(source, str(marker), timeout=1.0)
        pid = int(marker.read_text(encoding="utf-8"))
        self.assertFalse(self.process_exists(pid))
        self.assert_outputs_absent()

    def test_sampled_output_threshold_aborts_and_deletes_output(self) -> None:
        source = "import sys,time; sys.stdout.write('x'*8192); sys.stdout.flush(); time.sleep(30)"
        with self.assertRaisesRegex(MonitoredProcessOutputLimit, "sampled output threshold"):
            self.run_python(source, maximum=128)
        self.assert_outputs_absent()

    def test_monitor_runs_while_child_is_live(self) -> None:
        calls: list[int] = []
        result = self.run_python("import time; time.sleep(.08)", monitor=calls.append)
        self.assertGreaterEqual(result.monitor_calls, 1)
        self.assertEqual(result.monitor_calls, len(calls))
        self.assertTrue(all(pid > 0 for pid in calls))

    def test_measurement_failure_aborts_the_child(self) -> None:
        def fail(_pid: int) -> None:
            raise RuntimeError("measurement unavailable")

        with self.assertRaisesRegex(MonitoredProcessCheckFailed, "monitor callback failed"):
            self.run_python("import time; time.sleep(30)", monitor=fail)
        self.assert_outputs_absent()

    def test_literal_argument_is_never_interpreted_by_a_shell(self) -> None:
        marker = self.root / "argument.txt"
        literal = "literal&whoami|still-literal"
        source = "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])"
        result = self.run_python(source, str(marker), literal)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(encoding="utf-8"), literal)

    def test_temporary_output_is_removed_after_success(self) -> None:
        result = self.run_python("import sys; print('out'); print('err',file=sys.stderr)")
        self.assertGreater(result.stdout_bytes, 0)
        self.assertGreater(result.stderr_bytes, 0)
        self.assert_outputs_absent()

    def test_unowned_process_is_never_terminated(self) -> None:
        unowned = subprocess.Popen(
            (PYTHON, "-c", "import time; time.sleep(30)"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        def stop_unowned() -> None:
            if unowned.poll() is None:
                unowned.kill()
            unowned.wait(timeout=5)

        self.addCleanup(stop_unowned)
        with self.assertRaises(MonitoredProcessCheckFailed):
            self.run_python(
                "import time; time.sleep(30)",
                monitor=lambda _pid: (_ for _ in ()).throw(RuntimeError("stop")),
            )
        time.sleep(0.05)
        self.assertIsNone(unowned.poll())


if __name__ == "__main__":
    unittest.main()
