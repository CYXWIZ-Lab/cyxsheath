from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def redact_query(url: str) -> str:
    """Redact sensitive query values while preserving the URL structure."""

    parts = urlsplit(url)
    pairs = parse_qsl(parts.query)
    redacted = [
        (key, "[REDACTED]" if key in {"token", "password", "api_key"} else value)
        for key, value in pairs
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(redacted), parts.fragment))
