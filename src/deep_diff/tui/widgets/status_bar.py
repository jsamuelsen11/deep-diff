"""Status bar widget showing diff summary statistics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Static

if TYPE_CHECKING:
    from deep_diff.core.models import DiffDepth, DiffStats


class StatusBar(Static):
    """Bottom bar displaying file count, status breakdown, and depth."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $boost;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(self, stats: DiffStats, depth: DiffDepth) -> None:
        content = (
            f"{stats.total_files} files | "
            f"[green]{stats.added} added[/green] "
            f"[red]{stats.removed} removed[/red] "
            f"[yellow]{stats.modified} modified[/yellow] "
            f"[dim]{stats.identical} identical[/dim] "
            f"| depth: {depth.value}"
        )
        super().__init__(content)
