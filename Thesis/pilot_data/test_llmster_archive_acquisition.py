from __future__ import annotations

from contextlib import nullcontext
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

import llmster_archive_acquisition as acquisition


class FakeResponse:
    def __init__(
        self,
        payload: bytes,
        *,
        status: int = 200,
        url: str = acquisition.ARCHIVE_URL,
        content_length: int | None = None,
        non_bytes: bool = False,
    ) -> None:
        self.payload = payload
        self.status = status
        self.url = url
        self.headers = (
            {} if content_length is None else {"Content-Length": str(content_length)}
        )
        self.offset = 0
        self.non_bytes = non_bytes

    def geturl(self) -> str:
        return self.url

    def read(self, size: int = -1) -> bytes:
        if self.non_bytes:
            return "invalid"  # type: ignore[return-value]
        if self.offset >= len(self.payload):
            return b""
        end = len(self.payload) if size < 0 else self.offset + size
        chunk = self.payload[self.offset:end]
        self.offset += len(chunk)
        return chunk


class LlmsterArchiveAcquisitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / ".gitignore").write_text("/.replay_cache/\n", encoding="utf-8")
        self.payload = b"fixture-llmster-archive"
        self.expected = hashlib.sha512(self.payload).hexdigest()

    def destination(self) -> Path:
        return self.root / acquisition.DESTINATION_RELATIVE

    def partial(self) -> Path:
        destination = self.destination()
        return destination.with_name(destination.name + ".partial")

    def opener(self, response: FakeResponse):
        return lambda url, timeout: nullcontext(response)

    def acquire(self, response: FakeResponse, *, free_values: list[int] | None = None):
        values = iter(
            free_values
            or [
                acquisition.MINIMUM_FREE_BYTES_AFTER + acquisition.MAXIMUM_ARCHIVE_BYTES,
                acquisition.MINIMUM_FREE_BYTES_AFTER,
            ]
        )
        with patch.object(acquisition, "EXPECTED_SHA512", self.expected):
            return acquisition.acquire_exact_archive(
                self.root,
                open_response=self.opener(response),
                free_bytes=lambda path: next(values),
            )

    def assert_clean_failure(self, response: FakeResponse, message: str) -> None:
        with self.assertRaisesRegex(acquisition.AcquisitionError, message):
            self.acquire(response)
        self.assertFalse(self.destination().exists())
        self.assertFalse(self.partial().exists())

    def test_verified_stream_is_atomically_placed(self) -> None:
        result = self.acquire(FakeResponse(self.payload, content_length=len(self.payload)))
        self.assertEqual(self.payload, self.destination().read_bytes())
        self.assertEqual(hashlib.sha256(self.payload).hexdigest(), result.sha256)
        self.assertEqual(self.expected, result.sha512)
        self.assertEqual("https", result.final_url_scheme)
        self.assertEqual("llmster.lmstudio.ai", result.final_url_host)
        self.assertTrue(result.partial_absent_after)

    def test_non_exact_final_url_is_rejected(self) -> None:
        self.assert_clean_failure(
            FakeResponse(self.payload, url="https://example.invalid/archive.zip"),
            "archive_url_not_exact",
        )

    def test_non_200_status_is_rejected(self) -> None:
        self.assert_clean_failure(FakeResponse(self.payload, status=503), "http_status_not_200")

    def test_declared_size_above_ceiling_is_rejected(self) -> None:
        self.assert_clean_failure(
            FakeResponse(self.payload, content_length=acquisition.MAXIMUM_ARCHIVE_BYTES + 1),
            "content_length_exceeds_ceiling",
        )

    def test_streamed_size_above_ceiling_is_rejected(self) -> None:
        with patch.object(acquisition, "MAXIMUM_ARCHIVE_BYTES", len(self.payload) - 1):
            self.assert_clean_failure(
                FakeResponse(self.payload), "archive_size_ceiling_exceeded"
            )

    def test_checksum_mismatch_removes_partial(self) -> None:
        with self.assertRaisesRegex(acquisition.AcquisitionError, "archive_sha512_mismatch"):
            acquisition.acquire_exact_archive(
                self.root,
                open_response=self.opener(FakeResponse(self.payload)),
                free_bytes=lambda path: (
                    acquisition.MINIMUM_FREE_BYTES_AFTER
                    + acquisition.MAXIMUM_ARCHIVE_BYTES
                ),
            )
        self.assertFalse(self.partial().exists())

    def test_preflight_storage_reserve_blocks_before_open(self) -> None:
        opened = False

        def forbidden_open(url: str, timeout: float):
            nonlocal opened
            opened = True
            raise AssertionError("network boundary reached")

        with self.assertRaisesRegex(acquisition.AcquisitionError, "preflight_storage"):
            acquisition.acquire_exact_archive(
                self.root,
                open_response=forbidden_open,
                free_bytes=lambda path: 0,
            )
        self.assertFalse(opened)

    def test_final_storage_reserve_failure_removes_partial(self) -> None:
        with self.assertRaisesRegex(acquisition.AcquisitionError, "final_storage_reserve"):
            self.acquire(
                FakeResponse(self.payload),
                free_values=[
                    acquisition.MINIMUM_FREE_BYTES_AFTER
                    + acquisition.MAXIMUM_ARCHIVE_BYTES,
                    acquisition.MINIMUM_FREE_BYTES_AFTER - 1,
                ],
            )
        self.assertFalse(self.partial().exists())

    def test_existing_destination_blocks_without_opening(self) -> None:
        self.destination().parent.mkdir(parents=True)
        self.destination().write_bytes(b"preserve")
        with self.assertRaisesRegex(acquisition.AcquisitionError, "destination_already_exists"):
            self.acquire(FakeResponse(self.payload))
        self.assertEqual(b"preserve", self.destination().read_bytes())

    def test_existing_partial_is_preserved_and_blocks(self) -> None:
        self.partial().parent.mkdir(parents=True)
        self.partial().write_bytes(b"unknown-owner")
        with self.assertRaisesRegex(acquisition.AcquisitionError, "unexpected_partial_exists"):
            self.acquire(FakeResponse(self.payload))
        self.assertEqual(b"unknown-owner", self.partial().read_bytes())

    def test_request_failure_is_normalized_without_artifact(self) -> None:
        def failing_open(url: str, timeout: float):
            raise ConnectionError("fixture")

        with self.assertRaisesRegex(acquisition.AcquisitionError, "archive_request_failed"):
            acquisition.acquire_exact_archive(
                self.root,
                open_response=failing_open,
                free_bytes=lambda path: (
                    acquisition.MINIMUM_FREE_BYTES_AFTER
                    + acquisition.MAXIMUM_ARCHIVE_BYTES
                ),
            )
        self.assertFalse(self.destination().exists())

    def test_non_bytes_response_chunk_is_rejected(self) -> None:
        self.assert_clean_failure(
            FakeResponse(self.payload, non_bytes=True), "response_chunk_not_bytes"
        )

    def test_invalid_timeout_is_rejected_before_open(self) -> None:
        with self.assertRaisesRegex(acquisition.AcquisitionError, "timeout_invalid"):
            acquisition.acquire_exact_archive(self.root, timeout_seconds=0)


if __name__ == "__main__":
    unittest.main()
