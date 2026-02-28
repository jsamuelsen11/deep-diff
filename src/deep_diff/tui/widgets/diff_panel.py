"""Detail panel widget showing depth-aware file comparison details."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.widgets import Static

from deep_diff.core.models import ChangeType, DiffDepth, FileStatus

if TYPE_CHECKING:
    from deep_diff.core.models import FileComparison

_STATUS_STYLES: dict[FileStatus, tuple[str, str]] = {
    FileStatus.added: ("green", "+"),
    FileStatus.removed: ("red", "-"),
    FileStatus.modified: ("yellow", "~"),
    FileStatus.identical: ("dim", " "),
}


def _truncate_hash(hex_digest: str | None, *, length: int = 8) -> str:
    """Truncate a hex digest for display, or return dash for None."""
    if hex_digest is None:
        return "-"
    return hex_digest[:length]


class DiffPanel(Static):
    """Panel that shows detail for the selected file comparison."""

    DEFAULT_CSS = """
    DiffPanel {
        width: 2fr;
        display: none;
        overflow-y: auto;
        padding: 1 2;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.last_content: str = ""

    def update_comparison(self, comp: FileComparison, depth: DiffDepth) -> None:
        """Render the comparison detail based on depth."""
        if depth == DiffDepth.structure:
            rendered = self._render_structure(comp)
        elif depth == DiffDepth.content:
            rendered = self._render_content_depth(comp)
        else:
            rendered = self._render_text(comp)
        self.last_content = rendered.plain
        self.update(rendered)

    @staticmethod
    def _render_structure(comp: FileComparison) -> Text:
        """Render structure-depth detail: path and status only."""
        style, prefix = _STATUS_STYLES[comp.status]
        text = Text()
        text.append(f"File: {comp.relative_path}\n", style="bold")
        text.append(f"Status: {prefix} {comp.status.value}\n", style=style)
        if comp.left_path is not None:
            text.append(f"Left:  {comp.left_path}\n")
        else:
            text.append("Left:  (none)\n", style="dim")
        if comp.right_path is not None:
            text.append(f"Right: {comp.right_path}\n")
        else:
            text.append("Right: (none)\n", style="dim")
        return text

    @staticmethod
    def _render_content_depth(comp: FileComparison) -> Text:
        """Render content-depth detail: path, status, and hashes."""
        style, prefix = _STATUS_STYLES[comp.status]
        text = Text()
        text.append(f"File: {comp.relative_path}\n", style="bold")
        text.append(f"Status: {prefix} {comp.status.value}\n", style=style)
        text.append(f"Left Hash:  {_truncate_hash(comp.content_hash_left)}\n")
        text.append(f"Right Hash: {_truncate_hash(comp.content_hash_right)}\n")
        if comp.similarity is not None:
            text.append(f"Similarity: {comp.similarity:.0%}\n")
        return text

    @staticmethod
    def _render_text(comp: FileComparison) -> Text:
        """Render text-depth detail: full unified diff."""
        style, prefix = _STATUS_STYLES[comp.status]
        text = Text()

        # Header with similarity
        header = f"{prefix} {comp.relative_path}"
        if comp.similarity is not None:
            header += f" ({comp.similarity:.0%} similar)"
        text.append(header + "\n", style=style)
        text.append(f"Status: {comp.status.value}\n\n", style=style)

        if comp.status in (FileStatus.identical, FileStatus.added, FileStatus.removed):
            return text

        if not comp.hunks:
            text.append("(binary, modified)\n", style="yellow")
            return text

        for hunk in comp.hunks:
            hunk_header = (
                f"@@ -{hunk.start_left},{hunk.count_left} +{hunk.start_right},{hunk.count_right} @@"
            )
            text.append(hunk_header + "\n", style="cyan")

            for change in hunk.changes:
                content = change.content
                if not content.endswith("\n"):
                    content += "\n"

                if change.change_type == ChangeType.delete:
                    text.append(f"-{content}", style="red")
                elif change.change_type == ChangeType.insert:
                    text.append(f"+{content}", style="green")
                else:
                    text.append(f" {content}", style="dim")

        return text
