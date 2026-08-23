from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sheath import ArtifactError, ArtifactStore, digest_bytes


class ArtifactStoreTests(unittest.TestCase):
    def test_stores_content_at_a_stable_digest_path(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parents[1]) as temporary:
            store = ArtifactStore(Path(temporary) / "artifacts")

            first = store.store_bytes("stdout", b"tests passed\n")
            second = store.store_bytes("stdout", b"tests passed\n")

            self.assertEqual(first, second)
            self.assertEqual(first.digest, digest_bytes(b"tests passed\n"))
            self.assertEqual(first.size_bytes, 13)
            self.assertTrue((store.root / first.path).is_file())

    def test_reuses_bytes_without_conflating_artifact_kinds(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parents[1]) as temporary:
            store = ArtifactStore(Path(temporary) / "artifacts")

            stdout = store.store_bytes("stdout", b"")
            stderr = store.store_bytes("stderr", b"")

            self.assertNotEqual(stdout.id, stderr.id)
            self.assertEqual(stdout.path, stderr.path)
            self.assertEqual(len(store.artifacts), 2)

    def test_detects_external_byte_mutation(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parents[1]) as temporary:
            store = ArtifactStore(Path(temporary) / "artifacts")
            artifact = store.store_bytes("stdout", b"original")
            (store.root / artifact.path).write_bytes(b"changed")

            with self.assertRaisesRegex(ArtifactError, "integrity check failed"):
                store.get(artifact.id)

    def test_rejects_unknown_kind(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parents[1]) as temporary:
            store = ArtifactStore(Path(temporary) / "artifacts")

            with self.assertRaisesRegex(ArtifactError, "unsupported artifact kind"):
                store.store_bytes("binary_dump", b"content")


if __name__ == "__main__":
    unittest.main()
