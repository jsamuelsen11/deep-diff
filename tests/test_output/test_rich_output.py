"""Tests for deep_diff.output.rich_output."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

from rich.console import Console

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
from deep_diff.output.rich_output import RichRenderer


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


def _capture_render(renderer: RichRenderer, result: DiffResult) -> str:
    """Render a result and capture the output as a string."""
    renderer.render(result)
    file = renderer._console.file
    assert isinstance(file, StringIO)
    return file.getvalue()


def _capture_stats(renderer: RichRenderer, stats: DiffStats) -> str:
    """Render stats and capture the output as a string."""
    renderer.render_stats(stats)
    file = renderer._console.file
    assert isinstance(file, StringIO)
    return file.getvalue()


class TestRichRendererInit:
    """Verify RichRenderer constructor."""

    def test_default_console(self) -> None:
        r = RichRenderer()
        assert r._console is not None

    def test_custom_console(self) -> None:
        console = Console(file=StringIO())
        r = RichRenderer(console=console)
        assert r._console is console


class TestRichRendererStructureTree:
    """Verify tree rendering for structure-depth results."""

    def test_empty_result(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        result = _make_result(())
        output = _capture_render(r, result)
        assert "left" in output
        assert "right" in output

    def test_added_file_has_plus_prefix(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        comp = FileComparison(
            relative_path="new.txt",
            status=FileStatus.added,
            left_path=None,
            right_path=Path("/tmp/right/new.txt"),
        )
        result = _make_result((comp,))
        output = _capture_render(r, result)
        assert "+ new.txt" in output

    def test_removed_file_has_minus_prefix(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        comp = FileComparison(
            relative_path="old.txt",
            status=FileStatus.removed,
            left_path=Path("/tmp/left/old.txt"),
            right_path=None,
        )
        result = _make_result((comp,))
        output = _capture_render(r, result)
        assert "- old.txt" in output

    def test_identical_file_has_space_prefix(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        comp = FileComparison(
            relative_path="same.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/same.txt"),
            right_path=Path("/tmp/right/same.txt"),
        )
        result = _make_result((comp,))
        output = _capture_render(r, result)
        assert "same.txt" in output

    def test_modified_file_has_tilde_prefix(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        comp = FileComparison(
            relative_path="changed.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/changed.txt"),
            right_path=Path("/tmp/right/changed.txt"),
        )
        result = _make_result((comp,))
        output = _capture_render(r, result)
        assert "~ changed.txt" in output

    def test_nested_file_creates_directory_node(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        comp = FileComparison(
            relative_path="sub/nested.txt",
            status=FileStatus.added,
            left_path=None,
            right_path=Path("/tmp/right/sub/nested.txt"),
        )
        result = _make_result((comp,))
        output = _capture_render(r, result)
        assert "sub" in output
        assert "+ nested.txt" in output

    def test_deeply_nested_creates_hierarchy(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        comp = FileComparison(
            relative_path="a/b/c/file.txt",
            status=FileStatus.removed,
            left_path=Path("/tmp/left/a/b/c/file.txt"),
            right_path=None,
        )
        result = _make_result((comp,))
        output = _capture_render(r, result)
        assert "a" in output
        assert "b" in output
        assert "c" in output
        assert "- file.txt" in output

    def test_tree_root_label(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        result = _make_result((), left_name="alpha", right_name="beta")
        output = _capture_render(r, result)
        assert "alpha" in output
        assert "beta" in output

    def test_mixed_results(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        comps = (
            FileComparison(
                relative_path="added.txt",
                status=FileStatus.added,
                left_path=None,
                right_path=Path("/tmp/right/added.txt"),
            ),
            FileComparison(
                relative_path="common.txt",
                status=FileStatus.identical,
                left_path=Path("/tmp/left/common.txt"),
                right_path=Path("/tmp/right/common.txt"),
            ),
            FileComparison(
                relative_path="removed.txt",
                status=FileStatus.removed,
                left_path=Path("/tmp/left/removed.txt"),
                right_path=None,
            ),
        )
        result = _make_result(comps)
        output = _capture_render(r, result)
        assert "+ added.txt" in output
        assert "common.txt" in output
        assert "- removed.txt" in output


class TestRichRendererStats:
    """Verify stats rendering."""

    def test_stats_output(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        stats = DiffStats(total_files=5, identical=2, modified=1, added=1, removed=1)
        output = _capture_stats(r, stats)
        assert "5" in output
        assert "2" in output
        assert "added" in output
        assert "removed" in output
        assert "modified" in output
        assert "identical" in output

    def test_stats_zero_counts(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        stats = DiffStats(total_files=0, identical=0, modified=0, added=0, removed=0)
        output = _capture_stats(r, stats)
        assert "0" in output


class TestRichRendererContentTable:
    """Verify content-depth rendering as a summary table."""

    def test_content_table_has_column_headers(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        comp = FileComparison(
            relative_path="file.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/file.txt"),
            right_path=Path("/tmp/right/file.txt"),
            content_hash_left="aabbccdd11223344",
            content_hash_right="aabbccdd11223344",
            similarity=1.0,
        )
        result = _make_result((comp,), depth=DiffDepth.content)
        output = _capture_render(r, result)
        assert "File" in output
        assert "Status" in output
        assert "Left Hash" in output
        assert "Right Hash" in output

    def test_content_table_shows_file_path(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        comp = FileComparison(
            relative_path="config.yaml",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/config.yaml"),
            right_path=Path("/tmp/right/config.yaml"),
            content_hash_left="aabbccdd",
            content_hash_right="aabbccdd",
            similarity=1.0,
        )
        result = _make_result((comp,), depth=DiffDepth.content)
        output = _capture_render(r, result)
        assert "config.yaml" in output

    def test_content_table_modified_status(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        comp = FileComparison(
            relative_path="data.bin",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/data.bin"),
            right_path=Path("/tmp/right/data.bin"),
            content_hash_left="a1b2c3d4e5f60000",
            content_hash_right="99887766aabbccdd",
        )
        result = _make_result((comp,), depth=DiffDepth.content)
        output = _capture_render(r, result)
        assert "modified" in output
        assert "a1b2c3d4" in output
        assert "99887766" in output

    def test_content_table_identical_status(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        comp = FileComparison(
            relative_path="same.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/same.txt"),
            right_path=Path("/tmp/right/same.txt"),
            content_hash_left="deadbeef12345678",
            content_hash_right="deadbeef12345678",
            similarity=1.0,
        )
        result = _make_result((comp,), depth=DiffDepth.content)
        output = _capture_render(r, result)
        assert "identical" in output

    def test_content_table_added_file_shows_dash_for_left(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
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
        assert "aabbccdd" in output
        # Left hash column should render as dash placeholder
        lines = [line for line in output.splitlines() if "new.txt" in line]
        assert len(lines) == 1
        row = lines[0]
        # Dash should appear before the right hash (left hash column)
        dash_pos = row.index("-")
        hash_pos = row.index("aabbccdd")
        assert dash_pos < hash_pos

    def test_content_table_removed_file_shows_dash_for_right(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        comp = FileComparison(
            relative_path="old.txt",
            status=FileStatus.removed,
            left_path=Path("/tmp/left/old.txt"),
            right_path=None,
            content_hash_left="aabbccdd11223344",
            content_hash_right=None,
        )
        result = _make_result((comp,), depth=DiffDepth.content)
        output = _capture_render(r, result)
        assert "aabbccdd" in output
        # Right hash column should render as dash placeholder
        lines = [line for line in output.splitlines() if "old.txt" in line]
        assert len(lines) == 1
        row = lines[0]
        # Dash should appear after the left hash (right hash column)
        hash_pos = row.index("aabbccdd")
        dash_pos = row.rindex("-")
        assert dash_pos > hash_pos

    def test_content_table_hash_truncation(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        long_hash = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2"
        comp = FileComparison(
            relative_path="file.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/file.txt"),
            right_path=Path("/tmp/right/file.txt"),
            content_hash_left=long_hash,
            content_hash_right=long_hash,
            similarity=1.0,
        )
        result = _make_result((comp,), depth=DiffDepth.content)
        output = _capture_render(r, result)
        assert "a1b2c3d4" in output
        # Full hash should NOT appear
        assert long_hash not in output

    def test_content_table_both_hashes_none(self) -> None:
        # Use no_color console so we can inspect cell values without ANSI codes
        console = Console(file=StringIO(), force_terminal=False, no_color=True, width=120)
        r = RichRenderer(console=console)
        comp = FileComparison(
            relative_path="orphan.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/orphan.txt"),
            right_path=Path("/tmp/right/orphan.txt"),
            content_hash_left=None,
            content_hash_right=None,
            similarity=1.0,
        )
        result = _make_result((comp,), depth=DiffDepth.content)
        output = _capture_render(r, result)
        lines = [line for line in output.splitlines() if "orphan.txt" in line]
        assert len(lines) == 1
        # Split the row by the table column separator and check hash cells
        cells = [c.strip() for c in lines[0].split("│")]
        hash_cells = [c for c in cells if c == "-"]
        assert len(hash_cells) >= 2

    def test_content_table_empty_comparisons(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        result = _make_result((), depth=DiffDepth.content)
        output = _capture_render(r, result)
        assert "left" in output
        assert "right" in output

    def test_content_table_title(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        result = _make_result((), left_name="alpha", right_name="beta", depth=DiffDepth.content)
        output = _capture_render(r, result)
        assert "alpha" in output
        assert "beta" in output

    def test_content_table_multiple_files(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        comps = (
            FileComparison(
                relative_path="a.txt",
                status=FileStatus.added,
                left_path=None,
                right_path=Path("/tmp/right/a.txt"),
            ),
            FileComparison(
                relative_path="b.txt",
                status=FileStatus.identical,
                left_path=Path("/tmp/left/b.txt"),
                right_path=Path("/tmp/right/b.txt"),
                content_hash_left="11111111",
                content_hash_right="11111111",
                similarity=1.0,
            ),
            FileComparison(
                relative_path="c.txt",
                status=FileStatus.removed,
                left_path=Path("/tmp/left/c.txt"),
                right_path=None,
            ),
        )
        result = _make_result(comps, depth=DiffDepth.content)
        output = _capture_render(r, result)
        assert "a.txt" in output
        assert "b.txt" in output
        assert "c.txt" in output


class TestRichRendererTextDiff:
    """Verify text-depth rendering as syntax-highlighted diffs."""

    def test_text_header_shows_names(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        result = _make_result((), depth=DiffDepth.text)
        output = _capture_render(r, result)
        assert "left" in output
        assert "right" in output

    def test_text_identical_file_label(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
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
        assert "@@" not in output

    def test_text_added_file_label(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
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

    def test_text_removed_file_label(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
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

    def test_text_modified_with_hunks_shows_panel(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        hunk = Hunk(
            start_left=1,
            count_left=3,
            start_right=1,
            count_right=3,
            changes=(
                TextChange(ChangeType.equal, "line 1\n", line_left=1, line_right=1),
                TextChange(ChangeType.delete, "old line\n", line_left=2, line_right=None),
                TextChange(ChangeType.insert, "new line\n", line_left=None, line_right=2),
                TextChange(ChangeType.equal, "line 3\n", line_left=3, line_right=3),
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
        assert "@@" in output

    def test_text_hunk_header_format(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
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

    def test_text_delete_line_has_minus_prefix(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        hunk = Hunk(
            start_left=1,
            count_left=1,
            start_right=1,
            count_right=0,
            changes=(TextChange(ChangeType.delete, "old line\n", line_left=1, line_right=None),),
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
        assert "-old line" in output

    def test_text_insert_line_has_plus_prefix(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        hunk = Hunk(
            start_left=1,
            count_left=0,
            start_right=1,
            count_right=1,
            changes=(TextChange(ChangeType.insert, "new line\n", line_left=None, line_right=1),),
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
        assert "+new line" in output

    def test_text_equal_line_has_space_prefix(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        hunk = Hunk(
            start_left=1,
            count_left=1,
            start_right=1,
            count_right=1,
            changes=(TextChange(ChangeType.equal, "context\n", line_left=1, line_right=1),),
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
        assert " context" in output

    def test_text_similarity_shown_in_title(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
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

    def test_text_binary_modified_no_hunks(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
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
        assert "@@" not in output

    def test_text_empty_comparisons(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        result = _make_result((), depth=DiffDepth.text)
        output = _capture_render(r, result)
        assert "left" in output
        assert "right" in output

    def test_text_multiple_hunks(self) -> None:
        console = Console(file=StringIO(), force_terminal=True, width=120)
        r = RichRenderer(console=console)
        hunk1 = Hunk(
            start_left=1,
            count_left=2,
            start_right=1,
            count_right=2,
            changes=(
                TextChange(ChangeType.delete, "a\n", line_left=1, line_right=None),
                TextChange(ChangeType.insert, "b\n", line_left=None, line_right=1),
            ),
        )
        hunk2 = Hunk(
            start_left=10,
            count_left=2,
            start_right=10,
            count_right=2,
            changes=(
                TextChange(ChangeType.delete, "c\n", line_left=10, line_right=None),
                TextChange(ChangeType.insert, "d\n", line_left=None, line_right=10),
            ),
        )
        comp = FileComparison(
            relative_path="multi.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/multi.txt"),
            right_path=Path("/tmp/right/multi.txt"),
            hunks=(hunk1, hunk2),
            similarity=0.6,
        )
        result = _make_result((comp,), depth=DiffDepth.text)
        output = _capture_render(r, result)
        assert "@@ -1,2 +1,2 @@" in output
        assert "@@ -10,2 +10,2 @@" in output


class TestRichRendererHelpers:
    """Verify static helper methods."""

    def test_truncate_hash_normal(self) -> None:
        assert RichRenderer._truncate_hash("a1b2c3d4e5f6") == "a1b2c3d4"

    def test_truncate_hash_none(self) -> None:
        assert RichRenderer._truncate_hash(None) == "-"

    def test_truncate_hash_short_string(self) -> None:
        assert RichRenderer._truncate_hash("abc") == "abc"

    def test_truncate_hash_custom_length(self) -> None:
        assert RichRenderer._truncate_hash("a1b2c3d4e5f6", length=4) == "a1b2"

    def test_format_change_line_delete(self) -> None:
        change = TextChange(ChangeType.delete, "old\n", line_left=1, line_right=None)
        assert RichRenderer._format_change_line(change) == "-old\n"

    def test_format_change_line_insert(self) -> None:
        change = TextChange(ChangeType.insert, "new\n", line_left=None, line_right=1)
        assert RichRenderer._format_change_line(change) == "+new\n"

    def test_format_change_line_equal(self) -> None:
        change = TextChange(ChangeType.equal, "ctx\n", line_left=1, line_right=1)
        assert RichRenderer._format_change_line(change) == " ctx\n"

    def test_format_change_line_appends_newline(self) -> None:
        change = TextChange(ChangeType.equal, "no newline", line_left=1, line_right=1)
        assert RichRenderer._format_change_line(change) == " no newline\n"

    def test_change_style_delete(self) -> None:
        assert RichRenderer._change_style(ChangeType.delete) == "red"

    def test_change_style_insert(self) -> None:
        assert RichRenderer._change_style(ChangeType.insert) == "green"

    def test_change_style_equal(self) -> None:
        assert RichRenderer._change_style(ChangeType.equal) == "dim"


class TestRichRendererProtocol:
    """Verify RichRenderer satisfies the Renderer protocol."""

    def test_isinstance_check(self) -> None:
        r = RichRenderer()
        assert isinstance(r, Renderer)
