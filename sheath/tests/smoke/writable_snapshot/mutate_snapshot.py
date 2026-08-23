"""Mutate only the staged workspace mounted by the Docker smoke runner."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    seed = root / "seed.txt"
    generated = root / "generated.txt"
    before = seed.read_text(encoding="utf-8")
    seed.write_text("changed\n", encoding="utf-8")
    generated.write_text("generated\n", encoding="utf-8")
    result = {
        "created_file": generated.is_file(),
        "seed_changed": seed.read_text(encoding="utf-8") == "changed\n",
        "seed_was_original": before == "original\n",
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if all(result.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
