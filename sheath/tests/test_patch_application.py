import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from sheath import (
    ArtifactStore,
    PatchApplier,
    PatchError,
    SnapshotStager,
    directory_digest,
    identify_container_executable,
)
from sheath.patches import _build_patch_record, _runtime_digest


IMAGE_DIGEST = "sha256:" + "1" * 64


class PatchApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory(dir=Path(__file__).parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "keep.txt").write_text("same\n", encoding="utf-8")
        (self.source / "modify.txt").write_text("before\n", encoding="utf-8")
        (self.source / "delete.txt").write_text("delete\n", encoding="utf-8")
        self.stager = SnapshotStager(self.root / "staging")
        self.store = ArtifactStore(self.root / "artifacts")
        self.identity = identify_container_executable(
            "python",
            "/usr/local/bin/python",
            IMAGE_DIGEST,
        )

    def make_patch(self, *, mutate: bool = True):
        with self.stager.stage(self.source) as result:
            if mutate:
                (result.root / "modify.txt").write_bytes(b"after\n")
                (result.root / "delete.txt").unlink()
                (result.root / "added.bin").write_bytes(b"\x00\xff\x10")
                (result.root / "new-dir").mkdir()
                (result.root / "new-dir" / "nested.txt").write_bytes(b"nested\n")
            encoded = _build_patch_record(
                self.source,
                result.root,
                result.source_digest,
                self.identity.digest,
                _runtime_digest(),
                4_194_304,
            )
        return self.store.store_bytes("patch", encoded), json.loads(encoded)

    def fresh_snapshot(self):
        snapshot = self.stager.stage(self.source)
        self.addCleanup(snapshot.close)
        return snapshot

    def changed_patch(self, record, change) -> object:
        change(record)
        encoded = (
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        return self.store.store_bytes("patch", encoded)

    def test_applies_patch_to_fresh_snapshot(self) -> None:
        patch, record = self.make_patch()
        snapshot = self.fresh_snapshot()

        application = PatchApplier().apply(snapshot, patch, self.store)

        self.assertEqual(application.patch_artifact_id, patch.id)
        self.assertEqual(application.source_digest, snapshot.source_digest)
        self.assertEqual(application.result_digest, record["result_digest"])
        self.assertEqual(directory_digest(snapshot.root), record["result_digest"])
        self.assertEqual((snapshot.root / "added.bin").read_bytes(), b"\x00\xff\x10")
        self.assertEqual((snapshot.root / "modify.txt").read_bytes(), b"after\n")
        self.assertFalse((snapshot.root / "delete.txt").exists())
        self.assertEqual(
            application.changed_paths,
            ("added.bin", "delete.txt", "modify.txt", "new-dir", "new-dir/nested.txt"),
        )

    def test_applies_empty_patch_without_changing_snapshot(self) -> None:
        patch, _ = self.make_patch(mutate=False)
        snapshot = self.fresh_snapshot()

        application = PatchApplier().apply(snapshot, patch, self.store)

        self.assertEqual(application.changed_paths, ())
        self.assertEqual(directory_digest(snapshot.root), snapshot.source_digest)

    def test_rejects_nonfresh_snapshot_and_discards_it(self) -> None:
        patch, _ = self.make_patch()
        snapshot = self.fresh_snapshot()
        root = snapshot.root
        (root / "keep.txt").write_text("drift\n", encoding="utf-8")

        with self.assertRaisesRegex(PatchError, "fresh snapshot"):
            PatchApplier().apply(snapshot, patch, self.store)

        self.assertTrue(snapshot.closed)
        self.assertFalse(root.exists())

    def test_rejects_before_state_mismatch_and_discards_snapshot(self) -> None:
        _, record = self.make_patch()
        patch = self.changed_patch(
            record,
            lambda value: value["changes"][1]["before"].update(size_bytes=999),
        )
        snapshot = self.fresh_snapshot()
        root = snapshot.root

        with self.assertRaisesRegex(PatchError, "before state"):
            PatchApplier().apply(snapshot, patch, self.store)

        self.assertTrue(snapshot.closed)
        self.assertFalse(root.exists())

    def test_rejects_non_directory_parent_and_discards_snapshot(self) -> None:
        _, record = self.make_patch()

        def move_under_file(value) -> None:
            value["changes"][0]["path"] = "keep.txt/escape.bin"
            value["changes"].sort(key=lambda change: change["path"])

        patch = self.changed_patch(record, move_under_file)
        snapshot = self.fresh_snapshot()
        root = snapshot.root

        with self.assertRaisesRegex(PatchError, "non-directory parent"):
            PatchApplier().apply(snapshot, patch, self.store)

        self.assertTrue(snapshot.closed)
        self.assertFalse(root.exists())

    def test_rejects_windows_separator_escape_and_discards_snapshot(self) -> None:
        _, record = self.make_patch()

        def move_outside_root(value) -> None:
            value["changes"][0]["path"] = "..\\escape.bin"
            value["changes"].sort(key=lambda change: change["path"])

        patch = self.changed_patch(record, move_outside_root)
        snapshot = self.fresh_snapshot()
        root = snapshot.root
        escaped = root.parent / "escape.bin"

        with self.assertRaisesRegex(PatchError, "relative POSIX path"):
            PatchApplier().apply(snapshot, patch, self.store)

        self.assertTrue(snapshot.closed)
        self.assertFalse(root.exists())
        self.assertFalse(escaped.exists())

    def test_rejects_source_drift_and_discards_snapshot(self) -> None:
        patch, _ = self.make_patch()
        snapshot = self.fresh_snapshot()
        root = snapshot.root
        (self.source / "keep.txt").write_text("source drift\n", encoding="utf-8")

        with self.assertRaisesRegex(PatchError, "staged revision"):
            PatchApplier().apply(snapshot, patch, self.store)

        self.assertTrue(snapshot.closed)
        self.assertFalse(root.exists())

    def test_rejects_result_digest_mismatch_and_discards_partial_tree(self) -> None:
        _, record = self.make_patch()
        patch = self.changed_patch(
            record,
            lambda value: value.update(result_digest="sha256:" + "2" * 64),
        )
        snapshot = self.fresh_snapshot()
        root = snapshot.root

        with self.assertRaisesRegex(PatchError, "result_digest"):
            PatchApplier().apply(snapshot, patch, self.store)

        self.assertTrue(snapshot.closed)
        self.assertFalse(root.exists())
        self.assertEqual((self.source / "modify.txt").read_text(), "before\n")

    def test_rejects_tampered_artifact_and_invalid_limit(self) -> None:
        patch, _ = self.make_patch()
        snapshot = self.fresh_snapshot()
        (self.store.root / patch.path).write_bytes(b"tampered")

        with self.assertRaisesRegex(PatchError, "application failed"):
            PatchApplier().apply(snapshot, patch, self.store)
        with self.assertRaisesRegex(PatchError, "max_patch_bytes"):
            PatchApplier(0)

        self.assertTrue(snapshot.closed)


if __name__ == "__main__":
    unittest.main()
