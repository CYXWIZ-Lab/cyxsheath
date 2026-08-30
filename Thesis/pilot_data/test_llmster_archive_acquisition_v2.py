from __future__ import annotations

from contextlib import nullcontext
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

import llmster_archive_acquisition as base
import llmster_archive_acquisition_v2 as acquisition


class FakeResponse:
    status = 200
    headers: dict[str, str]

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.offset = 0
        self.headers = {"Content-Length": str(len(payload))}

    def geturl(self) -> str:
        return acquisition.ARCHIVE_URL

    def read(self, size: int = -1) -> bytes:
        if self.offset >= len(self.payload):
            return b""
        end = len(self.payload) if size < 0 else self.offset + size
        chunk = self.payload[self.offset:end]
        self.offset += len(chunk)
        return chunk


class LlmsterArchiveAcquisitionV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / ".gitignore").write_text("/.replay_cache/\n", encoding="utf-8")
        self.payload = b"v2-storage-policy-fixture"

    def destination(self) -> Path:
        return self.root / acquisition.DESTINATION_RELATIVE

    def acquire(self, free_values: list[int]):
        response = FakeResponse(self.payload)
        values = iter(free_values)
        with patch.object(acquisition, "EXPECTED_SHA512", hashlib.sha512(self.payload).hexdigest()):
            return acquisition.acquire_exact_archive(
                self.root,
                open_response=lambda url, timeout: nullcontext(response),
                free_bytes=lambda path: next(values),
            )

    def test_only_storage_policy_differs_from_pinned_base_contract(self) -> None:
        self.assertEqual(base.ARCHIVE_URL, acquisition.ARCHIVE_URL)
        self.assertEqual(base.EXPECTED_SHA512, acquisition.EXPECTED_SHA512)
        self.assertEqual(base.MAXIMUM_ARCHIVE_BYTES, acquisition.MAXIMUM_ARCHIVE_BYTES)
        self.assertEqual(8_589_934_592, acquisition.MINIMUM_FREE_BYTES_AFTER)
        self.assertNotEqual(base.MINIMUM_FREE_BYTES_AFTER, acquisition.MINIMUM_FREE_BYTES_AFTER)

    def test_exact_preflight_and_final_reserves_pass(self) -> None:
        result = self.acquire(
            [
                acquisition.MINIMUM_FREE_BYTES_AFTER + acquisition.MAXIMUM_ARCHIVE_BYTES,
                acquisition.MINIMUM_FREE_BYTES_AFTER,
            ]
        )
        self.assertEqual(self.payload, self.destination().read_bytes())
        self.assertEqual(hashlib.sha512(self.payload).hexdigest(), result.sha512)

    def test_one_byte_below_preflight_blocks_before_request(self) -> None:
        opened = False

        def forbidden_open(url: str, timeout: float):
            nonlocal opened
            opened = True
            raise AssertionError("request boundary reached")

        with self.assertRaisesRegex(acquisition.AcquisitionError, "preflight_storage"):
            acquisition.acquire_exact_archive(
                self.root,
                open_response=forbidden_open,
                free_bytes=lambda path: (
                    acquisition.MINIMUM_FREE_BYTES_AFTER
                    + acquisition.MAXIMUM_ARCHIVE_BYTES
                    - 1
                ),
            )
        self.assertFalse(opened)

    def test_one_byte_below_final_reserve_removes_partial(self) -> None:
        with self.assertRaisesRegex(acquisition.AcquisitionError, "final_storage_reserve"):
            self.acquire(
                [
                    acquisition.MINIMUM_FREE_BYTES_AFTER
                    + acquisition.MAXIMUM_ARCHIVE_BYTES,
                    acquisition.MINIMUM_FREE_BYTES_AFTER - 1,
                ]
            )
        partial = self.destination().with_name(self.destination().name + ".partial")
        self.assertFalse(partial.exists())

    def test_existing_destination_still_fails_before_request(self) -> None:
        self.destination().parent.mkdir(parents=True)
        self.destination().write_bytes(b"preserve")
        with self.assertRaisesRegex(acquisition.AcquisitionError, "destination_already_exists"):
            self.acquire(
                [
                    acquisition.MINIMUM_FREE_BYTES_AFTER
                    + acquisition.MAXIMUM_ARCHIVE_BYTES,
                    acquisition.MINIMUM_FREE_BYTES_AFTER,
                ]
            )
        self.assertEqual(b"preserve", self.destination().read_bytes())


if __name__ == "__main__":
    unittest.main()
