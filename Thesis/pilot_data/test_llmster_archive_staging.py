from __future__ import annotations

from io import BytesIO
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

sys.path.insert(0, str(Path(__file__).parent))

import llmster_archive_inventory as inventory
import llmster_archive_staging as staging


class LlmsterArchiveStagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.archive = self.root / "fixture.zip"
        self.parent = self.root / "staging"
        self.parent.mkdir()
        self.name = "llmster-0123456789abcdef0123456789abcdef"

    def write_archive(self, members: list[tuple[str | ZipInfo, bytes]]) -> None:
        with ZipFile(self.archive, "w", compression=ZIP_DEFLATED) as target:
            for name, payload in members:
                target.writestr(name, payload)

    @staticmethod
    def raw_name(name: str) -> ZipInfo:
        info = ZipInfo("placeholder")
        info.filename = name
        return info

    def expected(self) -> tuple[dict[str, int | str], inventory.ArchiveInventoryResult]:
        payload = self.archive.read_bytes()
        identity: dict[str, int | str] = {
            "expected_bytes": len(payload),
            "expected_sha256": hashlib.sha256(payload).hexdigest(),
            "expected_sha512": hashlib.sha512(payload).hexdigest(),
        }
        result = inventory.inspect_archive(self.archive, **identity)
        return identity, result

    def stage(self, *, free_values: list[int] | None = None) -> staging.StagingResult:
        identity, inspected = self.expected()
        values = iter(free_values or [10**12, 10**12])
        return staging.stage_archive(
            self.archive,
            staging_parent=self.parent,
            staging_name=self.name,
            expected_inventory_sha256=inspected.canonical_inventory_sha256,
            expected_total_uncompressed_bytes=inspected.total_uncompressed_bytes,
            free_bytes=lambda _path: next(values),
            **identity,
        )

    def stage_inventory_rejection(self) -> None:
        payload = self.archive.read_bytes()
        staging.stage_archive(
            self.archive,
            staging_parent=self.parent,
            staging_name=self.name,
            expected_bytes=len(payload),
            expected_sha256=hashlib.sha256(payload).hexdigest(),
            expected_sha512=hashlib.sha512(payload).hexdigest(),
            expected_inventory_sha256="0" * 64,
            expected_total_uncompressed_bytes=0,
            free_bytes=lambda _path: 10**12,
        )

    @property
    def staged(self) -> Path:
        return self.parent / self.name

    def test_success_streams_content_and_explicit_cleanup_is_owned(self) -> None:
        self.write_archive(
            [
                ("pkg/app.exe", b"MZ-fixture"),
                ("pkg/", b""),
                ("README.md", b"hello"),
            ]
        )
        result = self.stage()
        self.assertEqual(b"MZ-fixture", (self.staged / "pkg" / "app.exe").read_bytes())
        self.assertEqual(3, result.entry_count)
        self.assertEqual(2, result.file_count)
        self.assertEqual(1, result.directory_count)
        self.assertEqual(1, result.signature_candidate_count)
        self.assertEqual(0, result.existing_destination_overwrite_count)
        self.assertEqual(0, result.binary_launch_count)
        self.assertEqual(0, result.installer_invocation_count)
        self.assertEqual(0, result.network_request_count)
        staging.remove_owned_staging(
            self.staged,
            expected_parent=self.parent,
            token=self.name.removeprefix("llmster-"),
            archive_sha256=self.expected()[0]["expected_sha256"],
        )
        self.assertFalse(self.staged.exists())
        self.assertTrue(self.archive.is_file())
        self.assertTrue(self.parent.is_dir())

    def test_record_omits_local_path_and_member_names(self) -> None:
        self.write_archive([("private-name.exe", b"x")])
        record = self.stage().to_record()
        encoded = json.dumps(record, sort_keys=True)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn("private-name.exe", encoded)
        self.assertNotIn("staging_path", record)

    def test_backslash_path_uses_canonical_destination(self) -> None:
        self.write_archive([(self.raw_name("pkg\\tool.node"), b"node")])
        result = self.stage()
        self.assertEqual(b"node", (self.staged / "pkg" / "tool.node").read_bytes())
        expected_paths = hashlib.sha256(b"pkg/tool.node").hexdigest()
        self.assertEqual(expected_paths, result.signature_candidate_paths_sha256)

    def test_existing_child_is_rejected_without_modification(self) -> None:
        self.write_archive([("file.txt", b"x")])
        self.staged.mkdir()
        sentinel = self.staged / "sentinel.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(staging.StagingError, "staging_child_already_exists"):
            self.stage()
        self.assertEqual("keep", sentinel.read_text(encoding="utf-8"))

    def test_insufficient_storage_is_rejected_before_child_creation(self) -> None:
        self.write_archive([("file.txt", b"x")])
        with self.assertRaisesRegex(staging.StagingError, "preflight_storage_reserve_failed"):
            self.stage(free_values=[staging.MINIMUM_FREE_BYTES_AFTER])
        self.assertFalse(self.staged.exists())

    def test_final_reserve_failure_rolls_back_owned_child(self) -> None:
        self.write_archive([("file.txt", b"x")])
        with self.assertRaisesRegex(staging.StagingError, "final_storage_reserve_failed"):
            self.stage(free_values=[10**12, staging.MINIMUM_FREE_BYTES_AFTER - 1])
        self.assertFalse(self.staged.exists())
        self.assertTrue(self.archive.is_file())
        self.assertTrue(self.parent.is_dir())

    def test_traversal_is_rejected_before_child_creation(self) -> None:
        self.write_archive([("../escape.txt", b"x")])
        with self.assertRaisesRegex(staging.StagingError, "archive_inventory_rejected"):
            self.stage_inventory_rejection()
        self.assertFalse(self.staged.exists())
        self.assertFalse((self.root / "escape.txt").exists())

    def test_symlink_is_rejected_before_child_creation(self) -> None:
        link = ZipInfo("link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.write_archive([(link, b"target")])
        with self.assertRaisesRegex(staging.StagingError, "archive_inventory_rejected"):
            self.stage_inventory_rejection()
        self.assertFalse(self.staged.exists())

    def test_case_collision_is_rejected_before_child_creation(self) -> None:
        self.write_archive([("A.txt", b"a"), ("a.txt", b"b")])
        with self.assertRaisesRegex(staging.StagingError, "archive_inventory_rejected"):
            self.stage_inventory_rejection()
        self.assertFalse(self.staged.exists())

    def test_member_read_failure_rolls_back_owned_child(self) -> None:
        self.write_archive([("file.txt", b"content")])
        original_open = ZipFile.open

        def failing_open(archive, name, mode="r", pwd=None, *, force_zip64=False):
            if mode == "r":
                raise OSError("fixture read failure")
            return original_open(archive, name, mode, pwd, force_zip64=force_zip64)

        with patch.object(ZipFile, "open", failing_open):
            with self.assertRaisesRegex(staging.StagingError, "staging_member_write_failed"):
                self.stage()
        self.assertFalse(self.staged.exists())
        self.assertTrue(self.archive.is_file())

    def test_actual_size_mismatch_rolls_back_owned_child(self) -> None:
        self.write_archive([("file.txt", b"content")])
        with patch.object(ZipFile, "open", return_value=BytesIO(b"short")):
            with self.assertRaisesRegex(staging.StagingError, "written_file_size_mismatch"):
                self.stage()
        self.assertFalse(self.staged.exists())

    def test_source_change_after_inventory_is_rejected_before_child_creation(self) -> None:
        self.write_archive([("file.txt", b"content")])
        original_inspect = staging.inspect_archive

        def inspect_then_change(*args, **kwargs):
            result = original_inspect(*args, **kwargs)
            self.archive.write_bytes(self.archive.read_bytes() + b"x")
            return result

        with patch.object(staging, "inspect_archive", side_effect=inspect_then_change):
            with self.assertRaisesRegex(staging.StagingError, "archive_changed_after_inventory"):
                self.stage()
        self.assertFalse(self.staged.exists())
        self.assertTrue(self.parent.is_dir())

    def test_stream_reads_never_exceed_frozen_chunk_size(self) -> None:
        payload = b"content"
        self.write_archive([("file.txt", payload)])
        requested: list[int] = []

        class TrackingBytesIO(BytesIO):
            def read(self, size: int = -1) -> bytes:
                requested.append(size)
                return super().read(size)

        with patch.object(ZipFile, "open", return_value=TrackingBytesIO(payload)):
            self.stage()
        self.assertTrue(requested)
        self.assertTrue(all(size == staging.CHUNK_BYTES for size in requested))

    def test_existing_member_destination_is_not_overwritten(self) -> None:
        self.write_archive([("file.txt", b"archive")])
        original_write_marker = staging._write_marker

        def create_conflict(root: Path, token: str, archive_sha256: str) -> None:
            original_write_marker(root, token, archive_sha256)
            (root / "file.txt").write_bytes(b"existing")

        with patch.object(staging, "_write_marker", side_effect=create_conflict):
            with self.assertRaisesRegex(staging.StagingError, "existing_destination_rejected"):
                self.stage()
        self.assertFalse(self.staged.exists())
        self.assertTrue(self.archive.is_file())
        self.assertTrue(self.parent.is_dir())

    def test_wrong_marker_blocks_public_rollback(self) -> None:
        self.write_archive([("file.txt", b"x")])
        result = self.stage()
        marker = result.staging_path / staging.MARKER_NAME
        marker.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(staging.StagingError, "ownership_marker_mismatch"):
            staging.remove_owned_staging(
                result.staging_path,
                expected_parent=self.parent,
                token=self.name.removeprefix("llmster-"),
                archive_sha256=self.expected()[0]["expected_sha256"],
            )
        self.assertTrue(result.staging_path.is_dir())

    def test_missing_marker_blocks_public_rollback(self) -> None:
        self.write_archive([("file.txt", b"x")])
        result = self.stage()
        (result.staging_path / staging.MARKER_NAME).unlink()
        with self.assertRaisesRegex(staging.StagingError, "ownership_marker_missing_or_invalid"):
            staging.remove_owned_staging(
                result.staging_path,
                expected_parent=self.parent,
                token=self.name.removeprefix("llmster-"),
                archive_sha256=self.expected()[0]["expected_sha256"],
            )
        self.assertTrue(result.staging_path.is_dir())

    def test_invalid_name_and_archive_inside_parent_are_rejected(self) -> None:
        self.write_archive([("file.txt", b"x")])
        identity, inspected = self.expected()
        common = {
            "staging_parent": self.parent,
            "expected_inventory_sha256": inspected.canonical_inventory_sha256,
            "expected_total_uncompressed_bytes": inspected.total_uncompressed_bytes,
            **identity,
        }
        with self.assertRaisesRegex(staging.StagingError, "staging_name_invalid"):
            staging.stage_archive(self.archive, staging_name="unsafe", **common)
        inside = self.parent / "fixture.zip"
        inside.write_bytes(self.archive.read_bytes())
        with self.assertRaisesRegex(staging.StagingError, "archive_must_be_outside"):
            staging.stage_archive(inside, staging_name=self.name, **common)

    def test_storage_policy_cannot_be_weakened(self) -> None:
        self.write_archive([("file.txt", b"x")])
        identity, inspected = self.expected()
        with self.assertRaisesRegex(staging.StagingError, "minimum_free_bytes_after_policy_drift"):
            staging.stage_archive(
                self.archive,
                staging_parent=self.parent,
                staging_name=self.name,
                expected_inventory_sha256=inspected.canonical_inventory_sha256,
                expected_total_uncompressed_bytes=inspected.total_uncompressed_bytes,
                minimum_free_bytes_after=0,
                **identity,
            )

    def test_module_has_no_process_network_or_install_surface(self) -> None:
        source = Path(staging.__file__).read_text(encoding="utf-8")
        forbidden = ("subprocess", "socket", "requests", "urllib", "os.system", "startfile")
        for token in forbidden:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
