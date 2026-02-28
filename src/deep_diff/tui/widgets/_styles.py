"""Shared status styles and display helpers for TUI widgets."""

from __future__ import annotations

from deep_diff.core.models import FileStatus

STATUS_STYLES: dict[FileStatus, tuple[str, str]] = {
    FileStatus.added: ("green", "+"),
    FileStatus.removed: ("red", "-"),
    FileStatus.modified: ("yellow", "~"),
    FileStatus.identical: ("dim", " "),
}


def truncate_hash(hex_digest: str | None, *, length: int = 8) -> str:
    """Truncate a hex digest for display, or return dash for None."""
    if hex_digest is None:
        return "-"
    return hex_digest[:length]
