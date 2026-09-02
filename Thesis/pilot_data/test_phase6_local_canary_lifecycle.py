from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from phase6_local_canary_lifecycle import CanaryLifecycleError, GenerationObservation, execute_canary


class FakeRuntime:
    def __init__(self, fail: set[str] | None = None, verified: bool = True) -> None:
        self.fail = set() if fail is None else fail
        self.verified = verified
        self.calls: list[str] = []

    def _call(self, name: str) -> None:
        self.calls.append(name)
        if name in self.fail:
            raise CanaryLifecycleError(f"fixture.{name}_failed")

    def preflight(self): self._call("preflight")
    def start_daemon(self): self._call("start_daemon")
    def load_model(self): self._call("load_model")
    def start_server(self): self._call("start_server")
    def start_proxy(self): self._call("start_proxy")

    def run_generation(self):
        self._call("run_generation")
        return GenerationObservation(
            self.verified,
            "accept" if self.verified else "revise",
            1,
            2.5,
            "sha256:" + "a" * 64,
        )

    def stop_proxy(self): self._call("stop_proxy")
    def stop_server(self): self._call("stop_server")
    def unload_model(self): self._call("unload_model")
    def stop_daemon(self): self._call("stop_daemon")
    def final_check(self): self._call("final_check")


class LocalCanaryLifecycleTests(unittest.TestCase):
    def test_passing_attempt_cleans_in_reverse_order(self) -> None:
        runtime = FakeRuntime()
        result = execute_canary(runtime)
        self.assertEqual("passed", result.status)
        self.assertTrue(result.cleanup_passed)
        self.assertEqual(
            [
                "preflight", "start_daemon", "load_model", "start_server", "start_proxy",
                "run_generation", "stop_proxy", "stop_server", "unload_model", "stop_daemon",
                "final_check",
            ],
            runtime.calls,
        )

    def test_verified_task_failure_is_not_infrastructure_failure(self) -> None:
        result = execute_canary(FakeRuntime(verified=False))
        self.assertEqual("task_failed", result.status)
        self.assertEqual((), result.failures)
        self.assertTrue(result.cleanup_passed)

    def test_load_failure_cleans_only_acquired_daemon(self) -> None:
        runtime = FakeRuntime({"load_model"})
        result = execute_canary(runtime)
        self.assertEqual("infrastructure_failed", result.status)
        self.assertEqual(("fixture.load_model_failed",), result.failures)
        self.assertEqual(
            ["preflight", "start_daemon", "load_model", "stop_daemon", "final_check"],
            runtime.calls,
        )

    def test_proxy_start_failure_cleans_server_model_and_daemon(self) -> None:
        runtime = FakeRuntime({"start_proxy"})
        execute_canary(runtime)
        self.assertEqual(
            [
                "preflight", "start_daemon", "load_model", "start_server", "start_proxy",
                "stop_server", "unload_model", "stop_daemon", "final_check",
            ],
            runtime.calls,
        )

    def test_cleanup_failures_do_not_skip_later_cleanup_or_final_check(self) -> None:
        runtime = FakeRuntime({"stop_proxy", "unload_model"})
        result = execute_canary(runtime)
        self.assertEqual("infrastructure_failed", result.status)
        self.assertEqual(("cleanup.proxy_failed", "cleanup.model_failed"), result.failures)
        self.assertFalse(result.cleanup_passed)
        self.assertIn("stop_daemon", runtime.calls)
        self.assertEqual("final_check", runtime.calls[-1])

    def test_unexpected_exception_is_fail_closed(self) -> None:
        runtime = FakeRuntime()
        runtime.start_daemon = lambda: (_ for _ in ()).throw(RuntimeError("raw detail"))
        result = execute_canary(runtime)
        self.assertEqual(("unexpected_runtime_error",), result.failures)
        self.assertNotIn("raw detail", repr(result))


if __name__ == "__main__":
    unittest.main()
