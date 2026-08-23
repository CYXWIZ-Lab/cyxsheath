"""Digest-pinned Docker implementation of the isolated sandbox protocol."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path, PurePosixPath
import subprocess
from threading import Event, Lock, Thread
import time
from typing import Callable, Protocol
import uuid

from .artifacts import digest_bytes
from .runner import RunnerError, SandboxProfile, SandboxRequest, SandboxResult
from .snapshots import WorkspaceBinding
from .tools import identify_container_executable, identify_executable


class DockerBackendError(RunnerError):
    """Raised when Docker configuration or transport violates the contract."""


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _positive_integer(value: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DockerBackendError(f"{field} must be a positive integer")


def _image_digest(reference: str) -> str:
    if not isinstance(reference, str) or not reference.strip() or "\x00" in reference or any(
        character.isspace() for character in reference
    ):
        raise DockerBackendError("image must be a non-empty reference without spaces")
    repository, separator, digest = reference.rpartition("@")
    if not separator or not repository:
        raise DockerBackendError("image must be pinned by digest")
    value = digest.removeprefix("sha256:")
    if not digest.startswith("sha256:") or len(value) != 64:
        raise DockerBackendError("image must use a sha256 digest")
    try:
        int(value, 16)
    except ValueError as error:
        raise DockerBackendError("image must use a sha256 digest") from error
    return digest


def _implementation_digest() -> str:
    module_root = Path(__file__).resolve().parent
    sources = (
        module_root / "docker_backend.py",
        module_root / "runner.py",
        module_root / "tools.py",
        module_root / "snapshots.py",
        module_root / "artifacts.py",
    )
    digests = [digest_bytes(path.read_bytes()) for path in sources]
    return digest_bytes(json.dumps(digests, separators=(",", ":")).encode("utf-8"))


def _runtime_source_digest(root: Path) -> str:
    resolved = Path(root).resolve()
    if not resolved.is_dir():
        raise DockerBackendError("runtime source root must be a directory")
    files = sorted(
        path
        for path in resolved.rglob("*")
        if path.suffix == ".py" or path.name == "py.typed"
    )
    if not files:
        raise DockerBackendError("runtime source root contains no Python sources")
    records = []
    for path in files:
        if path.is_symlink() or not path.is_file():
            raise DockerBackendError("runtime source entries must be regular files")
        records.append(
            {
                "digest": digest_bytes(path.read_bytes()),
                "path": path.relative_to(resolved).as_posix(),
            }
        )
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return digest_bytes(encoded)


@dataclass(frozen=True, slots=True)
class DockerSandboxConfig:
    docker_cli: Path
    docker_version: str
    image: str
    workspace: WorkspaceBinding
    patch_runtime_root: Path | None = None
    memory_bytes: int = 268_435_456
    cpus: float = 1.0
    pids_limit: int = 64
    tmpfs_bytes: int = 16_777_216
    user: str = "65534:65534"

    def __post_init__(self) -> None:
        cli = Path(self.docker_cli).resolve()
        if not cli.is_file():
            raise DockerBackendError("docker_cli must identify an existing file")
        if not isinstance(self.workspace, WorkspaceBinding):
            raise DockerBackendError("workspace must be a WorkspaceBinding")
        root = self.workspace.root
        if "," in str(root):
            raise DockerBackendError("workspace_root cannot contain a comma")
        runtime = self.patch_runtime_root
        if runtime is not None:
            if not self.workspace.writable:
                raise DockerBackendError("patch runtime requires a writable snapshot")
            runtime = Path(runtime).resolve()
            if not runtime.is_dir():
                raise DockerBackendError("patch_runtime_root must be a directory")
            if "," in str(runtime) or "," in str(self.workspace.source_root):
                raise DockerBackendError("patch mount paths cannot contain a comma")
            object.__setattr__(self, "patch_runtime_root", runtime)
        if not isinstance(self.docker_version, str) or not self.docker_version.strip():
            raise DockerBackendError("docker_version must be a non-empty string")
        _image_digest(self.image)
        _positive_integer(self.memory_bytes, "memory_bytes")
        _positive_integer(self.pids_limit, "pids_limit")
        _positive_integer(self.tmpfs_bytes, "tmpfs_bytes")
        if isinstance(self.cpus, bool) or not isinstance(self.cpus, (int, float)):
            raise DockerBackendError("cpus must be positive")
        if not math.isfinite(self.cpus) or self.cpus <= 0:
            raise DockerBackendError("cpus must be positive")
        if not isinstance(self.user, str):
            raise DockerBackendError("user must be a non-root numeric uid:gid")
        uid, separator, gid = self.user.partition(":")
        if not separator or not uid.isdigit() or not gid.isdigit() or int(uid) == 0:
            raise DockerBackendError("user must be a non-root numeric uid:gid")
        object.__setattr__(self, "docker_cli", cli)

    @property
    def workspace_root(self) -> Path:
        return self.workspace.root

    @property
    def image_digest(self) -> str:
        return _image_digest(self.image)

    @property
    def environment_digest(self) -> str:
        cli = identify_executable("docker", self.docker_cli)
        runtime_digest = None
        if self.patch_runtime_root is not None:
            runtime_digest = _runtime_source_digest(self.patch_runtime_root)
        record = {
            "adapter_implementation_digest": _implementation_digest(),
            "cpus": self.cpus,
            "docker_cli_digest": cli.digest,
            "docker_version": self.docker_version,
            "image": self.image,
            "memory_bytes": self.memory_bytes,
            "pids_limit": self.pids_limit,
            "patch_runtime_digest": runtime_digest,
            "tmpfs_bytes": self.tmpfs_bytes,
            "user": self.user,
            "workspace_access": self.workspace.access,
            "workspace_source_digest": self.workspace.source_digest,
            "workspace_source_root": str(self.workspace.source_root),
        }
        encoded = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        return digest_bytes(encoded)


@dataclass(frozen=True, slots=True)
class CliResult:
    started_at: str
    ended_at: str
    exit_code: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    stdout_truncated: bool
    stderr_truncated: bool


class DockerTransport(Protocol):
    def run(
        self,
        argv: tuple[str, ...],
        abort_argv: tuple[str, ...],
        timeout_seconds: float,
        max_output_bytes: int,
    ) -> CliResult: ...


class _BoundedProcessTransport:
    """Runs only the Docker CLI while bounding retained output and wall time."""

    def run(
        self,
        argv: tuple[str, ...],
        abort_argv: tuple[str, ...],
        timeout_seconds: float,
        max_output_bytes: int,
    ) -> CliResult:
        started_at = _utc_timestamp()
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            creationflags=creation_flags,
        )
        assert process.stdout is not None
        assert process.stderr is not None

        buffers = (bytearray(), bytearray())
        truncated = [False, False]
        retained = 0
        lock = Lock()
        output_exceeded = Event()
        stream_errors: list[Exception] = []

        def drain(stream, index: int) -> None:
            nonlocal retained
            try:
                while True:
                    chunk = stream.read(65_536)
                    if not chunk:
                        break
                    with lock:
                        available = max(0, max_output_bytes - retained)
                        accepted = chunk[:available]
                        buffers[index].extend(accepted)
                        retained += len(accepted)
                        if len(accepted) != len(chunk):
                            truncated[index] = True
                            output_exceeded.set()
            except Exception as error:
                with lock:
                    stream_errors.append(error)
                    output_exceeded.set()

        threads = (
            Thread(target=drain, args=(process.stdout, 0), daemon=True),
            Thread(target=drain, args=(process.stderr, 1), daemon=True),
        )
        for thread in threads:
            thread.start()

        deadline = time.monotonic() + timeout_seconds
        timed_out = False
        while process.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            if output_exceeded.wait(min(0.02, remaining)):
                break

        if process.poll() is None and (timed_out or output_exceeded.is_set()):
            self._abort(abort_argv, creation_flags)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

        for thread in threads:
            thread.join(timeout=5)
        if any(thread.is_alive() for thread in threads):
            process.kill()
            raise DockerBackendError("Docker output streams did not close")
        if stream_errors:
            raise DockerBackendError("Docker output stream capture failed") from stream_errors[0]

        ended_at = _utc_timestamp()
        return CliResult(
            started_at=started_at,
            ended_at=ended_at,
            exit_code=None if timed_out else process.returncode,
            timed_out=timed_out,
            stdout=bytes(buffers[0]),
            stderr=bytes(buffers[1]),
            stdout_truncated=truncated[0],
            stderr_truncated=truncated[1],
        )

    @staticmethod
    def _abort(argv: tuple[str, ...], creation_flags: int) -> None:
        try:
            subprocess.run(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
                timeout=5,
                creationflags=creation_flags,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass


class DockerCliBackend:
    """Runs a typed workspace binding in a locked-down disposable container."""

    def __init__(
        self,
        config: DockerSandboxConfig,
        transport: DockerTransport | None = None,
        name_factory: Callable[[], str] | None = None,
    ) -> None:
        self._config = config
        self._transport = transport or _BoundedProcessTransport()
        self._docker_identity = identify_executable("docker", config.docker_cli)
        self._name_factory = name_factory or (
            lambda: f"sheath-{uuid.uuid4().hex[:20]}"
        )
        self._profile = SandboxProfile(
            backend_id="docker-cli",
            backend_version=config.docker_version,
            environment_digest=config.environment_digest,
            filesystem_isolated=True,
            network_disabled=True,
            process_isolated=True,
            resource_limits_enforced=True,
            executable_identity_enforced=True,
        )

    @property
    def profile(self) -> SandboxProfile:
        return self._profile

    @property
    def config(self) -> DockerSandboxConfig:
        return self._config

    def execute(self, request: SandboxRequest) -> SandboxResult:
        self._validate_request(request)
        relative = Path(request.working_directory).resolve().relative_to(
            self._config.workspace_root
        )
        workdir = PurePosixPath("/workspace", *relative.parts).as_posix()
        name = self._name_factory()
        if not name.startswith("sheath-") or not name.removeprefix("sheath-").isalnum():
            raise DockerBackendError("container name factory returned an unsafe name")

        docker = str(self._config.docker_cli)
        mount = (
            f"type=bind,source={self._config.workspace_root},"
            "target=/workspace"
        )
        if not self._config.workspace.writable:
            mount += ",readonly"
        extra_mounts: tuple[str, ...] = ()
        extra_environment: tuple[str, ...] = ()
        if self._config.patch_runtime_root is not None:
            source_mount = (
                f"type=bind,source={self._config.workspace.source_root},"
                "target=/source,readonly"
            )
            runtime_mount = (
                f"type=bind,source={self._config.patch_runtime_root},"
                "target=/sheath-runtime,readonly"
            )
            extra_mounts = (
                "--mount",
                source_mount,
                "--mount",
                runtime_mount,
            )
            extra_environment = ("--env", "PYTHONPATH=/sheath-runtime")
        argv = (
            docker,
            "run",
            "--pull",
            "never",
            "--name",
            name,
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges=true",
            "--pids-limit",
            str(self._config.pids_limit),
            "--memory",
            str(self._config.memory_bytes),
            "--cpus",
            str(self._config.cpus),
            "--user",
            self._config.user,
            "--mount",
            mount,
            *extra_mounts,
            "--tmpfs",
            f"/tmp:rw,noexec,nosuid,size={self._config.tmpfs_bytes}",
            "--workdir",
            workdir,
            "--env",
            "HOME=/tmp",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            *extra_environment,
            "--init",
            "--entrypoint",
            request.executable_path,
            self._config.image,
            *request.argv[1:],
        )
        result = self._transport.run(
            argv,
            (docker, "rm", "--force", name),
            request.timeout_seconds,
            request.max_output_bytes,
        )
        return SandboxResult(
            action_id=request.action_id,
            sandbox_digest=self.profile.digest,
            started_at=result.started_at,
            ended_at=result.ended_at,
            exit_code=result.exit_code,
            timed_out=result.timed_out,
            stdout=result.stdout,
            stderr=result.stderr,
            stdout_truncated=result.stdout_truncated,
            stderr_truncated=result.stderr_truncated,
        )

    def _validate_request(self, request: SandboxRequest) -> None:
        if not self._docker_identity.matches_source():
            raise DockerBackendError("Docker CLI identity changed before dispatch")
        if self._config.environment_digest != self.profile.environment_digest:
            raise DockerBackendError("Docker configuration sources changed before dispatch")
        if request.environment_digest != self.profile.environment_digest:
            raise DockerBackendError("request environment does not match Docker profile")
        if request.executable_scope != "container_image":
            raise DockerBackendError("Docker requires a container executable identity")
        if request.executable_image_digest != self._config.image_digest:
            raise DockerBackendError("executable identity uses another image")
        expected = identify_container_executable(
            "target",
            request.executable_path,
            self._config.image_digest,
        )
        if request.executable_digest != expected.digest:
            raise DockerBackendError("container executable identity is invalid")
        if request.executable_size_bytes != 0:
            raise DockerBackendError("container executable size must be zero")
        if not request.argv or request.argv[0] != request.executable_path:
            raise DockerBackendError("argv must start with the identified executable")
        working_directory = Path(request.working_directory).resolve()
        try:
            working_directory.relative_to(self._config.workspace_root)
        except ValueError as error:
            raise DockerBackendError("working directory escapes workspace") from error
        if not working_directory.is_dir():
            raise DockerBackendError("working directory does not exist")
