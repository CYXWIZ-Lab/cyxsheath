from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).parents[2] / "sheath" / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from sheath import GenerationRequest, SnapshotStager, build_cyxcode_prompt

from phase6_local_generator_canary import BASE_URL, LocalCanaryError, cyxcode_config, load_canary
from phase6_minimum_poc import build_contract


MANIFEST = Path(__file__).parent / "local_canary_task" / "manifest.json"


class LocalGeneratorCanaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.task = load_canary(MANIFEST)

    def test_task_is_frozen_and_hidden_tests_are_outside_source(self) -> None:
        self.assertEqual(("feature_flags.py",), self.task.allowed_changed_paths)
        self.assertFalse((self.task.source_root / "hidden_tests.py").exists())

    def test_defective_baseline_fails_visible_and_hidden_checks(self) -> None:
        visible = subprocess.run(
            (sys.executable, "-B", "-m", "unittest", "-v"),
            cwd=self.task.source_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        hidden = subprocess.run(
            (sys.executable, "-B", "-c", self.task.hidden_script),
            cwd=self.task.source_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(0, visible.returncode)
        self.assertNotEqual(0, hidden.returncode)

    def test_prompt_contains_request_but_not_hidden_test_source(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parent) as name:
            stager = SnapshotStager(Path(name) / "staging")
            with stager.stage(self.task.source_root) as snapshot:
                contract = build_contract(self.task, snapshot.source_digest)
                prompt = build_cyxcode_prompt(
                    GenerationRequest(contract, contract.repository.revision, snapshot.source_digest, 1)
                ).decode("utf-8")
        self.assertIn(self.task.request, prompt)
        self.assertNotIn("FeatureFlagHiddenTests", prompt)
        self.assertNotIn(self.task.hidden_script, prompt)

    def test_config_uses_authenticated_proxy_and_is_deny_by_default(self) -> None:
        token = "a" * 64
        config = cyxcode_config(token)
        provider = config["provider"]["lmstudio"]
        self.assertEqual(BASE_URL, provider["options"]["baseURL"])
        self.assertEqual(token, provider["options"]["apiKey"])
        self.assertEqual(["lmstudio"], config["enabled_providers"])
        self.assertEqual("deny", config["permission"]["*"])
        self.assertEqual("allow", config["permission"]["edit"])
        for name in ("bash", "webfetch", "websearch", "external_directory", "task", "skill"):
            self.assertNotIn(name, {key for key, value in config["permission"].items() if value == "allow"})
        encoded = json.dumps(config)
        self.assertIn("host.docker.internal:1235", encoded)
        self.assertNotIn("127.0.0.1:1234", encoded)

    def test_proxy_token_must_be_256_bit_lowercase_hex(self) -> None:
        for token in ("", "a" * 63, "A" * 64, "g" * 64):
            with self.subTest(token=token):
                with self.assertRaisesRegex(LocalCanaryError, "proxy token invalid"):
                    cyxcode_config(token)

    def test_source_mutation_is_rejected(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parent) as name:
            copied = Path(name) / "local_canary_task"
            shutil.copytree(MANIFEST.parent, copied)
            target = copied / "source" / "feature_flags.py"
            target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(LocalCanaryError, "source digest drift"):
                load_canary(copied / "manifest.json")


if __name__ == "__main__":
    unittest.main()
