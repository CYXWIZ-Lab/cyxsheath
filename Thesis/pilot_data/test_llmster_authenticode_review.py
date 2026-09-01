from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

import llmster_archive_staging as staging
import llmster_authenticode_review as review


TOKEN = "a" * 32
ARCHIVE_SHA256 = "b" * 64


class LlmsterAuthenticodeReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name).resolve() / "staging"
        self.parent.mkdir()
        self.root = self.parent / f"llmster-{TOKEN}"
        self.root.mkdir()
        staging._write_marker(self.root, TOKEN, ARCHIVE_SHA256)
        self.payloads = {
            "zeta/readme.txt": b"not a candidate",
            "candidates/01.exe": b"valid",
            "candidates/02.DLL": b"unsigned",
            "candidates/03.node": b"mismatch",
            "candidates/04.ps1": b"unknown error",
            "candidates/05.exe": b"untrusted",
            "candidates/06.dll": b"unsupported",
            "candidates/07.node": b"incompatible",
            "candidates/08.ps1": b"future status",
            "candidates/09.exe": b"timeout",
            "candidates/10.dll": b"tool error",
        }
        for name, content in self.payloads.items():
            destination = self.root.joinpath(*name.split("/"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)

    def expectations(self, *, candidate_count: int = 10, candidate_digest: str | None = None) -> review.ReviewExpectations:
        manifest = []
        candidates = []
        for name, content in self.payloads.items():
            manifest.append({"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
            if Path(name).suffix.casefold() in staging.SIGNATURE_SUFFIXES:
                candidates.append(name)
        manifest.sort(key=lambda item: str(item["path"]).encode("utf-8"))
        candidates.sort(key=lambda item: item.encode("utf-8"))
        manifest_digest = hashlib.sha256(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
        paths_digest = hashlib.sha256("\n".join(candidates).encode("utf-8")).hexdigest()
        return review.ReviewExpectations(
            expected_parent=self.parent,
            token=TOKEN,
            archive_sha256=ARCHIVE_SHA256,
            payload_file_count=len(self.payloads),
            payload_bytes=sum(map(len, self.payloads.values())),
            content_manifest_sha256=manifest_digest,
            candidate_count=candidate_count,
            candidate_paths_sha256=candidate_digest or paths_digest,
        )

    @staticmethod
    def observation(path: Path) -> review.InspectionObservation:
        index = int(path.stem)
        statuses = {
            1: "Valid",
            2: "NotSigned",
            3: "HashMismatch",
            4: "UnknownError",
            5: "NotTrusted",
            6: "NotSupportedFileFormat",
            7: "Incompatible",
            8: "FutureStatus",
        }
        if index in statuses:
            return review.InspectionObservation.status(statuses[index])
        if index == 9:
            return review.InspectionObservation.timeout()
        return review.InspectionObservation.tool_error()

    def test_all_statuses_and_operational_outcomes_are_aggregated_privately(self) -> None:
        result = review.review_staged_candidates(self.root, expectations=self.expectations(), inspector=self.observation)
        record = result.to_record()
        self.assertEqual(
            {
                "signed_valid": 1,
                "unsigned": 1,
                "invalid": 2,
                "untrusted": 1,
                "unsupported": 1,
                "incompatible": 1,
                "unknown": 1,
                "timeout": 1,
                "tool_error": 1,
            },
            record["outcome_counts"],
        )
        self.assertEqual(10, record["candidate_count"])
        self.assertEqual(10, record["inspector_call_count"])
        for adapter_owned in ("automatic_retry_count", "target_binary_launch_count", "installer_invocation_count", "network_request_count"):
            self.assertNotIn(adapter_owned, record)
        serialized = json.dumps(record)
        self.assertNotIn("candidates/", serialized)
        self.assertNotIn("FutureStatus", serialized)

    def test_candidate_order_and_classification_digest_are_deterministic(self) -> None:
        observed: list[str] = []

        def inspector(path: Path) -> review.InspectionObservation:
            observed.append(path.relative_to(self.root).as_posix())
            return review.InspectionObservation.status("NotSigned")

        first = review.review_staged_candidates(self.root, expectations=self.expectations(), inspector=inspector)
        second = review.review_staged_candidates(self.root, expectations=self.expectations(), inspector=self.observation)
        self.assertEqual(sorted(observed, key=lambda item: item.encode("utf-8")), observed)
        self.assertNotEqual(first.classification_manifest_sha256, second.classification_manifest_sha256)

    def test_marker_mismatch_rejects_before_inspection(self) -> None:
        (self.root / staging.MARKER_NAME).write_text("{}\n", encoding="utf-8")
        calls: list[Path] = []
        with self.assertRaisesRegex(review.AuthenticodeReviewError, "owned_staging_rejected"):
            review.review_staged_candidates(self.root, expectations=self.expectations(), inspector=lambda path: calls.append(path))
        self.assertEqual([], calls)

    def test_manifest_mismatch_rejects_before_inspection(self) -> None:
        expectations = self.expectations()
        changed = replace(expectations, content_manifest_sha256="0" * 64)
        calls: list[Path] = []
        with self.assertRaisesRegex(review.AuthenticodeReviewError, "content_manifest_mismatch"):
            review.review_staged_candidates(self.root, expectations=changed, inspector=lambda path: calls.append(path))
        self.assertEqual([], calls)

    def test_candidate_count_mismatch_rejects_before_inspection(self) -> None:
        with self.assertRaisesRegex(review.AuthenticodeReviewError, "candidate_count_mismatch"):
            review.review_staged_candidates(self.root, expectations=self.expectations(candidate_count=9), inspector=self.observation)

    def test_candidate_digest_mismatch_rejects_before_inspection(self) -> None:
        with self.assertRaisesRegex(review.AuthenticodeReviewError, "candidate_paths_digest_mismatch"):
            review.review_staged_candidates(self.root, expectations=self.expectations(candidate_digest="0" * 64), inspector=self.observation)

    def test_link_like_payload_is_rejected(self) -> None:
        original = review._is_link_like
        with patch.object(review, "_is_link_like", side_effect=lambda path: path.name == "readme.txt" or original(path)):
            with self.assertRaisesRegex(review.AuthenticodeReviewError, "link_or_junction_rejected"):
                review.review_staged_candidates(self.root, expectations=self.expectations(), inspector=self.observation)

    def test_special_payload_is_rejected(self) -> None:
        original_scandir = review.os.scandir

        class SpecialEntry:
            name = "special"
            path = str(self.root / "special")

            @staticmethod
            def is_dir(*, follow_symlinks: bool) -> bool:
                return False

            @staticmethod
            def is_file(*, follow_symlinks: bool) -> bool:
                return False

        def fake_scandir(path: Path):
            if Path(path) == self.root:
                class SpecialIterator:
                    def __enter__(self):
                        return iter([SpecialEntry()])

                    def __exit__(self, *_: object) -> None:
                        return None

                return SpecialIterator()
            return original_scandir(path)

        with patch.object(review.os, "scandir", side_effect=fake_scandir):
            with self.assertRaisesRegex(review.AuthenticodeReviewError, "special_payload_rejected"):
                review.review_staged_candidates(self.root, expectations=self.expectations(), inspector=self.observation)

    def test_candidate_mutation_during_inspection_is_rejected(self) -> None:
        def mutating(path: Path) -> review.InspectionObservation:
            path.write_bytes(path.read_bytes() + b"changed")
            return review.InspectionObservation.status("Valid")

        with self.assertRaisesRegex(review.AuthenticodeReviewError, "candidate_changed_during_inspection"):
            review.review_staged_candidates(self.root, expectations=self.expectations(), inspector=mutating)

    def test_marker_mutation_during_inspection_is_rejected(self) -> None:
        changed = False

        def mutating(_: Path) -> review.InspectionObservation:
            nonlocal changed
            if not changed:
                (self.root / staging.MARKER_NAME).write_text("{}\n", encoding="utf-8")
                changed = True
            return review.InspectionObservation.status("Valid")

        with self.assertRaisesRegex(review.AuthenticodeReviewError, "owned_staging_changed_during_inspection"):
            review.review_staged_candidates(self.root, expectations=self.expectations(), inspector=mutating)

    def test_invalid_observation_kind_is_rejected(self) -> None:
        with self.assertRaisesRegex(review.AuthenticodeReviewError, "inspector_observation_kind_invalid"):
            review.normalize_observation(review.InspectionObservation(kind="other"))

    def test_operational_observation_cannot_include_signature_status(self) -> None:
        with self.assertRaisesRegex(review.AuthenticodeReviewError, "operational_outcome_has_status"):
            review.normalize_observation(review.InspectionObservation(kind="timeout", signature_status="Valid"))

    def test_inspector_exception_is_not_concealed_as_tool_error(self) -> None:
        def broken(_: Path) -> review.InspectionObservation:
            raise RuntimeError("adapter bug")

        with self.assertRaisesRegex(RuntimeError, "adapter bug"):
            review.review_staged_candidates(self.root, expectations=self.expectations(), inspector=broken)

    def test_policy_source_has_no_platform_process_or_network_surface(self) -> None:
        source = Path(review.__file__).read_text(encoding="utf-8")
        for forbidden in ("subprocess", "powershell", "Get-AuthenticodeSignature", "socket", "requests", "urllib", "startfile"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
