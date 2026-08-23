import base64
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from sheath import (
    ArtifactStore,
    CliResult,
    DockerCliBackend,
    DockerPatchExtractor,
    DockerSandboxConfig,
    PatchError,
    SnapshotStager,
    directory_digest,
    identify_container_executable,
)
from sheath.patches import _build_patch_record, _runtime_digest, _validate_record


IMAGE_DIGEST = "sha256:" + "1" * 64
IMAGE = f"example.invalid/sheath-patch@{IMAGE_DIGEST}"


class PatchTransport:
    def __init__(self, source: Path, result: Path, source_digest: str) -> None:
        self.source = source
        self.result = result
        self.source_digest = source_digest
        self.calls = []

    def run(self, argv, abort_argv, timeout_seconds, max_output_bytes):
        self.calls.append((argv, abort_argv, timeout_seconds, max_output_bytes))
        identity = identify_container_executable(
            "python",
            "/usr/local/bin/python",
            IMAGE_DIGEST,
        )
        encoded = _build_patch_record(
            self.source,
            self.result,
            self.source_digest,
            identity.digest,
            _runtime_digest(),
            max_output_bytes,
        )
        return CliResult(
            started_at="2026-08-14T09:10:00Z",
            ended_at="2026-08-14T09:10:01Z",
            exit_code=0,
            timed_out=False,
            stdout=encoded,
            stderr=b"",
            stdout_truncated=False,
            stderr_truncated=False,
        )


class PatchExtractorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory(dir=Path(__file__).parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "keep.txt").write_text("same\n", encoding="utf-8")
        (self.source / "modify.txt").write_text("before\n", encoding="utf-8")
        (self.source / "delete.txt").write_text("delete\n", encoding="utf-8")
        self.snapshot = SnapshotStager(self.root / "staging").stage(self.source)
        self.addCleanup(self.snapshot.close)
        self.store = ArtifactStore(self.root / "artifacts")
        self.identity = identify_container_executable(
            "python",
            "/usr/local/bin/python",
            IMAGE_DIGEST,
        )

    def build(self, maximum: int = 4_194_304):
        encoded = _build_patch_record(
            self.source,
            self.snapshot.root,
            self.snapshot.source_digest,
            self.identity.digest,
            _runtime_digest(),
            maximum,
        )
        record, paths = _validate_record(
            encoded,
            self.snapshot.source_digest,
            self.identity.digest,
            _runtime_digest(),
        )
        return encoded, record, paths

    def mutate(self) -> None:
        (self.snapshot.root / "modify.txt").write_bytes(b"after\n")
        (self.snapshot.root / "delete.txt").unlink()
        (self.snapshot.root / "added.bin").write_bytes(b"\x00\xff\x10")
        (self.snapshot.root / "new-dir").mkdir()
        (self.snapshot.root / "new-dir" / "nested.txt").write_text(
            "nested\n",
            encoding="utf-8",
        )

    def backend(self, transport) -> DockerCliBackend:
        config = DockerSandboxConfig(
            Path(sys.executable),
            "fixture",
            IMAGE,
            self.snapshot.binding,
            patch_runtime_root=Path(__file__).parents[1] / "src",
        )
        return DockerCliBackend(
            config,
            transport,
            name_factory=lambda: "sheath-patchfixture",
        )

    def test_builds_canonical_binary_safe_delta(self) -> None:
        self.mutate()

        first, record, paths = self.build()
        second, _, _ = self.build()

        self.assertEqual(first, second)
        self.assertEqual(record["source_digest"], self.snapshot.source_digest)
        self.assertEqual(record["result_digest"], directory_digest(self.snapshot.root))
        self.assertEqual(
            paths,
            (
                "added.bin",
                "delete.txt",
                "modify.txt",
                "new-dir",
                "new-dir/nested.txt",
            ),
        )
        changes = {change["path"]: change for change in record["changes"]}
        self.assertEqual(changes["delete.txt"]["operation"], "delete")
        self.assertEqual(changes["new-dir"]["after"]["kind"], "directory")
        self.assertEqual(
            base64.b64decode(changes["added.bin"]["after"]["content_base64"]),
            b"\x00\xff\x10",
        )
        self.assertEqual(
            base64.b64decode(changes["modify.txt"]["after"]["content_base64"]),
            b"after\n",
        )

    def test_unchanged_snapshot_produces_empty_delta(self) -> None:
        _, record, paths = self.build()

        self.assertEqual(paths, ())
        self.assertEqual(record["source_digest"], record["result_digest"])
        self.assertEqual(record["changes"], [])

    def test_docker_extractor_stores_patch_and_evidence(self) -> None:
        self.mutate()
        transport = PatchTransport(
            self.source,
            self.snapshot.root,
            self.snapshot.source_digest,
        )
        extractor = DockerPatchExtractor(self.backend(transport), self.identity)

        extraction = extractor.extract(self.snapshot, self.store)
        record = json.loads(
            (self.store.root / extraction.artifact.path).read_bytes()
        )

        self.assertEqual(extraction.artifact.kind, "patch")
        self.assertEqual(extraction.changed_paths, tuple(
            change["path"] for change in record["changes"]
        ))
        self.assertEqual(extraction.observation_id, "observation:action-patch-extract")
        self.assertEqual(len(extraction.evidence_ids), 1)
        self.assertRegex(extraction.sandbox_digest, r"^sha256:[0-9a-f]{64}$")
        self.assertTrue(extraction.stdout_artifact_id.startswith("artifact:stdout:"))
        self.assertTrue(extraction.stderr_artifact_id.startswith("artifact:stderr:"))
        argv = transport.calls[0][0]
        self.assertIn("PYTHONPATH=/sheath-runtime", argv)

    def test_rejects_patch_limit_and_source_drift(self) -> None:
        (self.snapshot.root / "large.bin").write_bytes(b"x" * 4096)
        with self.assertRaisesRegex(PatchError, "byte limit"):
            self.build(256)

        (self.snapshot.root / "large.bin").unlink()
        (self.source / "keep.txt").write_text("source drift\n", encoding="utf-8")
        with self.assertRaisesRegex(PatchError, "staged revision"):
            self.build()

    def test_rejects_closed_snapshot_and_invalid_budgets(self) -> None:
        transport = PatchTransport(
            self.source,
            self.snapshot.root,
            self.snapshot.source_digest,
        )
        backend = self.backend(transport)
        self.snapshot.close()

        with self.assertRaisesRegex(PatchError, "active WorkspaceSnapshot"):
            DockerPatchExtractor(backend, self.identity).extract(
                self.snapshot,
                self.store,
            )
        with self.assertRaisesRegex(PatchError, "timeout_seconds"):
            DockerPatchExtractor(backend, self.identity, timeout_seconds=0)
        with self.assertRaisesRegex(PatchError, "max_patch_bytes"):
            DockerPatchExtractor(backend, self.identity, max_patch_bytes=0)


if __name__ == "__main__":
    unittest.main()
