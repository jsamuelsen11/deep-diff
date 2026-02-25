"""Rich console renderer (default output mode)."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from rich.console import Console
from rich.tree import Tree

from deep_diff.core.models import FileStatus

if TYPE_CHECKING:
    from deep_diff.core.models import DiffResult, DiffStats

_STATUS_STYLES: dict[FileStatus, tuple[str, str]] = {
    FileStatus.added: ("green", "+"),
    FileStatus.removed: ("red", "-"),
    FileStatus.modified: ("yellow", "~"),
    FileStatus.identical: ("dim", " "),
}


def _status_style(status: FileStatus) -> tuple[str, str]:
    """Return (rich_style, prefix_char) for a file status."""
    return _STATUS_STYLES[status]


class RichRenderer:
    """Renders diff results as a nested Rich tree with color-coded labels.

    Directory nodes are plain text. Leaf files are colored by status:
    - Added files: green with '+' prefix
    - Removed files: red with '-' prefix
    - Modified files: yellow with '~' prefix
    - Identical files: dim with ' ' prefix
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize with an optional Rich console.

        Args:
            console: Rich Console instance. Defaults to Console() if None.
        """
        self._console = console or Console()

    def render(self, result: DiffResult) -> None:
        """Render the diff result as a nested Rich tree."""
        tree = self._build_tree(result)
        self._console.print(tree)

    def render_stats(self, stats: DiffStats) -> None:
        """Render summary statistics."""
        self._console.print(
            f"[bold]{stats.total_files}[/bold] files compared: "
            f"[green]{stats.added} added[/green], "
            f"[red]{stats.removed} removed[/red], "
            f"[yellow]{stats.modified} modified[/yellow], "
            f"[dim]{stats.identical} identical[/dim]"
        )

    def _build_tree(self, result: DiffResult) -> Tree:
        """Build a nested Rich Tree from the diff result."""
        label = f"[bold]{result.left_root.name}[/bold] vs [bold]{result.right_root.name}[/bold]"
        tree = Tree(label)
        nodes: dict[str, Tree] = {}

        for comp in result.comparisons:
            parts = PurePosixPath(comp.relative_path).parts
            style, prefix = _status_style(comp.status)

            if len(parts) == 1:
                tree.add(f"[{style}]{prefix} {parts[0]}[/{style}]")
            else:
                parent = self._get_or_create_dir(nodes, tree, str(PurePosixPath(*parts[:-1])))
                parent.add(f"[{style}]{prefix} {parts[-1]}[/{style}]")

        return tree

    @staticmethod
    def _get_or_create_dir(nodes: dict[str, Tree], root: Tree, dir_path: str) -> Tree:
        """Get or create a directory node in the tree.

        Creates intermediate directory nodes as needed.

        Args:
            nodes: Cache of already-created directory nodes keyed by path.
            root: The root Tree to attach top-level directories to.
            dir_path: POSIX-style directory path (e.g. "sub/deep").

        Returns:
            The Tree node for the given directory path.
        """
        if dir_path in nodes:
            return nodes[dir_path]

        parts = PurePosixPath(dir_path).parts
        current_path = ""
        parent = root

        for part in parts:
            current_path = str(PurePosixPath(current_path, part)) if current_path else part
            if current_path not in nodes:
                nodes[current_path] = parent.add(f"[bold]{part}[/bold]")
            parent = nodes[current_path]

        return parent
