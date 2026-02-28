"""Rich console renderer (default output mode)."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from deep_diff.core.models import ChangeType, DiffDepth, FileStatus

if TYPE_CHECKING:
    from deep_diff.core.models import DiffResult, DiffStats, FileComparison, TextChange

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
    """Renders diff results using depth-appropriate formatting.

    Rendering modes by depth:
    - structure: nested Rich tree with color-coded files
    - content: summary table with file status and truncated hashes
    - text: syntax-highlighted unified diffs in panels

    File status indicators (shared across modes):
    - Added: green with '+' prefix
    - Removed: red with '-' prefix
    - Modified: yellow with '~' prefix
    - Identical: dim with ' ' prefix
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize with an optional Rich console.

        Args:
            console: Rich Console instance. Defaults to Console() if None.
        """
        self._console = console or Console()

    def render(self, result: DiffResult) -> None:
        """Render the diff result using depth-appropriate formatting."""
        if result.depth == DiffDepth.structure:
            tree = self._build_tree(result)
            self._console.print(tree)
        elif result.depth == DiffDepth.content:
            self._render_content(result)
        elif result.depth == DiffDepth.text:
            self._render_text(result)
        else:
            msg = f"Unsupported depth for rendering: '{result.depth}'"
            raise NotImplementedError(msg)

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

    # -- Content depth rendering ------------------------------------------

    def _render_content(self, result: DiffResult) -> None:
        """Render content-depth results as a summary table with hashes."""
        table = Table(
            title=f"{result.left_root.name} vs {result.right_root.name}",
            title_style="bold",
        )
        table.add_column("File", style="bold", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Left Hash", style="dim", no_wrap=True)
        table.add_column("Right Hash", style="dim", no_wrap=True)

        for comp in result.comparisons:
            style, prefix = _status_style(comp.status)
            status_text = f"[{style}]{prefix} {comp.status.value}[/{style}]"
            left_hash = self._truncate_hash(comp.content_hash_left)
            right_hash = self._truncate_hash(comp.content_hash_right)
            table.add_row(comp.relative_path, status_text, left_hash, right_hash)

        self._console.print(table)

    @staticmethod
    def _truncate_hash(hex_digest: str | None, *, length: int = 8) -> str:
        """Truncate a hex digest for display, or return dash for None."""
        if hex_digest is None:
            return "-"
        return hex_digest[:length]

    # -- Text depth rendering ---------------------------------------------

    def _render_text(self, result: DiffResult) -> None:
        """Render text-depth results as syntax-highlighted unified diffs."""
        header = Text(
            f"{result.left_root.name} vs {result.right_root.name}",
            style="bold",
        )
        self._console.print(header)
        self._console.print()

        for comp in result.comparisons:
            if comp.status == FileStatus.identical:
                self._console.print(f"[dim]  {comp.relative_path} (identical)[/dim]")
            elif comp.status == FileStatus.added:
                self._console.print(f"[green]+ {comp.relative_path} (added)[/green]")
            elif comp.status == FileStatus.removed:
                self._console.print(f"[red]- {comp.relative_path} (removed)[/red]")
            elif comp.hunks:
                self._render_diff_panel(comp)
            else:
                self._console.print(f"[yellow]~ {comp.relative_path} (binary, modified)[/yellow]")

    def _render_diff_panel(self, comp: FileComparison) -> None:
        """Render a modified file's hunks as a unified diff in a Panel."""
        diff_text = Text()

        for hunk in comp.hunks:
            hunk_header = (
                f"@@ -{hunk.start_left},{hunk.count_left} +{hunk.start_right},{hunk.count_right} @@"
            )
            diff_text.append(hunk_header + "\n", style="cyan")

            for change in hunk.changes:
                line = self._format_change_line(change)
                style = self._change_style(change.change_type)
                diff_text.append(line, style=style)

        similarity_label = ""
        if comp.similarity is not None:
            similarity_label = f" ({comp.similarity:.0%} similar)"

        panel = Panel(
            diff_text,
            title=f"[yellow]~ {comp.relative_path}{similarity_label}[/yellow]",
            border_style="yellow",
            expand=False,
        )
        self._console.print(panel)

    @staticmethod
    def _format_change_line(change: TextChange) -> str:
        """Format a TextChange as a prefixed diff line."""
        content = change.content
        if not content.endswith("\n"):
            content += "\n"

        if change.change_type == ChangeType.delete:
            return f"-{content}"
        if change.change_type == ChangeType.insert:
            return f"+{content}"
        return f" {content}"

    @staticmethod
    def _change_style(change_type: ChangeType) -> str:
        """Return Rich style string for a change type."""
        if change_type == ChangeType.delete:
            return "red"
        if change_type == ChangeType.insert:
            return "green"
        return "dim"
