from __future__ import annotations


def retry_delays(
    max_attempts: int,
    initial_delay: float,
    multiplier: float = 2.0,
    max_delay: float | None = None,
) -> list[float]:
    """Return delays between attempts for an exponential retry schedule."""

    delays: list[float] = []
    delay = initial_delay
    for _ in range(max_attempts - 1):
        delays.append(delay)
        delay *= multiplier
    return delays
