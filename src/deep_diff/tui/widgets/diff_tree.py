"""Tree widget displaying the file comparison hierarchy."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from textual.widgets import Tree

from deep_diff.core.models import FileComparison, FileStatus
from deep_diff.tui.widgets._styles import STATUS_STYLES

if TYPE_CHECKING:
    from textual.widgets._tree import TreeNode

    from deep_diff.core.models import DiffResult


class DiffTree(Tree[FileComparison]):
    """Tree widget that displays file comparison results with status markers."""

    DEFAULT_CSS = """
    DiffTree {
        width: 1fr;
        min-width: 20;
        border-right: solid $accent;
    }
    """

    def __init__(self, result: DiffResult) -> None:
        label = f"{result.left_root.name} vs {result.right_root.name}"
        super().__init__(label)
        self._result = result
        self._diff_nodes: list[TreeNode[FileComparison]] = []
        self._current_diff_index: int = -1

    def on_mount(self) -> None:
        """Populate the tree from DiffResult.comparisons."""
        self._build_tree()
        self.root.expand_all()

    def _build_tree(self) -> None:
        """Build tree nodes mirroring RichRenderer._build_tree logic."""
        dir_nodes: dict[str, TreeNode[FileComparison]] = {}

        for comp in self._result.comparisons:
            parts = PurePosixPath(comp.relative_path).parts
            style, prefix = STATUS_STYLES[comp.status]
            label = f"[{style}]{prefix} {parts[-1]}[/{style}]"

            if len(parts) == 1:
                node = self.root.add_leaf(label, data=comp)
            else:
                parent = self._get_or_create_dir(dir_nodes, parts[:-1])
                node = parent.add_leaf(label, data=comp)

            if comp.status != FileStatus.identical:
                self._diff_nodes.append(node)

    def _get_or_create_dir(
        self,
        dir_nodes: dict[str, TreeNode[FileComparison]],
        parts: tuple[str, ...],
    ) -> TreeNode[FileComparison]:
        """Get or create intermediate directory nodes."""
        current_path = ""
        parent: TreeNode[FileComparison] = self.root
        for part in parts:
            current_path = f"{current_path}/{part}" if current_path else part
            if current_path not in dir_nodes:
                dir_nodes[current_path] = parent.add(f"[bold]{part}[/bold]")
            parent = dir_nodes[current_path]
        return parent

    def select_next_diff(self) -> None:
        """Move cursor to the next non-identical file node."""
        if not self._diff_nodes:
            return
        self._current_diff_index = (self._current_diff_index + 1) % len(self._diff_nodes)
        node = self._diff_nodes[self._current_diff_index]
        self.select_node(node)
        self.scroll_to_node(node)

    def select_prev_diff(self) -> None:
        """Move cursor to the previous non-identical file node."""
        if not self._diff_nodes:
            return
        self._current_diff_index = (self._current_diff_index - 1) % len(self._diff_nodes)
        node = self._diff_nodes[self._current_diff_index]
        self.select_node(node)
        self.scroll_to_node(node)
