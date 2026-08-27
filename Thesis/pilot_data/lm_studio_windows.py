"""Windows host observations and identity checks for LM Studio activation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
from typing import Any

from cli_transport import CliTransportError, CliTransportTimeout, run_cli


PROCESS_NAMES = {"lm studio.exe", "llmster.exe", "lms.exe"}
SERVICE_ROOT_NAMES = {"lm studio.exe", "llmster.exe"}


class WindowsHostError(RuntimeError):
    """Raised when a required Windows host observation is unavailable."""


@dataclass(frozen=True, slots=True)
class ProcessEntry:
    pid: int
    parent_pid: int
    created: str
    name: str
    command: str
    private_bytes: int
    working_set_bytes: int


@dataclass(frozen=True, slots=True)
class HostSnapshot:
    available_memory_bytes: int
    port_1234_listening: bool
    processes: tuple[ProcessEntry, ...]


@dataclass(frozen=True, slots=True)
class OwnedRoot:
    pid: int
    created: str


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_file_identity(path: Path, size: int, digest: str, label: str) -> None:
    if not path.is_file():
        raise WindowsHostError(f"{label}_missing")
    if path.stat().st_size != size:
        raise WindowsHostError(f"{label}_size_mismatch")
    if file_sha256(path) != digest:
        raise WindowsHostError(f"{label}_digest_mismatch")


def engine_identity(engine_root: Path) -> tuple[int, int, str]:
    entries: list[dict[str, Any]] = []
    for path in (item for item in engine_root.rglob("*") if item.is_file()):
        entries.append(
            {
                "path": path.relative_to(engine_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
    entries.sort(key=lambda item: item["path"].encode("utf-8"))
    encoded = json.dumps(entries, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return len(entries), sum(item["bytes"] for item in entries), hashlib.sha256(encoded).hexdigest()


def assert_engine_identity(
    engine_root: Path,
    *,
    expected_files: int,
    expected_bytes: int,
    expected_sha256: str,
) -> None:
    if engine_identity(engine_root) != (expected_files, expected_bytes, expected_sha256):
        raise WindowsHostError("engine_identity_mismatch")


def powershell_path() -> Path:
    system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    path = system_root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if not path.is_file():
        raise WindowsHostError("powershell_missing")
    return path.resolve()


def powershell_json(script: str, *, cwd: Path, timeout_seconds: int = 30) -> Any:
    encoded_script = (
        "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false);" + script
    )
    result = run_cli(
        (
            str(powershell_path()),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            encoded_script,
        ),
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        max_output_bytes=1048576,
    )
    if result.returncode != 0:
        raise WindowsHostError("powershell_inventory_command_failed")
    try:
        return json.loads(result.stdout.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WindowsHostError("powershell_inventory_json_invalid") from error


def host_snapshot(*, cwd: Path) -> HostSnapshot:
    script = r"""
$ErrorActionPreference='Stop'
$os=Get-CimInstance Win32_OperatingSystem
$processes=@(Get-CimInstance Win32_Process | ForEach-Object {
  $command=''
  if([string]$_.Name -eq 'LM Studio.exe'){$command=[string]$_.CommandLine}
  [ordered]@{
    pid=[int]$_.ProcessId
    parent_pid=[int]$_.ParentProcessId
    created=([datetime]$_.CreationDate).ToUniversalTime().ToString('o')
    name=[string]$_.Name
    command=$command
    private_bytes=[int64]$_.PrivatePageCount
    working_set_bytes=[int64]$_.WorkingSetSize
  }
})
$listeners=@([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners())
$listener=@($listeners | Where-Object {$_.Port -eq 1234}).Count -gt 0
[ordered]@{
  available_memory_bytes=[int64]$os.FreePhysicalMemory*1024
  port_1234_listening=[bool]$listener
  processes=$processes
} | ConvertTo-Json -Depth 4 -Compress
"""
    raw = powershell_json(script, cwd=cwd)
    try:
        processes = tuple(
            ProcessEntry(
                pid=int(item["pid"]),
                parent_pid=int(item["parent_pid"]),
                created=str(item["created"]),
                name=str(item["name"]),
                command=str(item["command"]),
                private_bytes=int(item["private_bytes"]),
                working_set_bytes=int(item["working_set_bytes"]),
            )
            for item in raw["processes"]
        )
        return HostSnapshot(
            available_memory_bytes=int(raw["available_memory_bytes"]),
            port_1234_listening=bool(raw["port_1234_listening"]),
            processes=processes,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise WindowsHostError("host_snapshot_shape_invalid") from error


def matching_runtime_processes(snapshot: HostSnapshot) -> tuple[ProcessEntry, ...]:
    return tuple(item for item in snapshot.processes if item.name.lower() in PROCESS_NAMES)


def capture_owned_root(snapshot: HostSnapshot, *, expected_pid: int | None = None) -> OwnedRoot:
    if expected_pid is not None:
        roots = [
            item
            for item in snapshot.processes
            if item.pid == expected_pid and item.name.lower() in SERVICE_ROOT_NAMES
        ]
    else:
        roots = [
            item
            for item in snapshot.processes
            if item.name.lower() == "llmster.exe"
            or (
                item.name.lower() == "lm studio.exe"
                and "--run-as-service" in item.command
            )
        ]
    if len(roots) != 1:
        raise WindowsHostError(f"activation_root_count_{len(roots)}")
    return OwnedRoot(roots[0].pid, roots[0].created)


def process_tree(snapshot: HostSnapshot, root: OwnedRoot) -> tuple[ProcessEntry, ...]:
    by_pid = {item.pid: item for item in snapshot.processes}
    entry = by_pid.get(root.pid)
    if entry is None or entry.created != root.created:
        raise WindowsHostError("owned_root_identity_missing")
    found = {root.pid}
    changed = True
    while changed:
        changed = False
        for item in snapshot.processes:
            if item.parent_pid in found and item.pid not in found:
                found.add(item.pid)
                changed = True
    return tuple(item for item in snapshot.processes if item.pid in found)


def gpu_used_memory_mib(*, cwd: Path) -> int:
    executable = shutil.which("nvidia-smi.exe")
    if executable is None:
        raise WindowsHostError("nvidia_smi_missing")
    for attempt in range(3):
        try:
            result = run_cli(
                (
                    str(Path(executable).resolve()),
                    "--query-gpu=memory.used",
                    "--format=csv,noheader,nounits",
                ),
                cwd=cwd,
                timeout_seconds=15,
                max_output_bytes=4096,
            )
            value = int(result.stdout.decode("ascii").splitlines()[0].strip())
            if result.returncode == 0 and value >= 0:
                return value
        except (CliTransportError, CliTransportTimeout, UnicodeDecodeError, ValueError, IndexError):
            pass
        if attempt < 2:
            time.sleep(1)
    raise WindowsHostError("gpu_measurement_failed_after_three_attempts")


def stop_owned_process(entry: ProcessEntry, *, cwd: Path) -> int:
    safe_creation = entry.created.replace("'", "''")
    script = (
        "$ErrorActionPreference='Stop';"
        f"$p=Get-CimInstance Win32_Process -Filter \"ProcessId = {entry.pid}\";"
        "if($null -eq $p){exit 0};"
        "$created=([datetime]$p.CreationDate).ToUniversalTime().ToString('o');"
        f"if($created -ne '{safe_creation}'){{exit 7}};"
        f"Stop-Process -Id {entry.pid} -Force -ErrorAction Stop"
    )
    result = run_cli(
        (
            str(powershell_path()),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ),
        cwd=cwd,
        timeout_seconds=15,
        max_output_bytes=4096,
    )
    return result.returncode
