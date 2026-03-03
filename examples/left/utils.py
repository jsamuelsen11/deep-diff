"""Shared utility functions."""

from __future__ import annotations


def format_name(first: str, last: str) -> str:
    """Format a full name from parts."""
    return f"{first.strip()} {last.strip()}"


def clamp(value: int, low: int, high: int) -> int:
    """Clamp a value to the given range."""
    return max(low, min(high, value))


def truncate(text: str, max_length: int = 80) -> str:
    """Truncate text with an ellipsis if it exceeds max_length."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
