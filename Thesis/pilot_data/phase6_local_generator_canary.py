"""Frozen task and CyxCode configuration for the local-generator canary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from phase6_minimum_poc import PocTask


PILOT_ID = "phase6-local-generator-canary-v2"
MODEL = "lmstudio/cyxsheath-qwen25-coder-7b-q4km"
BASE_URL = "http://host.docker.internal:1235/v1"
DECISION = Path(__file__).parents[1] / "Phase6_Local_Generator_V2_Decision.md"


class LocalCanaryError(ValueError):
    """Raised when the local-canary task or configuration has drifted."""


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise LocalCanaryError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_canary(manifest_path: Path) -> PocTask:
    manifest_path = Path(manifest_path).resolve(strict=True)
    record = json.loads(manifest_path.read_text(encoding="utf-8"))
    _expect(record["schema_version"] == "1.0.0", "schema version drift")
    _expect(record["pilot_id"] == PILOT_ID, "pilot identity drift")
    _expect(record["model"] == MODEL, "model drift")
    _expect(record["decision_sha256"] == _sha256(DECISION), "decision digest drift")
    task_root = manifest_path.parent
    source = (task_root / "source").resolve(strict=True)
    hidden = (task_root / "hidden_tests.py").resolve(strict=True)
    _expect(source.parent == task_root and hidden.parent == task_root, "task path escaped")
    _expect(hidden.is_file() and not hidden.is_relative_to(source), "hidden tests entered source")
    expected_files = record["source_files"]
    actual_files = tuple(sorted(path.name for path in source.iterdir() if path.is_file()))
    _expect(actual_files == tuple(sorted(expected_files)), "source file set drift")
    _expect(not any(path.is_dir() for path in source.iterdir()), "source directory contamination")
    for name, digest in expected_files.items():
        _expect(_sha256(source / name) == digest, f"source digest drift: {name}")
    _expect(_sha256(hidden) == record["hidden_tests_sha256"], "hidden digest drift")
    allowed = tuple(record["allowed_changed_paths"])
    _expect(allowed == ("feature_flags.py",), "allowed path drift")
    request = record["request"]
    _expect(isinstance(request, str) and request.strip(), "request invalid")
    return PocTask(
        task_id=record["task_id"],
        directory=task_root.name,
        request=request,
        source_root=source,
        hidden_script=hidden.read_text(encoding="utf-8"),
        allowed_changed_paths=allowed,
        condition_order=("A",),
    )


def cyxcode_config(api_key: str) -> dict[str, object]:
    """Return the exact authenticated proxy and deny-by-default tool policy."""

    _expect(isinstance(api_key, str) and re.fullmatch(r"[0-9a-f]{64}", api_key) is not None, "proxy token invalid")

    return {
        "autoupdate": False,
        "enabled_providers": ["lmstudio"],
        "share": "disabled",
        "snapshot": False,
        "instructions": [],
        "plugin": [],
        "skills": {"paths": [], "urls": []},
        "mcp": {},
        "permission": {
            "*": "deny",
            "read": "allow",
            "list": "allow",
            "glob": "allow",
            "grep": "allow",
            "edit": "allow",
        },
        "agent": {"build": {"steps": 12, "temperature": 0}},
        "provider": {
            "lmstudio": {
                "name": "CyxSheath local LM Studio",
                "npm": "@ai-sdk/openai-compatible",
                "env": [],
                "models": {
                    "cyxsheath-qwen25-coder-7b-q4km": {
                        "name": "Qwen2.5-Coder-7B-Instruct Q4_K_M",
                        "tool_call": True,
                        "limit": {"context": 8192, "output": 2048},
                    }
                },
                "options": {
                    "apiKey": api_key,
                    "baseURL": BASE_URL,
                    "timeout": 600000,
                    "chunkTimeout": 120000,
                },
            }
        },
    }
