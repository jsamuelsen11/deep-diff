"""Tests for deep_diff.output.html_output."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

from deep_diff.core.models import (
    ChangeType,
    DiffDepth,
    DiffResult,
    DiffStats,
    FileComparison,
    FileStatus,
    Hunk,
    TextChange,
)
from deep_diff.output.base import Renderer
from deep_diff.output.html_output import HtmlRenderer


def _make_result(
    comparisons: tuple[FileComparison, ...],
    *,
    left_name: str = "left",
    right_name: str = "right",
    depth: DiffDepth = DiffDepth.structure,
) -> DiffResult:
    """Helper to build a DiffResult for testing."""
    return DiffResult(
        left_root=Path(f"/tmp/{left_name}"),
        right_root=Path(f"/tmp/{right_name}"),
        depth=depth,
        comparisons=comparisons,
        stats=DiffStats.from_comparisons(comparisons),
    )


def _capture_render(renderer: HtmlRenderer, result: DiffResult) -> str:
    """Render a result and capture the output as a string."""
    renderer.render(result)
    output = renderer._output
    assert isinstance(output, StringIO)
    return output.getvalue()


def _capture_stats(renderer: HtmlRenderer, stats: DiffStats) -> str:
    """Render stats and capture the output as a string."""
    renderer.render_stats(stats)
    output = renderer._output
    assert isinstance(output, StringIO)
    return output.getvalue()


class TestHtmlRendererInit:
    """Verify HtmlRenderer constructor."""

    def test_custom_output(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        assert r._output is buf

    def test_custom_title(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf, title="My Diff")
        assert r._title == "My Diff"


class TestHtmlRendererDocument:
    """Verify HTML document structure."""

    def test_output_has_doctype(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        result = _make_result(())
        output = _capture_render(r, result)
        assert "<!DOCTYPE html>" in output

    def test_output_has_html_tags(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        result = _make_result(())
        output = _capture_render(r, result)
        assert "<html" in output
        assert "</html>" in output
        assert "<head>" in output
        assert "<body>" in output
        assert "</body>" in output

    def test_output_has_charset(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        result = _make_result(())
        output = _capture_render(r, result)
        assert 'charset="utf-8"' in output

    def test_output_has_embedded_css(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        result = _make_result(())
        output = _capture_render(r, result)
        assert "<style>" in output
        assert "</style>" in output

    def test_custom_title_in_document(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf, title="Custom Title")
        result = _make_result(())
        output = _capture_render(r, result)
        assert "<title>Custom Title</title>" in output

    def test_heading_shows_root_names(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        result = _make_result((), left_name="alpha", right_name="beta")
        output = _capture_render(r, result)
        assert "alpha" in output
        assert "beta" in output


class TestHtmlRendererStructure:
    """Verify structure-depth HTML rendering."""

    def test_structure_table_has_headers(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        result = _make_result((), depth=DiffDepth.structure)
        output = _capture_render(r, result)
        assert "<th>File</th>" in output
        assert "<th>Status</th>" in output

    def test_added_file_has_status_class(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        comp = FileComparison(
            relative_path="new.txt",
            status=FileStatus.added,
            left_path=None,
            right_path=Path("/tmp/right/new.txt"),
        )
        result = _make_result((comp,))
        output = _capture_render(r, result)
        assert "status-added" in output
        assert "+ added" in output
        assert "new.txt" in output

    def test_removed_file_has_status_class(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        comp = FileComparison(
            relative_path="old.txt",
            status=FileStatus.removed,
            left_path=Path("/tmp/left/old.txt"),
            right_path=None,
        )
        result = _make_result((comp,))
        output = _capture_render(r, result)
        assert "status-removed" in output
        assert "- removed" in output

    def test_modified_file_has_status_class(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        comp = FileComparison(
            relative_path="changed.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/changed.txt"),
            right_path=Path("/tmp/right/changed.txt"),
        )
        result = _make_result((comp,))
        output = _capture_render(r, result)
        assert "status-modified" in output
        assert "~ modified" in output

    def test_identical_file_has_status_class(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        comp = FileComparison(
            relative_path="same.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/same.txt"),
            right_path=Path("/tmp/right/same.txt"),
        )
        result = _make_result((comp,))
        output = _capture_render(r, result)
        assert "status-identical" in output

    def test_file_path_html_escaped(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        comp = FileComparison(
            relative_path="<script>alert('xss')</script>.txt",
            status=FileStatus.added,
            left_path=None,
            right_path=Path("/tmp/right/xss.txt"),
        )
        result = _make_result((comp,))
        output = _capture_render(r, result)
        assert "<script>" not in output
        assert "&lt;script&gt;" in output


class TestHtmlRendererContent:
    """Verify content-depth HTML rendering."""

    def test_content_table_has_hash_columns(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        comp = FileComparison(
            relative_path="f.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/f.txt"),
            right_path=Path("/tmp/right/f.txt"),
            content_hash_left="aabbccdd11223344",
            content_hash_right="aabbccdd11223344",
        )
        result = _make_result((comp,), depth=DiffDepth.content)
        output = _capture_render(r, result)
        assert "<th>Left Hash</th>" in output
        assert "<th>Right Hash</th>" in output

    def test_hashes_truncated(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        comp = FileComparison(
            relative_path="f.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/f.txt"),
            right_path=Path("/tmp/right/f.txt"),
            content_hash_left="a1b2c3d4e5f60000",
            content_hash_right="99887766aabbccdd",
        )
        result = _make_result((comp,), depth=DiffDepth.content)
        output = _capture_render(r, result)
        assert "a1b2c3d4" in output
        assert "99887766" in output
        # Full hash should not appear
        assert "a1b2c3d4e5f60000" not in output

    def test_null_hash_shows_dash(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        comp = FileComparison(
            relative_path="new.txt",
            status=FileStatus.added,
            left_path=None,
            right_path=Path("/tmp/right/new.txt"),
            content_hash_left=None,
            content_hash_right="aabbccdd11223344",
        )
        result = _make_result((comp,), depth=DiffDepth.content)
        output = _capture_render(r, result)
        assert "<code>-</code>" in output
        assert "<code>aabbccdd</code>" in output


class TestHtmlRendererText:
    """Verify text-depth HTML rendering."""

    def test_identical_file_label(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        comp = FileComparison(
            relative_path="same.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/same.txt"),
            right_path=Path("/tmp/right/same.txt"),
            similarity=1.0,
        )
        result = _make_result((comp,), depth=DiffDepth.text)
        output = _capture_render(r, result)
        assert "same.txt" in output
        assert "identical" in output

    def test_added_file_label(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        comp = FileComparison(
            relative_path="new.txt",
            status=FileStatus.added,
            left_path=None,
            right_path=Path("/tmp/right/new.txt"),
        )
        result = _make_result((comp,), depth=DiffDepth.text)
        output = _capture_render(r, result)
        assert "new.txt" in output
        assert "added" in output
        assert "status-added" in output

    def test_removed_file_label(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        comp = FileComparison(
            relative_path="old.txt",
            status=FileStatus.removed,
            left_path=Path("/tmp/left/old.txt"),
            right_path=None,
        )
        result = _make_result((comp,), depth=DiffDepth.text)
        output = _capture_render(r, result)
        assert "old.txt" in output
        assert "removed" in output

    def test_modified_file_has_diff_block(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        hunk = Hunk(
            start_left=1,
            count_left=3,
            start_right=1,
            count_right=3,
            changes=(
                TextChange(ChangeType.equal, "line 1\n", line_left=1, line_right=1),
                TextChange(ChangeType.delete, "old line\n", line_left=2, line_right=None),
                TextChange(ChangeType.insert, "new line\n", line_left=None, line_right=2),
            ),
        )
        comp = FileComparison(
            relative_path="modified.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/modified.txt"),
            right_path=Path("/tmp/right/modified.txt"),
            hunks=(hunk,),
            similarity=0.78,
        )
        result = _make_result((comp,), depth=DiffDepth.text)
        output = _capture_render(r, result)
        assert "modified.txt" in output
        assert "diff-block" in output
        assert "file-header" in output

    def test_hunk_header_shown(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        hunk = Hunk(
            start_left=1,
            count_left=3,
            start_right=1,
            count_right=3,
            changes=(TextChange(ChangeType.equal, "ctx\n", line_left=1, line_right=1),),
        )
        comp = FileComparison(
            relative_path="f.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/f.txt"),
            right_path=Path("/tmp/right/f.txt"),
            hunks=(hunk,),
            similarity=0.9,
        )
        result = _make_result((comp,), depth=DiffDepth.text)
        output = _capture_render(r, result)
        assert "@@ -1,3 +1,3 @@" in output
        assert "diff-line-hunk" in output

    def test_change_lines_have_correct_classes(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        hunk = Hunk(
            start_left=1,
            count_left=3,
            start_right=1,
            count_right=3,
            changes=(
                TextChange(ChangeType.equal, "ctx\n", line_left=1, line_right=1),
                TextChange(ChangeType.delete, "old\n", line_left=2, line_right=None),
                TextChange(ChangeType.insert, "new\n", line_left=None, line_right=2),
            ),
        )
        comp = FileComparison(
            relative_path="f.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/f.txt"),
            right_path=Path("/tmp/right/f.txt"),
            hunks=(hunk,),
            similarity=0.9,
        )
        result = _make_result((comp,), depth=DiffDepth.text)
        output = _capture_render(r, result)
        assert "diff-line-delete" in output
        assert "diff-line-insert" in output
        assert "diff-line" in output  # equal lines use base class

    def test_similarity_shown_in_header(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        hunk = Hunk(
            start_left=1,
            count_left=1,
            start_right=1,
            count_right=1,
            changes=(TextChange(ChangeType.equal, "x\n", line_left=1, line_right=1),),
        )
        comp = FileComparison(
            relative_path="f.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/f.txt"),
            right_path=Path("/tmp/right/f.txt"),
            hunks=(hunk,),
            similarity=0.78,
        )
        result = _make_result((comp,), depth=DiffDepth.text)
        output = _capture_render(r, result)
        assert "78% similar" in output

    def test_binary_modified_no_hunks(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        comp = FileComparison(
            relative_path="image.png",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/image.png"),
            right_path=Path("/tmp/right/image.png"),
            hunks=(),
            similarity=None,
        )
        result = _make_result((comp,), depth=DiffDepth.text)
        output = _capture_render(r, result)
        assert "binary, modified" in output
        assert "image.png" in output

    def test_content_html_escaped(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        hunk = Hunk(
            start_left=1,
            count_left=1,
            start_right=1,
            count_right=1,
            changes=(
                TextChange(
                    ChangeType.delete,
                    "<script>alert('xss')</script>\n",
                    line_left=1,
                    line_right=None,
                ),
            ),
        )
        comp = FileComparison(
            relative_path="f.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/f.txt"),
            right_path=Path("/tmp/right/f.txt"),
            hunks=(hunk,),
            similarity=0.5,
        )
        result = _make_result((comp,), depth=DiffDepth.text)
        output = _capture_render(r, result)
        assert "<script>alert" not in output
        assert "&lt;script&gt;" in output

    def test_empty_comparisons(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        result = _make_result((), depth=DiffDepth.text)
        output = _capture_render(r, result)
        assert "<!DOCTYPE html>" in output


class TestHtmlRendererStats:
    """Verify stats rendering."""

    def test_stats_contains_all_counts(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        stats = DiffStats(total_files=5, identical=2, modified=1, added=1, removed=1)
        output = _capture_stats(r, stats)
        assert ">5<" in output
        assert ">2<" in output
        assert ">1<" in output

    def test_stats_has_labels(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        stats = DiffStats(total_files=5, identical=2, modified=1, added=1, removed=1)
        output = _capture_stats(r, stats)
        assert "Total Files" in output
        assert "Added" in output
        assert "Removed" in output
        assert "Modified" in output
        assert "Identical" in output

    def test_stats_is_valid_html(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        stats = DiffStats(total_files=0, identical=0, modified=0, added=0, removed=0)
        output = _capture_stats(r, stats)
        assert "<!DOCTYPE html>" in output
        assert "</html>" in output

    def test_stats_has_heading(self) -> None:
        buf = StringIO()
        r = HtmlRenderer(output=buf)
        stats = DiffStats(total_files=1, identical=1, modified=0, added=0, removed=0)
        output = _capture_stats(r, stats)
        assert "Diff Summary" in output


class TestHtmlRendererProtocol:
    """Verify HtmlRenderer satisfies the Renderer protocol."""

    def test_isinstance_check(self) -> None:
        r = HtmlRenderer()
        assert isinstance(r, Renderer)
