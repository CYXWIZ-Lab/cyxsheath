from __future__ import annotations

import hashlib
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZIP_BZIP2, ZIP_DEFLATED, ZipFile, ZipInfo

sys.path.insert(0, str(Path(__file__).parent))

import llmster_archive_inventory as inventory


class LlmsterArchiveInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.archive = self.root / "fixture.zip"

    def write_archive(
        self,
        members: list[tuple[str | ZipInfo, bytes]],
        *,
        compression: int = ZIP_DEFLATED,
    ) -> None:
        with ZipFile(self.archive, "w", compression=compression) as target:
            for name, payload in members:
                target.writestr(name, payload)

    def inspect(self):
        payload = self.archive.read_bytes()
        return inventory.inspect_archive(
            self.archive,
            expected_bytes=len(payload),
            expected_sha256=hashlib.sha256(payload).hexdigest(),
            expected_sha512=hashlib.sha512(payload).hexdigest(),
        )

    def assert_rejected(self, message: str) -> None:
        with self.assertRaisesRegex(inventory.ArchiveInventoryError, message):
            self.inspect()

    def mutate_eocd_field(self, offset: int, value: int, format_code: str = "H") -> None:
        payload = bytearray(self.archive.read_bytes())
        position = payload.rfind(inventory.EOCD_SIGNATURE)
        self.assertGreaterEqual(position, 0)
        struct.pack_into("<" + format_code, payload, position + offset, value)
        self.archive.write_bytes(payload)

    def test_metadata_inventory_never_opens_a_member(self) -> None:
        self.write_archive(
            [("package/", b""), ("package/app.exe", b"MZ-fixture"), ("README.md", b"ok")]
        )
        with patch.object(ZipFile, "open", side_effect=AssertionError("member opened")):
            result = self.inspect()
        self.assertEqual(3, result.entry_count)
        self.assertEqual(2, result.file_count)
        self.assertEqual(1, result.directory_count)
        self.assertEqual(("README.md", "package"), result.top_level_components)
        self.assertEqual(((".exe", 1),), result.sensitive_suffix_counts)
        self.assertEqual(0, result.member_content_read_count)
        self.assertEqual(0, result.extraction_count)

    def test_parent_traversal_is_rejected(self) -> None:
        self.write_archive([("../escape.txt", b"x")])
        self.assert_rejected("member_traversal_segment_rejected")

    def test_absolute_path_is_rejected(self) -> None:
        self.write_archive([("/escape.txt", b"x")])
        self.assert_rejected("member_absolute_path_rejected")

    def test_backslash_path_is_rejected(self) -> None:
        self.write_archive([("..\\escape.txt", b"x")])
        # zipfile normalizes Windows separators before exposing the name; the
        # resulting parent traversal must still fail closed.
        self.assert_rejected("member_traversal_segment_rejected")

    def test_drive_path_is_rejected(self) -> None:
        self.write_archive([("C:escape.txt", b"x")])
        self.assert_rejected("member_absolute_path_rejected")

    def test_windows_device_name_is_rejected(self) -> None:
        self.write_archive([("package/CON.txt", b"x")])
        self.assert_rejected("member_windows_device_name_rejected")

    def test_case_colliding_members_are_rejected(self) -> None:
        self.write_archive([("A.txt", b"a"), ("a.txt", b"b")])
        self.assert_rejected("duplicate_or_case_colliding_member_rejected")

    def test_symlink_member_is_rejected(self) -> None:
        link = ZipInfo("link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.write_archive([(link, b"target")])
        self.assert_rejected("symlink_member_rejected")

    def test_unsupported_compression_is_rejected(self) -> None:
        self.write_archive([("payload.txt", b"x")], compression=ZIP_BZIP2)
        self.assert_rejected("compression_method_rejected")

    def test_entry_count_ceiling_is_checked_before_zipfile(self) -> None:
        self.write_archive([("a.txt", b"a"), ("b.txt", b"b")])
        with patch.object(inventory, "MAXIMUM_ENTRIES", 1):
            self.assert_rejected("entry_count_ceiling_exceeded")

    def test_total_uncompressed_ceiling_is_rejected(self) -> None:
        self.write_archive([("payload.txt", b"12345")])
        with patch.object(inventory, "MAXIMUM_TOTAL_UNCOMPRESSED_BYTES", 4):
            self.assert_rejected("total_uncompressed_ceiling_exceeded")

    def test_compression_ratio_ceiling_is_rejected(self) -> None:
        self.write_archive([("payload.txt", b"0" * 10_000)])
        with patch.object(inventory, "MAXIMUM_COMPRESSION_RATIO_MILLI", 1_000):
            self.assert_rejected("compression_ratio_ceiling_exceeded")

    def test_multi_disk_metadata_is_rejected(self) -> None:
        self.write_archive([("payload.txt", b"x")])
        self.mutate_eocd_field(4, 1)
        self.assert_rejected("multi_disk_zip_rejected")

    def test_zip64_sentinel_is_rejected(self) -> None:
        self.write_archive([("payload.txt", b"x")])
        self.mutate_eocd_field(10, 0xFFFF)
        self.assert_rejected("zip64_rejected")

    def test_identity_drift_is_rejected_before_metadata_parse(self) -> None:
        self.write_archive([("payload.txt", b"x")])
        payload = self.archive.read_bytes()
        with self.assertRaisesRegex(inventory.ArchiveInventoryError, "archive_identity_mismatch"):
            inventory.inspect_archive(
                self.archive,
                expected_bytes=len(payload),
                expected_sha256="0" * 64,
                expected_sha512=hashlib.sha512(payload).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
