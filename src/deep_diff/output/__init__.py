"""Public API for deep_diff.output."""

from __future__ import annotations

from deep_diff.output.base import Renderer
from deep_diff.output.rich_output import RichRenderer

__all__ = [
    "Renderer",
    "RichRenderer",
]
