"""JSON export renderer."""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import PurePath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TextIO

    from deep_diff.core.models import DiffResult, DiffStats


class _DiffEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Path objects.

    StrEnum values serialize natively as strings. Only Path objects
    require custom handling.
    """

    def default(self, o: object) -> object:
        """Encode Path objects as their string representation."""
        if isinstance(o, PurePath):
            return str(o)
        return super().default(o)


class JsonRenderer:
    """Renders diff results as JSON to a text stream.

    Output modes:
    - render(): Full DiffResult as a JSON object
    - render_stats(): Summary DiffStats only

    Output goes to stdout by default. Pass a custom TextIO for
    file output or testing.
    """

    def __init__(self, output: TextIO | None = None, *, indent: int = 2) -> None:
        """Initialize with an optional output stream.

        Args:
            output: Text stream for JSON output. Defaults to sys.stdout.
            indent: JSON indentation level. Defaults to 2.
        """
        self._output = output or sys.stdout
        self._indent = indent

    def render(self, result: DiffResult) -> None:
        """Serialize the full diff result as JSON."""
        data = dataclasses.asdict(result)
        json.dump(data, self._output, cls=_DiffEncoder, indent=self._indent)
        self._output.write("\n")

    def render_stats(self, stats: DiffStats) -> None:
        """Serialize summary statistics as JSON."""
        data = dataclasses.asdict(stats)
        json.dump(data, self._output, cls=_DiffEncoder, indent=self._indent)
        self._output.write("\n")
