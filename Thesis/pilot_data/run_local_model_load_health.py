"""Execute one separately authorized LM Studio load-health attempt on Windows."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import time
from typing import Any

from cli_transport import CliTransportError, CliTransportTimeout, run_cli
from lm_studio_windows import (
    HostSnapshot,
    OwnedRoot,
    ProcessEntry,
    WindowsHostError,
    assert_engine_identity,
    assert_file_identity,
    capture_owned_root,
    engine_identity,
    file_sha256,
    gpu_used_memory_mib,
    host_snapshot,
    matching_runtime_processes,
    process_tree,
    stop_owned_process,
)
from monitored_process import MonitoredProcessError, run_monitored_process


ROOT = Path(__file__).resolve().parents[2]
PILOT = Path(__file__).resolve().parent
INTEGRATION_DECISION = (
    PILOT / "review_evidence" / "phase6_load_health_transport_integration_decision.json"
)
EXECUTION_AUTHORIZATION = (
    PILOT / "review_evidence" / "phase6_load_health_runner_execution_decision.json"
)
CACHE = ROOT / ".replay_cache" / "local_model_load_health_python"
OUTPUT = CACHE / "result.json"
TEMPORARY_CLI = CACHE / "lms.exe"
LOAD_STDOUT = CACHE / "load.stdout.bin"
LOAD_STDERR = CACHE / "load.stderr.bin"

CLI_BYTES = 120772792
CLI_SHA256 = "976d4389f97b2cf95b38a4eb673855d8a846f2db21a20eb4fe5e79f7179722f5"
WEIGHT_BYTES = 4683073536
WEIGHT_SHA256 = "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c"
ENGINE_FILES = 20
ENGINE_BYTES = 558082098
ENGINE_SHA256 = "389f3fc28e5ec80ec69a3b904ec844f51dadb789162000532c0b0db738c78561"
PREFERENCE_SHA256 = "7448caf18fc92b7e0769924b6cdf1f437279765ff33d2ad7bebccaf22c9857c7"
MODEL_KEY = "qwen2.5-coder-7b-instruct"
IDENTIFIER = "cyxsheath-qwen25-coder-7b-q4km"
LOAD_ARGS = (
    "load",
    MODEL_KEY,
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
    IDENTIFIER,
    "--yes",
)
CONTROL_OUTPUT_BYTES = 1048576
LOAD_OUTPUT_BYTES = 1048576
MINIMUM_PRELOAD_AVAILABLE = 21474836480
MINIMUM_OBSERVED_AVAILABLE = 17179869184
MAXIMUM_MEMORY = 12884901888
MAXIMUM_GPU_DELTA_MIB = 512
class ActivationError(WindowsHostError):
    """Raised when the frozen activation contract cannot be satisfied."""


@dataclass(slots=True)
class ResourceStats:
    preload_available_memory_bytes: int
    preload_gpu_used_memory_mib: int
    minimum_available_memory_bytes: int
    maximum_available_memory_drop_bytes: int = 0
    peak_activation_tree_private_bytes: int = 0
    peak_activation_tree_working_set_bytes: int = 0
    maximum_gpu_used_memory_delta_mib: int = 0
    load_samples: int = 0
    post_load_samples: int = 0
    http_listener_observed: bool = False


@dataclass(slots=True)
class AttemptState:
    failures: list[str] = field(default_factory=list)
    root: OwnedRoot | None = None
    owned_identities: set[tuple[int, str]] = field(default_factory=set)
    temporary_copy_staged: bool = False
    daemon_up_exit_code: int | None = None
    load_exit_code: int | None = None
    unload_exit_code: int | None = None
    daemon_down_exit_code: int | None = None
    inventory_after_load: list[dict[str, Any]] = field(default_factory=list)
    inventory_after_unload: list[dict[str, Any]] = field(default_factory=list)
    loaded_identity_passed: bool = False
    forced_cleanup_required: bool = False
    temporary_copy_deleted: bool = False
    raw_output_deleted: bool = False
    canonical_cli_matches_after: bool = False
    engine_matches_after: bool = False
    preference_matches_after: bool = False
    weight_matches_after: bool = False
    activation_processes_absent: bool = False
    port_absent_after: bool = False
    partial_weight_absent_after: bool = False

    def fail(self, label: str) -> None:
        if label not in self.failures:
            self.failures.append(label)


def _authorization_settings() -> dict[str, Any]:
    return {
        "model_key": MODEL_KEY,
        "identifier": IDENTIFIER,
        "context_length_tokens": 8192,
        "gpu_offload": "off",
        "parallel_predictions": 1,
        "idle_ttl_seconds": 600,
        "load_timeout_seconds": 600,
        "sample_interval_seconds": 1,
        "post_load_observation_samples": 15,
        "inference_request_count": 0,
        "http_server_start_count": 0,
        "cyxcode_invocation_count": 0,
        "docker_container_count": 0,
    }


def validate_execution_authorization(path: Path = EXECUTION_AUTHORIZATION) -> dict[str, Any]:
    if not path.is_file():
        raise ActivationError("load_health_runtime_not_authorized")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ActivationError("execution_authorization_unreadable") from error
    expected = {
        "schema_version": "1.0.0",
        "status": "python_load_health_runner_execution_authorized_once",
        "decision_scope": "one_exact_load_health_execution_without_inference_or_http_server",
        "integration_decision_sha256": file_sha256(INTEGRATION_DECISION),
        "runner_sha256": file_sha256(Path(__file__)),
        "monitored_process_sha256": file_sha256(PILOT / "monitored_process.py"),
        "windows_adapter_sha256": file_sha256(PILOT / "lm_studio_windows.py"),
        "maximum_attempts": 1,
        "settings": _authorization_settings(),
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ActivationError(f"execution_authorization_{key}_mismatch")
    return record


def assert_temporary_cli() -> None:
    assert_file_identity(TEMPORARY_CLI, CLI_BYTES, CLI_SHA256, "temporary_cli")


def run_control(*arguments: str, timeout_seconds: int, require_zero: bool = True):
    assert_temporary_cli()
    result = run_cli(
        (str(TEMPORARY_CLI.resolve()), *arguments),
        cwd=ROOT,
        timeout_seconds=timeout_seconds,
        max_output_bytes=CONTROL_OUTPUT_BYTES,
    )
    if require_zero and result.returncode != 0:
        raise ActivationError(f"control_{arguments[0]}_exit_nonzero")
    return result


def parse_inventory(payload: bytes) -> list[dict[str, Any]]:
    try:
        raw = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ActivationError("model_inventory_json_invalid") from error
    if raw is None:
        return []
    if not isinstance(raw, list):
        raw = [raw]
    inventory: list[dict[str, Any]] = []
    try:
        for item in raw:
            inventory.append(
                {
                    "identifier": str(item["identifier"]),
                    "modelKey": str(item["modelKey"]),
                    "contextLength": int(item["contextLength"]),
                }
            )
    except (KeyError, TypeError, ValueError) as error:
        raise ActivationError("model_inventory_shape_invalid") from error
    return inventory


def read_inventory() -> list[dict[str, Any]]:
    result = run_control("ps", "--json", timeout_seconds=120)
    return parse_inventory(result.stdout)


def record_resource_sample(
    stats: ResourceStats,
    state: AttemptState,
    *,
    phase: str,
    load_pid: int | None,
) -> None:
    if state.root is None:
        raise ActivationError("owned_root_not_captured")
    snapshot = host_snapshot(cwd=ROOT)
    tree = list(process_tree(snapshot, state.root))
    by_pid = {item.pid: item for item in snapshot.processes}
    if load_pid is not None and load_pid in by_pid and all(item.pid != load_pid for item in tree):
        tree.append(by_pid[load_pid])
    state.owned_identities.update((item.pid, item.created) for item in tree)
    private_bytes = sum(item.private_bytes for item in tree)
    working_set_bytes = sum(item.working_set_bytes for item in tree)
    available = snapshot.available_memory_bytes
    gpu = gpu_used_memory_mib(cwd=ROOT)
    memory_drop = max(0, stats.preload_available_memory_bytes - available)
    gpu_delta = max(0, gpu - stats.preload_gpu_used_memory_mib)
    stats.minimum_available_memory_bytes = min(stats.minimum_available_memory_bytes, available)
    stats.maximum_available_memory_drop_bytes = max(
        stats.maximum_available_memory_drop_bytes, memory_drop
    )
    stats.peak_activation_tree_private_bytes = max(
        stats.peak_activation_tree_private_bytes, private_bytes
    )
    stats.peak_activation_tree_working_set_bytes = max(
        stats.peak_activation_tree_working_set_bytes, working_set_bytes
    )
    stats.maximum_gpu_used_memory_delta_mib = max(
        stats.maximum_gpu_used_memory_delta_mib, gpu_delta
    )
    if phase == "load":
        stats.load_samples += 1
    elif phase == "post_load":
        stats.post_load_samples += 1
    else:
        raise ActivationError("resource_sample_phase_invalid")
    stats.http_listener_observed = stats.http_listener_observed or snapshot.port_1234_listening
    if snapshot.port_1234_listening:
        raise ActivationError("http_listener_observed")
    if available < MINIMUM_OBSERVED_AVAILABLE:
        raise ActivationError("available_memory_floor_failed")
    if memory_drop > MAXIMUM_MEMORY:
        raise ActivationError("available_memory_drop_ceiling_failed")
    if private_bytes > MAXIMUM_MEMORY:
        raise ActivationError("private_memory_ceiling_failed")
    if working_set_bytes > MAXIMUM_MEMORY:
        raise ActivationError("working_set_ceiling_failed")
    if gpu_delta > MAXIMUM_GPU_DELTA_MIB:
        raise ActivationError("gpu_memory_delta_ceiling_failed")


def _root_alive(root: OwnedRoot, snapshot: HostSnapshot) -> bool:
    return any(item.pid == root.pid and item.created == root.created for item in snapshot.processes)


def force_owned_processes(state: AttemptState) -> None:
    if state.root is None:
        return
    snapshot = host_snapshot(cwd=ROOT)
    try:
        tree = process_tree(snapshot, state.root)
        state.owned_identities.update((item.pid, item.created) for item in tree)
    except WindowsHostError:
        pass
    current = {(item.pid, item.created): item for item in snapshot.processes}
    owned = [current[key] for key in state.owned_identities if key in current]
    owned.sort(key=lambda item: item.pid == state.root.pid)
    for item in owned:
        try:
            returncode = stop_owned_process(item, cwd=ROOT)
            if returncode not in (0, 7):
                state.fail("forced_cleanup_command_failed")
            if returncode == 7:
                state.fail("forced_cleanup_pid_reuse_detected")
        except (WindowsHostError, CliTransportError, CliTransportTimeout):
            state.fail("forced_cleanup_command_failed")


def write_result(record: dict[str, Any]) -> None:
    OUTPUT.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run_attempt(authorization: dict[str, Any]) -> int:
    authorization_sha256 = file_sha256(EXECUTION_AUTHORIZATION)
    home = Path(os.environ["USERPROFILE"])
    canonical_cli = home / ".lmstudio" / "bin" / "lms.exe"
    model_path = ROOT / ".local_models" / "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
    preference_path = home / ".lmstudio" / ".internal" / "backend-preferences-v1.json"
    engine_root = (
        home
        / ".lmstudio"
        / "extensions"
        / "backends"
        / "llama.cpp-win-x86_64-nvidia-cuda-avx2-2.29.1"
    )
    state = AttemptState()
    stats: ResourceStats | None = None
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        if OUTPUT.exists():
            raise ActivationError("prior_load_health_result_present")
        if TEMPORARY_CLI.exists() or LOAD_STDOUT.exists() or LOAD_STDERR.exists():
            raise ActivationError("temporary_activation_artifact_present_at_baseline")
        baseline = host_snapshot(cwd=ROOT)
        if matching_runtime_processes(baseline):
            raise ActivationError("unclean_process_baseline")
        if baseline.port_1234_listening:
            raise ActivationError("port_1234_present_at_baseline")
        assert_file_identity(canonical_cli, CLI_BYTES, CLI_SHA256, "canonical_cli")
        assert_file_identity(model_path, WEIGHT_BYTES, WEIGHT_SHA256, "weight")
        if file_sha256(preference_path) != PREFERENCE_SHA256:
            raise ActivationError("engine_preference_digest_mismatch")
        assert_engine_identity(
            engine_root,
            expected_files=ENGINE_FILES,
            expected_bytes=ENGINE_BYTES,
            expected_sha256=ENGINE_SHA256,
        )
        preload_gpu = gpu_used_memory_mib(cwd=ROOT)
        if baseline.available_memory_bytes < MINIMUM_PRELOAD_AVAILABLE:
            raise ActivationError("preload_available_memory_floor_failed")
        stats = ResourceStats(
            preload_available_memory_bytes=baseline.available_memory_bytes,
            preload_gpu_used_memory_mib=preload_gpu,
            minimum_available_memory_bytes=baseline.available_memory_bytes,
        )

        shutil.copyfile(canonical_cli, TEMPORARY_CLI)
        state.temporary_copy_staged = True
        assert_temporary_cli()

        daemon_result = None
        try:
            daemon_result = run_control(
                "daemon", "up", "--json", timeout_seconds=180, require_zero=False
            )
            state.daemon_up_exit_code = daemon_result.returncode
        finally:
            snapshot = host_snapshot(cwd=ROOT)
            state.root = capture_owned_root(snapshot)
            state.owned_identities.update(
                (item.pid, item.created) for item in process_tree(snapshot, state.root)
            )
        if daemon_result is None or daemon_result.returncode != 0:
            raise ActivationError("daemon_up_exit_nonzero")
        if read_inventory():
            raise ActivationError("loaded_inventory_not_empty_before_load")
        if host_snapshot(cwd=ROOT).port_1234_listening:
            raise ActivationError("http_listener_started_with_daemon")

        assert_temporary_cli()
        load_result = run_monitored_process(
            (str(TEMPORARY_CLI.resolve()), *LOAD_ARGS),
            cwd=ROOT,
            timeout_seconds=600,
            sample_interval_seconds=1,
            max_output_file_bytes=LOAD_OUTPUT_BYTES,
            stdout_path=LOAD_STDOUT.resolve(),
            stderr_path=LOAD_STDERR.resolve(),
            monitor=lambda pid: record_resource_sample(
                stats, state, phase="load", load_pid=pid
            ),
        )
        state.load_exit_code = load_result.returncode
        if load_result.returncode != 0:
            raise ActivationError("load_exit_nonzero")
        state.inventory_after_load = read_inventory()
        state.loaded_identity_passed = state.inventory_after_load == [
            {
                "identifier": IDENTIFIER,
                "modelKey": MODEL_KEY,
                "contextLength": 8192,
            }
        ]
        if not state.loaded_identity_passed:
            raise ActivationError("loaded_identity_mismatch")
        for sample_index in range(15):
            record_resource_sample(stats, state, phase="post_load", load_pid=None)
            if sample_index < 14:
                time.sleep(1)
    except MonitoredProcessError as error:
        cause = error.__cause__
        state.fail(str(cause) if isinstance(cause, WindowsHostError) else type(error).__name__)
    except (WindowsHostError, CliTransportError, CliTransportTimeout) as error:
        state.fail(str(error) if isinstance(error, WindowsHostError) else type(error).__name__)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        state.fail("unexpected_activation_exception")
    finally:
        try:
            if state.root is None:
                try:
                    state.root = capture_owned_root(host_snapshot(cwd=ROOT))
                except WindowsHostError:
                    state.root = None
            if state.root is not None and _root_alive(state.root, host_snapshot(cwd=ROOT)):
                if TEMPORARY_CLI.is_file():
                    try:
                        unload = run_control(
                            "unload", IDENTIFIER, timeout_seconds=120, require_zero=False
                        )
                        state.unload_exit_code = unload.returncode
                        if unload.returncode != 0:
                            state.fail("unload_exit_nonzero")
                    except (WindowsHostError, CliTransportError, CliTransportTimeout):
                        state.fail("unload_command_failed")
                    try:
                        state.inventory_after_unload = read_inventory()
                        if state.inventory_after_unload:
                            state.fail("loaded_inventory_not_empty_after_unload")
                    except (WindowsHostError, CliTransportError, CliTransportTimeout):
                        state.fail("post_unload_inventory_failed")
                    try:
                        down = run_control(
                            "daemon", "down", timeout_seconds=120, require_zero=False
                        )
                        state.daemon_down_exit_code = down.returncode
                        if down.returncode != 0:
                            state.fail("daemon_down_exit_nonzero")
                    except (WindowsHostError, CliTransportError, CliTransportTimeout):
                        state.fail("daemon_down_command_failed")
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and _root_alive(
                    state.root, host_snapshot(cwd=ROOT)
                ):
                    time.sleep(0.25)
                if _root_alive(state.root, host_snapshot(cwd=ROOT)):
                    state.forced_cleanup_required = True
                    force_owned_processes(state)
                    time.sleep(2)
        except (WindowsHostError, CliTransportError, CliTransportTimeout, OSError):
            state.fail("cleanup_exception")

        try:
            final_snapshot = host_snapshot(cwd=ROOT)
            state.activation_processes_absent = not matching_runtime_processes(final_snapshot)
            state.port_absent_after = not final_snapshot.port_1234_listening
        except (WindowsHostError, CliTransportError, CliTransportTimeout):
            state.fail("final_host_snapshot_failed")
        state.partial_weight_absent_after = not Path(str(model_path) + ".part").exists()
        try:
            assert_file_identity(canonical_cli, CLI_BYTES, CLI_SHA256, "canonical_cli_after")
            state.canonical_cli_matches_after = True
        except (WindowsHostError, OSError):
            state.fail("canonical_cli_identity_changed_after")
        try:
            assert_engine_identity(
                engine_root,
                expected_files=ENGINE_FILES,
                expected_bytes=ENGINE_BYTES,
                expected_sha256=ENGINE_SHA256,
            )
            state.engine_matches_after = True
        except (WindowsHostError, OSError):
            state.fail("engine_identity_changed_after")
        try:
            state.preference_matches_after = file_sha256(preference_path) == PREFERENCE_SHA256
            if not state.preference_matches_after:
                state.fail("engine_preference_changed_after")
        except OSError:
            state.fail("engine_preference_changed_after")
        try:
            assert_file_identity(model_path, WEIGHT_BYTES, WEIGHT_SHA256, "weight_after")
            state.weight_matches_after = True
        except (WindowsHostError, OSError):
            state.fail("weight_identity_changed_after")

        LOAD_STDOUT.unlink(missing_ok=True)
        LOAD_STDERR.unlink(missing_ok=True)
        state.raw_output_deleted = not LOAD_STDOUT.exists() and not LOAD_STDERR.exists()
        TEMPORARY_CLI.unlink(missing_ok=True)
        state.temporary_copy_deleted = not TEMPORARY_CLI.exists()
        if not state.raw_output_deleted:
            state.fail("raw_output_retained")
        if not state.temporary_copy_deleted:
            state.fail("temporary_cli_retained")
        if not state.activation_processes_absent:
            state.fail("activation_process_retained")
        if not state.port_absent_after:
            state.fail("port_1234_retained")
        if not state.partial_weight_absent_after:
            state.fail("partial_weight_retained")
        if state.forced_cleanup_required:
            state.fail("forced_cleanup_required")

        accepted = (
            not state.failures
            and stats is not None
            and state.temporary_copy_staged
            and state.daemon_up_exit_code == 0
            and state.load_exit_code == 0
            and state.loaded_identity_passed
            and stats.post_load_samples == 15
            and state.unload_exit_code == 0
            and not state.inventory_after_unload
            and state.daemon_down_exit_code == 0
            and state.activation_processes_absent
            and state.port_absent_after
            and state.partial_weight_absent_after
            and state.raw_output_deleted
            and state.temporary_copy_deleted
            and state.canonical_cli_matches_after
            and state.engine_matches_after
            and state.preference_matches_after
            and state.weight_matches_after
        )
        resource_record = None
        if stats is not None:
            resource_record = {
                "preload_available_memory_bytes": stats.preload_available_memory_bytes,
                "minimum_available_memory_bytes": stats.minimum_available_memory_bytes,
                "maximum_available_memory_drop_bytes": stats.maximum_available_memory_drop_bytes,
                "peak_activation_tree_private_bytes": stats.peak_activation_tree_private_bytes,
                "peak_activation_tree_working_set_bytes": stats.peak_activation_tree_working_set_bytes,
                "preload_gpu_used_memory_mib": stats.preload_gpu_used_memory_mib,
                "maximum_gpu_used_memory_delta_mib": stats.maximum_gpu_used_memory_delta_mib,
                "load_samples": stats.load_samples,
                "post_load_samples": stats.post_load_samples,
                "http_listener_observed": stats.http_listener_observed,
            }
        record = {
            "schema_version": "1.0.0-local",
            "status": "load_health_passed" if accepted else "load_health_failed",
            "started_at": started_at,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "authorization_record": EXECUTION_AUTHORIZATION.name,
            "authorization_sha256": authorization_sha256,
            "authorization_status": authorization["status"],
            "runner_sha256": file_sha256(Path(__file__)),
            "monitored_process_sha256": file_sha256(PILOT / "monitored_process.py"),
            "windows_adapter_sha256": file_sha256(PILOT / "lm_studio_windows.py"),
            "engine": {
                "package": "llama.cpp-win-x86_64-nvidia-cuda-avx2-2.29.1",
                "inventory_sha256": ENGINE_SHA256,
                "preference_sha256": PREFERENCE_SHA256,
                "identity_matches_after": state.engine_matches_after,
                "preference_matches_after": state.preference_matches_after,
            },
            "cli": {
                "version": "1.3.3",
                "sha256": CLI_SHA256,
                "temporary_copy_staged": state.temporary_copy_staged,
                "daemon_up_exit_code": state.daemon_up_exit_code,
                "load_exit_code": state.load_exit_code,
                "unload_exit_code": state.unload_exit_code,
                "daemon_down_exit_code": state.daemon_down_exit_code,
                "canonical_identity_matches_after": state.canonical_cli_matches_after,
                "temporary_copy_deleted": state.temporary_copy_deleted,
            },
            "model": {
                "model_key": MODEL_KEY,
                "identifier": IDENTIFIER,
                "weight_sha256": WEIGHT_SHA256,
                "weight_identity_matches_after": state.weight_matches_after,
                "context_length_tokens": 8192,
                "gpu_offload": "off",
            },
            "observation": {
                "loaded_inventory": state.inventory_after_load,
                "loaded_identity_passed": state.loaded_identity_passed,
                "inference_request_count": 0,
                "http_server_start_count": 0,
                "cyxcode_invocation_count": 0,
                "docker_container_count": 0,
            },
            "resources": resource_record,
            "cleanup": {
                "loaded_inventory_after_unload": state.inventory_after_unload,
                "forced_cleanup_required": state.forced_cleanup_required,
                "activation_processes_absent": state.activation_processes_absent,
                "port_1234_listener_absent": state.port_absent_after,
                "partial_weight_absent": state.partial_weight_absent_after,
                "raw_cli_output_deleted": state.raw_output_deleted,
            },
            "failures": state.failures,
            "accepted": accepted,
        }
        write_result(record)
    return 0 if accepted else 1


def main() -> int:
    try:
        authorization = validate_execution_authorization()
    except ActivationError as error:
        print(f"BLOCKED: {error}")
        return 2
    return run_attempt(authorization)


if __name__ == "__main__":
    raise SystemExit(main())
