from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from sheath import (
    SnapshotError,
    SnapshotStager,
    WorkspaceBinding,
    directory_digest,
    read_only_workspace,
)


class SnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory(dir=Path(__file__).parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.staging = self.root / "staging"
        self.source.mkdir()
        (self.source / "nested").mkdir()
        (self.source / "nested" / "input.txt").write_text(
            "original\n",
            encoding="utf-8",
        )

    def test_digest_changes_with_file_content(self) -> None:
        before = directory_digest(self.source)

        (self.source / "nested" / "input.txt").write_text(
            "changed\n",
            encoding="utf-8",
        )

        self.assertNotEqual(directory_digest(self.source), before)

    def test_stages_verified_isolated_copy_and_removes_it(self) -> None:
        snapshot = SnapshotStager(self.staging).stage(self.source)
        snapshot_root = snapshot.root

        self.assertEqual(snapshot.source_digest, directory_digest(self.source))
        self.assertEqual(snapshot.source_digest, directory_digest(snapshot.root))
        self.assertTrue(snapshot.binding.writable)
        (snapshot.root / "nested" / "input.txt").write_text(
            "snapshot only\n",
            encoding="utf-8",
        )
        self.assertEqual(
            (self.source / "nested" / "input.txt").read_text(encoding="utf-8"),
            "original\n",
        )

        snapshot.close()
        snapshot.close()

        self.assertTrue(snapshot.closed)
        self.assertFalse(snapshot_root.exists())
        with self.assertRaisesRegex(SnapshotError, "already closed"):
            _ = snapshot.binding

    def test_context_cleanup_runs_after_an_exception(self) -> None:
        snapshot_root = None
        with self.assertRaisesRegex(RuntimeError, "fixture"):
            with SnapshotStager(self.staging).stage(self.source) as snapshot:
                snapshot_root = snapshot.root
                raise RuntimeError("fixture")

        assert snapshot_root is not None
        self.assertFalse(snapshot_root.exists())

    def test_rejects_overlapping_source_and_staging_roots(self) -> None:
        stager = SnapshotStager(self.source / "staging")

        with self.assertRaisesRegex(SnapshotError, "cannot overlap"):
            stager.stage(self.source)

    def test_rejects_source_mutation_during_copy(self) -> None:
        real_digest = directory_digest
        calls = 0

        def mutating_digest(root):
            nonlocal calls
            calls += 1
            if calls == 2:
                (self.source / "nested" / "input.txt").write_text(
                    "changed during copy\n",
                    encoding="utf-8",
                )
            return real_digest(root)

        with (
            patch("sheath.snapshots.directory_digest", side_effect=mutating_digest),
            self.assertRaisesRegex(SnapshotError, "source changed"),
        ):
            SnapshotStager(self.staging).stage(self.source)

        self.assertEqual(tuple(self.staging.iterdir()), ())

    def test_restages_owned_snapshot_as_an_independent_revision(self) -> None:
        stager = SnapshotStager(self.staging)
        first = stager.stage(self.source)
        (first.root / "nested" / "input.txt").write_text(
            "attempt one\n",
            encoding="utf-8",
        )

        second = stager.restage(first)
        self.assertEqual(second.source_digest, directory_digest(first.root))
        (second.root / "nested" / "input.txt").write_text(
            "attempt two\n",
            encoding="utf-8",
        )
        self.assertEqual(
            (first.root / "nested" / "input.txt").read_text(encoding="utf-8"),
            "attempt one\n",
        )

        second.close()
        first.close()
        self.assertEqual(tuple(self.staging.iterdir()), ())

    def test_restage_rejects_closed_or_foreign_snapshot(self) -> None:
        stager = SnapshotStager(self.staging)
        snapshot = stager.stage(self.source)
        other_stager = SnapshotStager(self.root / "other-staging")

        with self.assertRaisesRegex(SnapshotError, "not owned"):
            other_stager.restage(snapshot)
        snapshot.close()
        with self.assertRaisesRegex(SnapshotError, "active"):
            stager.restage(snapshot)

    def test_workspace_binding_rejects_unsafe_access_claims(self) -> None:
        read_only = read_only_workspace(self.source)
        self.assertFalse(read_only.writable)

        with self.assertRaisesRegex(SnapshotError, "refer directly"):
            WorkspaceBinding(
                self.source,
                "read_only",
                self.root,
                None,
            )
        with self.assertRaisesRegex(SnapshotError, "separate"):
            WorkspaceBinding(
                self.source,
                "writable_snapshot",
                self.source,
                "sha256:" + "1" * 64,
            )


if __name__ == "__main__":
    unittest.main()
