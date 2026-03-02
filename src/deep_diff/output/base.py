"""Renderer protocol for diff output."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from rich.console import RenderableType
    from rich.text import Text

    from deep_diff.core.models import DiffResult, DiffStats


@runtime_checkable
class Renderer(Protocol):
    """Protocol for rendering diff results.

    Implementations must provide a render method that takes a DiffResult
    and writes output to the appropriate destination (console, file, etc.).
    """

    def render(self, result: DiffResult) -> None:
        """Render the diff result."""
        ...

    def render_stats(self, stats: DiffStats) -> None:
        """Render summary statistics."""
        ...


@runtime_checkable
class WatchRenderer(Protocol):
    """Protocol for renderers that support watch-mode live updates.

    Watch mode needs renderable objects (instead of direct console output)
    so that ``rich.live.Live`` can refresh the display in-place.
    """

    def build_renderable(self, result: DiffResult) -> RenderableType:
        """Build a Rich renderable for the diff result."""
        ...

    def build_stats_renderable(self, stats: DiffStats) -> Text:
        """Build a Rich renderable for summary statistics."""
        ...
