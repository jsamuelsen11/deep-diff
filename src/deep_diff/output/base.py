"""Renderer protocol for diff output."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from deep_diff.core.models import DiffResult


@runtime_checkable
class Renderer(Protocol):
    """Protocol for rendering diff results.

    Implementations must provide a render method that takes a DiffResult
    and writes output to the appropriate destination (console, file, etc.).
    """

    def render(self, result: DiffResult) -> None:
        """Render the diff result."""
        ...
