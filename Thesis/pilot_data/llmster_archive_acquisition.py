"""Acquire one checksum-pinned llmster archive without installing or executing it."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import shutil
from typing import BinaryIO, Callable, ContextManager, Mapping, Protocol
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


ARCHIVE_NAME = "0.0.21-2-win32-x64.full.zip"
ARCHIVE_URL = f"https://llmster.lmstudio.ai/download/{ARCHIVE_NAME}"
EXPECTED_SHA512 = (
    "ec13183ddc2f56d68b48fc13428e0cdca84c29bfc2b87a7aa2b9befeb7b79a8c"
    "dd3ea5a7c50d6e941fcf43545c8730f8b2bf2665b030b98e5ccfab6a3d43efff"
)
DESTINATION_RELATIVE = Path(".replay_cache/llmster_acquisition") / ARCHIVE_NAME
MAXIMUM_ARCHIVE_BYTES = 1_073_741_824
MINIMUM_FREE_BYTES_AFTER = 34_359_738_368
CHUNK_BYTES = 1_048_576


class AcquisitionError(RuntimeError):
    """Raised when exact archive acquisition violates the frozen contract."""


class BinaryResponse(Protocol):
    status: int
    headers: Mapping[str, str]

    def geturl(self) -> str: ...

    def read(self, size: int = -1) -> bytes: ...


OpenResponse = Callable[[str, float], ContextManager[BinaryResponse]]
FreeBytes = Callable[[Path], int]


@dataclass(frozen=True, slots=True)
class AcquisitionResult:
    http_status: int
    final_url_scheme: str
    final_url_host: str
    exact_bytes: int
    sha256: str
    sha512: str
    free_bytes_after: int
    destination_relative_path: str
    partial_absent_after: bool

    def to_record(self) -> dict[str, int | str | bool]:
        return {
            "http_status": self.http_status,
            "final_url_scheme": self.final_url_scheme,
            "final_url_host": self.final_url_host,
            "exact_bytes": self.exact_bytes,
            "sha256": self.sha256,
            "sha512": self.sha512,
            "free_bytes_after": self.free_bytes_after,
            "destination_relative_path": self.destination_relative_path,
            "partial_absent_after": self.partial_absent_after,
        }


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def _open_exact(url: str, timeout_seconds: float) -> ContextManager[BinaryResponse]:
    request = Request(url, headers={"User-Agent": "cyxsheath-acquisition/1"})
    return build_opener(_RejectRedirects).open(request, timeout=timeout_seconds)


def _free_bytes(path: Path) -> int:
    return shutil.disk_usage(path).free


def _require_repository_root(root: Path) -> None:
    if not isinstance(root, Path) or not root.is_absolute() or not root.is_dir():
        raise AcquisitionError("repository_root_invalid")
    ignore = root / ".gitignore"
    if not ignore.is_file() or "/.replay_cache/" not in ignore.read_text(encoding="utf-8").splitlines():
        raise AcquisitionError("replay_cache_not_git_ignored")


def _require_url(url: str) -> tuple[str, str]:
    parsed = urlsplit(url)
    if (
        url != ARCHIVE_URL
        or parsed.scheme != "https"
        or parsed.hostname != "llmster.lmstudio.ai"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise AcquisitionError("archive_url_not_exact")
    return parsed.scheme, parsed.hostname


def _content_length(headers: Mapping[str, str]) -> int | None:
    raw = headers.get("Content-Length") or headers.get("content-length")
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as error:
        raise AcquisitionError("content_length_invalid") from error
    if value < 0:
        raise AcquisitionError("content_length_invalid")
    return value


def _stream(
    response: BinaryResponse,
    output: BinaryIO,
) -> tuple[int, str, str]:
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    total = 0
    while True:
        chunk = response.read(CHUNK_BYTES)
        if not isinstance(chunk, bytes):
            raise AcquisitionError("response_chunk_not_bytes")
        if not chunk:
            break
        total += len(chunk)
        if total > MAXIMUM_ARCHIVE_BYTES:
            raise AcquisitionError("archive_size_ceiling_exceeded")
        sha256.update(chunk)
        sha512.update(chunk)
        output.write(chunk)
    return total, sha256.hexdigest(), sha512.hexdigest()


def acquire_exact_archive(
    repository_root: Path,
    *,
    timeout_seconds: float = 900,
    open_response: OpenResponse = _open_exact,
    free_bytes: FreeBytes = _free_bytes,
) -> AcquisitionResult:
    """Acquire the frozen archive once; never extract, execute, or install it."""

    _require_repository_root(repository_root)
    if os.name != "nt":
        raise AcquisitionError("windows_target_required")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise AcquisitionError("timeout_invalid")

    destination = repository_root / DESTINATION_RELATIVE
    partial = destination.with_name(destination.name + ".partial")
    if destination.exists():
        raise AcquisitionError("destination_already_exists")
    if partial.exists():
        raise AcquisitionError("unexpected_partial_exists")
    initial_free = free_bytes(repository_root)
    if initial_free < MINIMUM_FREE_BYTES_AFTER + MAXIMUM_ARCHIVE_BYTES:
        raise AcquisitionError("preflight_storage_reserve_failed")

    created_partial = False
    try:
        try:
            response_context = open_response(ARCHIVE_URL, float(timeout_seconds))
        except Exception as error:
            raise AcquisitionError("archive_request_failed") from error

        with response_context as response:
            if isinstance(response.status, bool) or response.status != 200:
                raise AcquisitionError("http_status_not_200")
            scheme, host = _require_url(response.geturl())
            declared = _content_length(response.headers)
            if declared is not None and declared > MAXIMUM_ARCHIVE_BYTES:
                raise AcquisitionError("content_length_exceeds_ceiling")

            destination.parent.mkdir(parents=True, exist_ok=True)
            with partial.open("xb") as output:
                created_partial = True
                exact_bytes, sha256, sha512 = _stream(response, output)
                output.flush()
                os.fsync(output.fileno())

        if sha512 != EXPECTED_SHA512:
            raise AcquisitionError("archive_sha512_mismatch")
        final_free = free_bytes(repository_root)
        if final_free < MINIMUM_FREE_BYTES_AFTER:
            raise AcquisitionError("final_storage_reserve_failed")
        if destination.exists():
            raise AcquisitionError("destination_appeared_during_acquisition")
        os.rename(partial, destination)
        created_partial = False
        return AcquisitionResult(
            http_status=200,
            final_url_scheme=scheme,
            final_url_host=host,
            exact_bytes=exact_bytes,
            sha256=sha256,
            sha512=sha512,
            free_bytes_after=final_free,
            destination_relative_path=DESTINATION_RELATIVE.as_posix(),
            partial_absent_after=not partial.exists(),
        )
    except AcquisitionError:
        raise
    except OSError as error:
        raise AcquisitionError("archive_acquisition_io_failed") from error
    except Exception as error:
        raise AcquisitionError("archive_request_failed") from error
    finally:
        if created_partial and partial.exists():
            try:
                partial.unlink()
            except OSError as error:
                raise AcquisitionError("partial_cleanup_failed") from error
