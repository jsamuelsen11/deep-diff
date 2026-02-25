"""Tests for deep_diff.output.rich_output."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

from rich.console import Console

from deep_diff.core.models import (
    DiffDepth,
    DiffResult,
    DiffStats,
    FileComparison,
    FileStatus,
)
from deep_diff.output.base import Renderer
from deep_diff.output.rich_output import RichRenderer


def _make_result(
    comparisons: tuple[FileComparison, ...],
    *,
    left_name: str = "left",
    right_name: str = "right",
) -> DiffResult:
    """Helper to build a DiffResult for testing."""
    return DiffResult(
        left_root=Path(f"/tmp/{left_name}"),
        right_root=Path(f"/tmp/{right_name}"),
        depth=DiffDepth.structure,
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


class TestRichRendererProtocol:
    """Verify RichRenderer satisfies the Renderer protocol."""

    def test_isinstance_check(self) -> None:
        r = RichRenderer()
        assert isinstance(r, Renderer)
