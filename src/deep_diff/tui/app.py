"""Textual TUI application for interactive diff viewing."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Static

from deep_diff.tui.widgets.diff_panel import DiffPanel
from deep_diff.tui.widgets.diff_tree import DiffTree
from deep_diff.tui.widgets.status_bar import StatusBar

if TYPE_CHECKING:
    from deep_diff.core.models import DiffResult, FileComparison


class _StatsDisplay(Static):
    """Centered stats display for --stat mode."""

    DEFAULT_CSS = """
    _StatsDisplay {
        width: 100%;
        height: 1fr;
        content-align: center middle;
        text-align: center;
    }
    """

    def __init__(self, result: DiffResult) -> None:
        stats = result.stats
        content = (
            f"[bold]{stats.total_files}[/bold] files compared"
            f" (depth: {result.depth.value})\n\n"
            f"[green]{stats.added} added[/green]  "
            f"[red]{stats.removed} removed[/red]  "
            f"[yellow]{stats.modified} modified[/yellow]  "
            f"[dim]{stats.identical} identical[/dim]"
        )
        super().__init__(content)


class DeepDiffApp(App[None]):
    """Interactive TUI for browsing diff results."""

    CSS_PATH = "styles/app.tcss"

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit"),
        Binding("s", "toggle_view", "Toggle View"),
        Binding("n", "next_diff", "Next Diff"),
        Binding("p", "prev_diff", "Prev Diff"),
    ]

    def __init__(self, result: DiffResult, *, stat_only: bool = False) -> None:
        super().__init__()
        self._result = result
        self._stat_only = stat_only

    def compose(self) -> ComposeResult:
        yield Header()
        if self._stat_only:
            yield _StatsDisplay(self._result)
        else:
            with Horizontal(id="main-container"):
                yield DiffTree(self._result)
                yield DiffPanel()
            yield StatusBar(self._result.stats, self._result.depth)
        yield Footer()

    def on_tree_node_selected(self, event: DiffTree.NodeSelected[FileComparison]) -> None:
        """When a tree node is selected, show its detail in the panel."""
        if event.node.data is None:
            return
        panel = self.query_one(DiffPanel)
        panel.update_comparison(event.node.data, self._result.depth)
        container = self.query_one("#main-container")
        if not container.has_class("split-view"):
            container.add_class("split-view")

    def action_toggle_view(self) -> None:
        """Toggle between full-tree and split tree+detail view."""
        if self._stat_only:
            return
        container = self.query_one("#main-container")
        container.toggle_class("split-view")

    def action_next_diff(self) -> None:
        """Move to the next modified/added/removed file in the tree."""
        if self._stat_only:
            return
        tree = self.query_one(DiffTree)
        tree.select_next_diff()

    def action_prev_diff(self) -> None:
        """Move to the previous modified/added/removed file in the tree."""
        if self._stat_only:
            return
        tree = self.query_one(DiffTree)
        tree.select_prev_diff()
