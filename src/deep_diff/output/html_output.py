"""HTML export renderer with GitHub-inspired styling."""

from __future__ import annotations

import html
import sys
from typing import TYPE_CHECKING

from deep_diff.core.models import ChangeType, DiffDepth, FileStatus

if TYPE_CHECKING:
    from typing import TextIO

    from deep_diff.core.models import DiffResult, DiffStats, FileComparison

_STATUS_LABEL: dict[FileStatus, tuple[str, str]] = {
    FileStatus.added: ("added", "+"),
    FileStatus.removed: ("removed", "-"),
    FileStatus.modified: ("modified", "~"),
    FileStatus.identical: ("identical", " "),
}

_CUSTOM_CSS = """\
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    max-width: 960px;
    margin: 0 auto;
    padding: 24px;
    color: #1f2328;
    background: #fff;
}
h1 { font-size: 1.5em; border-bottom: 1px solid #d1d9e0; padding-bottom: 8px; }
h2 { font-size: 1.2em; margin-top: 24px; }
table.diff-table {
    width: 100%;
    border-collapse: collapse;
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
    font-size: 12px;
    margin-bottom: 16px;
}
table.diff-table th, table.diff-table td {
    padding: 4px 8px;
    border: 1px solid #d1d9e0;
    text-align: left;
}
table.diff-table th { background: #f6f8fa; font-weight: 600; }
.status-added { color: #1a7f37; }
.status-removed { color: #cf222e; }
.status-modified { color: #9a6700; }
.status-identical { color: #656d76; }
.file-header {
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 12px;
    background: #f6f8fa;
    border: 1px solid #d1d9e0;
    border-radius: 6px 6px 0 0;
    margin-top: 16px;
}
.diff-block {
    border: 1px solid #d1d9e0;
    border-top: none;
    border-radius: 0 0 6px 6px;
    overflow: auto;
    margin-bottom: 16px;
}
.diff-block pre {
    margin: 0;
    padding: 8px 12px;
    font-size: 12px;
    line-height: 1.5;
}
.file-label {
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
    font-size: 13px;
    padding: 4px 0;
}
table.stats-table {
    border-collapse: collapse;
    font-size: 14px;
    margin: 16px 0;
}
table.stats-table th, table.stats-table td {
    padding: 6px 16px;
    border: 1px solid #d1d9e0;
    text-align: left;
}
table.stats-table th { background: #f6f8fa; font-weight: 600; }
.diff-line { white-space: pre; }
.diff-line-delete { background: #ffebe9; color: #cf222e; white-space: pre; }
.diff-line-insert { background: #dafbe1; color: #1a7f37; white-space: pre; }
.diff-line-hunk { color: #6639ba; font-weight: 600; white-space: pre; }
"""


def _truncate_hash(hex_digest: str | None, *, length: int = 8) -> str:
    """Truncate a hex digest for display, or return dash for None."""
    if hex_digest is None:
        return "-"
    return hex_digest[:length]


class HtmlRenderer:
    """Renders diff results as a standalone HTML document.

    Uses Pygments DiffLexer for syntax highlighting of text-depth diffs
    with GitHub-inspired CSS styling.

    Output modes:
    - render(): Full diff result as HTML
    - render_stats(): Summary statistics as HTML
    """

    def __init__(self, output: TextIO | None = None, *, title: str = "deep-diff") -> None:
        """Initialize with an optional output stream.

        Args:
            output: Text stream for HTML output. Defaults to sys.stdout.
            title: HTML document title.
        """
        self._output = output or sys.stdout
        self._title = title

    def render(self, result: DiffResult) -> None:
        """Render the diff result as a standalone HTML document."""
        heading = (
            f"<h1>{html.escape(result.left_root.name)} vs "
            f"{html.escape(result.right_root.name)}</h1>"
        )

        if result.depth == DiffDepth.structure:
            body = heading + self._build_structure_html(result)
        elif result.depth == DiffDepth.content:
            body = heading + self._build_content_html(result)
        elif result.depth == DiffDepth.text:
            body = heading + self._build_text_html(result)
        else:
            msg = f"Unsupported depth for rendering: '{result.depth}'"
            raise NotImplementedError(msg)

        self._output.write(self._build_document(body))

    def render_stats(self, stats: DiffStats) -> None:
        """Render summary statistics as a standalone HTML document."""
        body = "<h1>Diff Summary</h1>" + self._build_stats_html(stats)
        self._output.write(self._build_document(body))

    def _build_document(self, body: str) -> str:
        """Wrap body content in a full HTML document with embedded CSS."""
        return (
            "<!DOCTYPE html>\n"
            f'<html lang="en">\n<head>\n'
            f'<meta charset="utf-8">\n'
            f"<title>{html.escape(self._title)}</title>\n"
            f"<style>\n{_CUSTOM_CSS}\n</style>\n"
            f"</head>\n<body>\n{body}\n</body>\n</html>\n"
        )

    def _build_structure_html(self, result: DiffResult) -> str:
        """Build HTML table for structure-depth results."""
        rows = ""
        for comp in result.comparisons:
            css_class, prefix = _STATUS_LABEL[comp.status]
            escaped_path = html.escape(comp.relative_path)
            rows += (
                f"<tr>"
                f"<td>{escaped_path}</td>"
                f'<td class="status-{css_class}">{prefix} {css_class}</td>'
                f"</tr>\n"
            )

        return (
            '<table class="diff-table">\n'
            "<thead><tr><th>File</th><th>Status</th></tr></thead>\n"
            f"<tbody>\n{rows}</tbody>\n"
            "</table>\n"
        )

    def _build_content_html(self, result: DiffResult) -> str:
        """Build HTML table for content-depth results with hashes."""
        rows = ""
        for comp in result.comparisons:
            css_class, prefix = _STATUS_LABEL[comp.status]
            escaped_path = html.escape(comp.relative_path)
            left_hash = html.escape(_truncate_hash(comp.content_hash_left))
            right_hash = html.escape(_truncate_hash(comp.content_hash_right))
            rows += (
                f"<tr>"
                f"<td>{escaped_path}</td>"
                f'<td class="status-{css_class}">{prefix} {css_class}</td>'
                f"<td><code>{left_hash}</code></td>"
                f"<td><code>{right_hash}</code></td>"
                f"</tr>\n"
            )

        return (
            '<table class="diff-table">\n'
            "<thead><tr>"
            "<th>File</th><th>Status</th><th>Left Hash</th><th>Right Hash</th>"
            "</tr></thead>\n"
            f"<tbody>\n{rows}</tbody>\n"
            "</table>\n"
        )

    def _build_text_html(self, result: DiffResult) -> str:
        """Build HTML for text-depth results with Pygments-highlighted diffs."""
        parts: list[str] = []

        for comp in result.comparisons:
            css_class, prefix = _STATUS_LABEL[comp.status]
            escaped_path = html.escape(comp.relative_path)

            if comp.status == FileStatus.identical:
                parts.append(
                    f'<div class="file-label status-{css_class}">'
                    f"  {escaped_path} (identical)</div>\n"
                )
            elif comp.status == FileStatus.added:
                parts.append(
                    f'<div class="file-label status-{css_class}">'
                    f"{prefix} {escaped_path} (added)</div>\n"
                )
            elif comp.status == FileStatus.removed:
                parts.append(
                    f'<div class="file-label status-{css_class}">'
                    f"{prefix} {escaped_path} (removed)</div>\n"
                )
            elif comp.hunks:
                parts.append(self._render_diff_block(comp))
            else:
                parts.append(
                    f'<div class="file-label status-{css_class}">'
                    f"{prefix} {escaped_path} (binary, modified)</div>\n"
                )

        return "".join(parts)

    def _render_diff_block(self, comp: FileComparison) -> str:
        """Render a modified file's hunks as a color-coded diff block."""
        similarity_label = ""
        if comp.similarity is not None:
            similarity_label = f" ({comp.similarity:.0%} similar)"

        css_class, prefix = _STATUS_LABEL[comp.status]
        escaped_path = html.escape(comp.relative_path)
        header = (
            f'<div class="file-header status-{css_class}">'
            f"{prefix} {escaped_path}{html.escape(similarity_label)}</div>\n"
        )

        diff_html = self._format_diff_html(comp)
        block = f'<div class="diff-block"><pre>{diff_html}</pre></div>\n'
        return header + block

    @staticmethod
    def _format_diff_html(comp: FileComparison) -> str:
        """Convert FileComparison hunks to color-coded HTML diff lines."""
        parts: list[str] = []

        for hunk in comp.hunks:
            hunk_header = html.escape(
                f"@@ -{hunk.start_left},{hunk.count_left} +{hunk.start_right},{hunk.count_right} @@"
            )
            parts.append(f'<span class="diff-line-hunk">{hunk_header}</span>\n')

            for change in hunk.changes:
                content = change.content
                if content.endswith("\n"):
                    content = content[:-1]
                escaped = html.escape(content)

                if change.change_type == ChangeType.delete:
                    parts.append(f'<span class="diff-line-delete">-{escaped}</span>\n')
                elif change.change_type == ChangeType.insert:
                    parts.append(f'<span class="diff-line-insert">+{escaped}</span>\n')
                else:
                    parts.append(f'<span class="diff-line"> {escaped}</span>\n')

        return "".join(parts)

    @staticmethod
    def _build_stats_html(stats: DiffStats) -> str:
        """Build HTML table for summary statistics."""
        return (
            '<table class="stats-table">\n'
            f"<tr><th>Total Files</th><td>{stats.total_files}</td></tr>\n"
            f'<tr><th>Added</th><td class="status-added">{stats.added}</td></tr>\n'
            f'<tr><th>Removed</th><td class="status-removed">{stats.removed}</td></tr>\n'
            f'<tr><th>Modified</th><td class="status-modified">{stats.modified}</td></tr>\n'
            f'<tr><th>Identical</th><td class="status-identical">{stats.identical}</td></tr>\n'
            "</table>\n"
        )
