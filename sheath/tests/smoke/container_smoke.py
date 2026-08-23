"""Minimal observable checks for the first disposable-container smoke run."""

from __future__ import annotations

import json
from pathlib import Path
import socket


def main() -> int:
    write_blocked = False
    unexpected = Path(__file__).with_name("unexpected-write.txt")
    try:
        unexpected.write_text("sandbox write escaped", encoding="utf-8")
    except OSError:
        write_blocked = True

    with socket.socket() as connection:
        connection.settimeout(0.25)
        network_blocked = connection.connect_ex(("1.1.1.1", 53)) != 0

    result = {
        "network_blocked": network_blocked,
        "workspace_write_blocked": write_blocked,
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if all(result.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
