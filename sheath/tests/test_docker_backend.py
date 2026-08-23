from io import BytesIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from sheath import (
    ArtifactStore,
    CliResult,
    CommandAction,
    CommandPolicy,
    ConstrainedRunner,
    DockerBackendError,
    DockerCliBackend,
    DockerSandboxConfig,
    EvidenceLedger,
    SandboxRequest,
    SnapshotStager,
    ToolSession,
    identify_container_executable,
    identify_executable,
    read_only_workspace,
)
from sheath.docker_backend import _BoundedProcessTransport


IMAGE_DIGEST = "sha256:" + "1" * 64
IMAGE = f"example.invalid/sheath-smoke@{IMAGE_DIGEST}"


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[
            tuple[tuple[str, ...], tuple[str, ...], float, int]
        ] = []

    def run(
        self,
        argv: tuple[str, ...],
        abort_argv: tuple[str, ...],
        timeout_seconds: float,
        max_output_bytes: int,
    ) -> CliResult:
        self.calls.append((argv, abort_argv, timeout_seconds, max_output_bytes))
        return CliResult(
            started_at="2026-08-14T00:20:00Z",
            ended_at="2026-08-14T00:20:01Z",
            exit_code=0,
            timed_out=False,
            stdout=b'{"smoke":"passed"}\n',
            stderr=b"",
            stdout_truncated=False,
            stderr_truncated=False,
        )


class FinishedProcess:
    def __init__(self, stdout: bytes, stderr: bytes) -> None:
        self.stdout = BytesIO(stdout)
        self.stderr = BytesIO(stderr)
        self.returncode = 0

    def poll(self):
        return self.returncode


class HangingProcess(FinishedProcess):
    def __init__(self) -> None:
        super().__init__(b"", b"")
        self.returncode = None

    def wait(self, timeout=None):
        del timeout
        self.returncode = 137
        return self.returncode

    def kill(self) -> None:
        self.returncode = 137


class FailingStream(BytesIO):
    def read(self, size=-1):
        del size
        raise OSError("fixture stream failure")


class BoundedTransportTests(unittest.TestCase):
    def test_retains_only_the_combined_output_limit(self) -> None:
        process = FinishedProcess(b"a" * 20, b"b" * 20)

        with patch("sheath.docker_backend.subprocess.Popen", return_value=process):
            result = _BoundedProcessTransport().run(
                ("docker", "run"),
                ("docker", "rm", "--force", "sheath-fixture"),
                1,
                16,
            )

        self.assertEqual(len(result.stdout) + len(result.stderr), 16)
        self.assertTrue(result.stdout_truncated or result.stderr_truncated)

    def test_timeout_requests_forced_container_removal(self) -> None:
        process = HangingProcess()

        with (
            patch("sheath.docker_backend.subprocess.Popen", return_value=process),
            patch("sheath.docker_backend.subprocess.run") as abort,
        ):
            result = _BoundedProcessTransport().run(
                ("docker", "run"),
                ("docker", "rm", "--force", "sheath-fixture"),
                0.01,
                16,
            )

        self.assertTrue(result.timed_out)
        self.assertIsNone(result.exit_code)
        self.assertEqual(
            abort.call_args.args[0],
            ("docker", "rm", "--force", "sheath-fixture"),
        )

    def test_stream_failure_cannot_become_successful_evidence(self) -> None:
        process = FinishedProcess(b"", b"")
        process.stdout = FailingStream()

        with (
            patch("sheath.docker_backend.subprocess.Popen", return_value=process),
            self.assertRaisesRegex(DockerBackendError, "capture failed"),
        ):
            _BoundedProcessTransport().run(
                ("docker", "run"),
                ("docker", "rm", "--force", "sheath-fixture"),
                1,
                16,
            )


class DockerBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory(dir=Path(__file__).parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = ArtifactStore(self.root / "artifacts")
        self.transport = FakeTransport()
        self.config = DockerSandboxConfig(
            docker_cli=Path(sys.executable),
            docker_version="fixture-29.1.3",
            image=IMAGE,
            workspace=read_only_workspace(self.root),
            memory_bytes=64 * 1024 * 1024,
            cpus=0.5,
            pids_limit=16,
            tmpfs_bytes=1024 * 1024,
        )
        self.backend = DockerCliBackend(
            self.config,
            self.transport,
            name_factory=lambda: "sheath-fixture123",
        )

    def session(self, identity=None) -> ToolSession:
        executable = identity or identify_container_executable(
            "python",
            "/usr/local/bin/python",
            IMAGE_DIGEST,
        )
        ledger = EvidenceLedger("r1")
        policy = CommandPolicy(
            self.root,
            (executable,),
            max_timeout_seconds=30,
            max_output_bytes=4096,
        )
        return ToolSession(policy, ledger, self.store)

    def test_dispatches_digest_pinned_locked_down_container(self) -> None:
        session = self.session()
        runner = ConstrainedRunner(session, self.backend)

        outcome = runner.execute(
            CommandAction(
                "action-smoke",
                ("python", "container_smoke.py"),
                ".",
                10,
                2048,
            ),
            ("smoke.isolation",),
        )

        argv, abort, timeout, output_limit = self.transport.calls[0]
        self.assertEqual(argv[0], str(Path(sys.executable).resolve()))
        self.assertIn(("--pull", "never"), tuple(zip(argv, argv[1:])))
        self.assertIn(("--network", "none"), tuple(zip(argv, argv[1:])))
        self.assertIn("--read-only", argv)
        self.assertIn(("--cap-drop", "ALL"), tuple(zip(argv, argv[1:])))
        self.assertIn("no-new-privileges=true", argv)
        self.assertIn(
            ("--entrypoint", "/usr/local/bin/python"),
            tuple(zip(argv, argv[1:])),
        )
        self.assertIn(IMAGE, argv)
        self.assertEqual(argv[-2:], (IMAGE, "container_smoke.py"))
        mount = argv[argv.index("--mount") + 1]
        self.assertTrue(mount.endswith("target=/workspace,readonly"))
        self.assertEqual(abort[-3:], ("rm", "--force", "sheath-fixture123"))
        self.assertEqual(timeout, 10)
        self.assertEqual(output_limit, 2048)
        self.assertTrue(outcome.evidence[0].passed)

    def test_writable_snapshot_mount_does_not_weaken_container_root(self) -> None:
        source = self.root / "source"
        source.mkdir()
        (source / "input.txt").write_text("original\n", encoding="utf-8")
        runtime = self.root / "runtime"
        runtime.mkdir()
        (runtime / "worker.py").write_text("# trusted fixture\n", encoding="utf-8")
        snapshot = SnapshotStager(self.root / "staging").stage(source)
        self.addCleanup(snapshot.close)
        transport = FakeTransport()
        config = DockerSandboxConfig(
            docker_cli=Path(sys.executable),
            docker_version="fixture-29.1.3",
            image=IMAGE,
            workspace=snapshot.binding,
            patch_runtime_root=runtime,
        )
        backend = DockerCliBackend(
            config,
            transport,
            name_factory=lambda: "sheath-writable123",
        )
        identity = identify_container_executable(
            "python",
            "/usr/local/bin/python",
            IMAGE_DIGEST,
        )
        ledger = EvidenceLedger("r1")
        session = ToolSession(
            CommandPolicy(snapshot.root, (identity,), 30, 4096),
            ledger,
            self.store,
        )

        outcome = ConstrainedRunner(session, backend).execute(
            CommandAction("action-write", ("python",), ".", 10, 2048),
            ("smoke.snapshot_write",),
        )

        argv = transport.calls[0][0]
        mount = argv[argv.index("--mount") + 1]
        self.assertEqual(mount, f"type=bind,source={snapshot.root},target=/workspace")
        mounts = [
            argv[index + 1]
            for index, value in enumerate(argv)
            if value == "--mount"
        ]
        self.assertIn(
            f"type=bind,source={source},target=/source,readonly",
            mounts,
        )
        self.assertIn(
            f"type=bind,source={runtime},target=/sheath-runtime,readonly",
            mounts,
        )
        self.assertIn("PYTHONPATH=/sheath-runtime", argv)
        self.assertIn("--read-only", argv)
        self.assertTrue(outcome.evidence[0].passed)

    def test_patch_runtime_rejects_read_only_workspace(self) -> None:
        with self.assertRaisesRegex(DockerBackendError, "writable snapshot"):
            DockerSandboxConfig(
                docker_cli=Path(sys.executable),
                docker_version="fixture",
                image=IMAGE,
                workspace=read_only_workspace(self.root),
                patch_runtime_root=self.root,
            )

    def test_patch_runtime_is_revalidated_before_dispatch(self) -> None:
        source = self.root / "runtime-source"
        source.mkdir()
        runtime = self.root / "runtime-drift"
        runtime.mkdir()
        worker = runtime / "worker.py"
        worker.write_text("trusted = True\n", encoding="utf-8")
        snapshot = SnapshotStager(self.root / "runtime-staging").stage(source)
        self.addCleanup(snapshot.close)
        transport = FakeTransport()
        backend = DockerCliBackend(
            DockerSandboxConfig(
                docker_cli=Path(sys.executable),
                docker_version="fixture",
                image=IMAGE,
                workspace=snapshot.binding,
                patch_runtime_root=runtime,
            ),
            transport,
            name_factory=lambda: "sheath-runtimedrift",
        )
        identity = identify_container_executable(
            "python",
            "/usr/local/bin/python",
            IMAGE_DIGEST,
        )
        session = ToolSession(
            CommandPolicy(snapshot.root, (identity,), 30, 4096),
            EvidenceLedger("r1"),
            self.store,
        )
        request = self._request(session, "action-runtime-drift", backend)
        worker.write_text("trusted = False\n", encoding="utf-8")

        with self.assertRaisesRegex(DockerBackendError, "sources changed"):
            backend.execute(request)

        self.assertEqual(transport.calls, [])

    def test_config_rejects_untyped_workspace_path(self) -> None:
        with self.assertRaisesRegex(DockerBackendError, "WorkspaceBinding"):
            DockerSandboxConfig(
                docker_cli=Path(sys.executable),
                docker_version="fixture",
                image=IMAGE,
                workspace=self.root,  # type: ignore[arg-type]
            )

    def test_equivalent_snapshot_copies_share_environment_digest(self) -> None:
        source = self.root / "digest-source"
        source.mkdir()
        (source / "input.txt").write_text("same\n", encoding="utf-8")
        first = SnapshotStager(self.root / "staging-one").stage(source)
        second = SnapshotStager(self.root / "staging-two").stage(source)
        self.addCleanup(first.close)
        self.addCleanup(second.close)

        first_config = DockerSandboxConfig(
            Path(sys.executable),
            "fixture",
            IMAGE,
            first.binding,
        )
        second_config = DockerSandboxConfig(
            Path(sys.executable),
            "fixture",
            IMAGE,
            second.binding,
        )

        self.assertNotEqual(first.root, second.root)
        self.assertEqual(
            first_config.environment_digest,
            second_config.environment_digest,
        )

    def test_rejects_unpinned_image(self) -> None:
        with self.assertRaisesRegex(DockerBackendError, "pinned by digest"):
            DockerSandboxConfig(
                docker_cli=Path(sys.executable),
                docker_version="fixture",
                image="python:3.12-alpine",
                workspace=read_only_workspace(self.root),
            )

    def test_rejects_root_container_user(self) -> None:
        with self.assertRaisesRegex(DockerBackendError, "non-root"):
            DockerSandboxConfig(
                docker_cli=Path(sys.executable),
                docker_version="fixture",
                image=IMAGE,
                workspace=read_only_workspace(self.root),
                user="0:0",
            )

    def test_host_executable_cannot_cross_container_boundary(self) -> None:
        session = self.session(identify_executable("python", Path(sys.executable)))

        with self.assertRaisesRegex(DockerBackendError, "container executable"):
            self.backend.execute(self._request(session, "action-host"))

        self.assertEqual(self.transport.calls, [])

    def test_executable_identity_must_use_configured_image(self) -> None:
        other_digest = "sha256:" + "2" * 64
        identity = identify_container_executable(
            "python",
            "/usr/local/bin/python",
            other_digest,
        )
        session = self.session(identity)
        authorization = session.request_action(
            CommandAction("action-smoke", ("python",), ".", 10, 2048)
        )
        request = SandboxRequest(
            action_id="action-smoke",
            executable_path=identity.path,
            executable_digest=identity.digest,
            executable_size_bytes=identity.size_bytes,
            executable_scope=identity.scope,
            executable_image_digest=identity.image_digest,
            argv=(identity.path,),
            working_directory=authorization.resolved_working_directory or "",
            timeout_seconds=10,
            max_output_bytes=2048,
            environment_digest=self.backend.profile.environment_digest,
        )

        with self.assertRaisesRegex(DockerBackendError, "another image"):
            self.backend.execute(request)

        self.assertEqual(self.transport.calls, [])

    def test_docker_cli_is_revalidated_before_dispatch(self) -> None:
        docker = self.root / "docker.bin"
        docker.write_bytes(b"trusted docker cli")
        transport = FakeTransport()
        backend = DockerCliBackend(
            DockerSandboxConfig(
                docker_cli=docker,
                docker_version="fixture",
                image=IMAGE,
                workspace=read_only_workspace(self.root),
            ),
            transport,
            name_factory=lambda: "sheath-fixture456",
        )
        session = self.session()
        request = self._request(session, "action-cli-drift", backend)
        docker.write_bytes(b"changed docker cli")

        with self.assertRaisesRegex(DockerBackendError, "CLI identity changed"):
            backend.execute(request)

        self.assertEqual(transport.calls, [])

    def _request(
        self,
        session: ToolSession,
        action_id: str,
        backend: DockerCliBackend | None = None,
    ) -> SandboxRequest:
        action = CommandAction(action_id, ("python",), ".", 10, 2048)
        authorization = session.request_action(action)
        identity = session.executables[0]

        return SandboxRequest(
            action_id=action.id,
            executable_path=identity.path,
            executable_digest=identity.digest,
            executable_size_bytes=identity.size_bytes,
            executable_scope=identity.scope,
            executable_image_digest=identity.image_digest,
            argv=(identity.path,),
            working_directory=authorization.resolved_working_directory or "",
            timeout_seconds=action.timeout_seconds,
            max_output_bytes=action.max_output_bytes,
            environment_digest=(backend or self.backend).profile.environment_digest,
        )


if __name__ == "__main__":
    unittest.main()
