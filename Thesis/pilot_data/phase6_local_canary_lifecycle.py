"""One-attempt lifecycle contract for the Phase-6 local generator canary."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Protocol


class CanaryLifecycleError(RuntimeError):
    """A bounded infrastructure step failed with a public reason code."""

    def __init__(self, code: str) -> None:
        if not isinstance(code, str) or not code or any(character.isspace() for character in code):
            raise ValueError("lifecycle error code invalid")
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class GenerationObservation:
    verified_success: bool
    verdict: str
    attempts: int
    wall_seconds: float
    record_digest: str

    def __post_init__(self) -> None:
        if type(self.verified_success) is not bool:
            raise ValueError("verified success invalid")
        if self.verdict not in ("accept", "revise", "failed"):
            raise ValueError("verdict invalid")
        if self.attempts != 1:
            raise ValueError("attempt count invalid")
        if not isinstance(self.wall_seconds, (int, float)) or not math.isfinite(self.wall_seconds) or self.wall_seconds < 0:
            raise ValueError("wall time invalid")
        if re.fullmatch(r"sha256:[0-9a-f]{64}", self.record_digest) is None:
            raise ValueError("record digest invalid")


@dataclass(frozen=True, slots=True)
class LifecycleResult:
    status: str
    observation: GenerationObservation | None
    failures: tuple[str, ...]
    cleanup_passed: bool
    events: tuple[str, ...]


class CanaryRuntime(Protocol):
    def preflight(self) -> None: ...
    def start_daemon(self) -> None: ...
    def load_model(self) -> None: ...
    def start_server(self) -> None: ...
    def start_proxy(self) -> None: ...
    def run_generation(self) -> GenerationObservation: ...
    def stop_proxy(self) -> None: ...
    def stop_server(self) -> None: ...
    def unload_model(self) -> None: ...
    def stop_daemon(self) -> None: ...
    def final_check(self) -> None: ...


def execute_canary(runtime: CanaryRuntime) -> LifecycleResult:
    """Execute once and always attempt cleanup for each acquired resource."""

    failures: list[str] = []
    events: list[str] = []
    observation: GenerationObservation | None = None
    daemon_started = False
    model_loaded = False
    server_started = False
    proxy_started = False

    def run_step(name: str, function) -> None:
        nonlocal daemon_started, model_loaded, server_started, proxy_started
        function()
        events.append(name)
        if name == "daemon_started":
            daemon_started = True
        elif name == "model_loaded":
            model_loaded = True
        elif name == "server_started":
            server_started = True
        elif name == "proxy_started":
            proxy_started = True

    try:
        run_step("preflight_passed", runtime.preflight)
        run_step("daemon_started", runtime.start_daemon)
        run_step("model_loaded", runtime.load_model)
        run_step("server_started", runtime.start_server)
        run_step("proxy_started", runtime.start_proxy)
        observation = runtime.run_generation()
        if not isinstance(observation, GenerationObservation):
            raise CanaryLifecycleError("generation_observation_invalid")
        events.append("generation_completed")
    except CanaryLifecycleError as error:
        failures.append(error.code)
    except Exception:
        failures.append("unexpected_runtime_error")
    finally:
        cleanup = (
            (proxy_started, "proxy_stopped", "cleanup.proxy_failed", runtime.stop_proxy),
            (server_started, "server_stopped", "cleanup.server_failed", runtime.stop_server),
            (model_loaded, "model_unloaded", "cleanup.model_failed", runtime.unload_model),
            (daemon_started, "daemon_stopped", "cleanup.daemon_failed", runtime.stop_daemon),
        )
        for acquired, event, code, function in cleanup:
            if not acquired:
                continue
            try:
                function()
                events.append(event)
            except Exception:
                failures.append(code)
        try:
            runtime.final_check()
            events.append("final_check_passed")
        except Exception:
            failures.append("cleanup.final_check_failed")

    cleanup_passed = not any(code.startswith("cleanup.") for code in failures)
    if failures:
        status = "infrastructure_failed"
    elif observation is not None and observation.verified_success and observation.verdict == "accept":
        status = "passed"
    else:
        status = "task_failed"
    return LifecycleResult(status, observation, tuple(failures), cleanup_passed, tuple(events))
