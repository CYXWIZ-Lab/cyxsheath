from __future__ import annotations


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Return sorted, coalesced inclusive integer ranges."""

    ordered = sorted(ranges)
    merged: list[tuple[int, int]] = []
    for start, end in ordered:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
