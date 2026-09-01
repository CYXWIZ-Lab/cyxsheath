"""Normalize a comma-separated feature-flag list."""


def normalize_feature_flags(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part]
