"""Acquire the pinned llmster archive under the revised storage policy."""

from __future__ import annotations

import math
import os
from pathlib import Path

try:
    from . import llmster_archive_acquisition as _base
except ImportError:  # Direct fixture execution from this directory.
    import llmster_archive_acquisition as _base


ARCHIVE_NAME = _base.ARCHIVE_NAME
ARCHIVE_URL = _base.ARCHIVE_URL
EXPECTED_SHA512 = _base.EXPECTED_SHA512
DESTINATION_RELATIVE = _base.DESTINATION_RELATIVE
MAXIMUM_ARCHIVE_BYTES = _base.MAXIMUM_ARCHIVE_BYTES
MINIMUM_FREE_BYTES_AFTER = 8_589_934_592

AcquisitionError = _base.AcquisitionError
AcquisitionResult = _base.AcquisitionResult
OpenResponse = _base.OpenResponse
FreeBytes = _base.FreeBytes


def acquire_exact_archive(
    repository_root: Path,
    *,
    timeout_seconds: float = 900,
    open_response: OpenResponse = _base._open_exact,
    free_bytes: FreeBytes = _base._free_bytes,
) -> AcquisitionResult:
    """Acquire once with a 1-GiB write ceiling and 8-GiB final reserve."""

    _base._require_repository_root(repository_root)
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
            scheme, host = _base._require_url(response.geturl())
            declared = _base._content_length(response.headers)
            if declared is not None and declared > MAXIMUM_ARCHIVE_BYTES:
                raise AcquisitionError("content_length_exceeds_ceiling")

            destination.parent.mkdir(parents=True, exist_ok=True)
            with partial.open("xb") as output:
                created_partial = True
                exact_bytes, sha256, sha512 = _base._stream(response, output)
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
