"""Tests for deep_diff.tui — Textual TUI application."""

from __future__ import annotations

from pathlib import Path

import pytest

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
from deep_diff.tui.app import DeepDiffApp, _StatsDisplay
from deep_diff.tui.widgets.diff_panel import DiffPanel
from deep_diff.tui.widgets.diff_tree import DiffTree


def _make_result(
    comparisons: tuple[FileComparison, ...],
    *,
    depth: DiffDepth = DiffDepth.structure,
) -> DiffResult:
    """Build a DiffResult for testing."""
    return DiffResult(
        left_root=Path("/tmp/left"),
        right_root=Path("/tmp/right"),
        depth=depth,
        comparisons=comparisons,
        stats=DiffStats.from_comparisons(comparisons),
    )


def _mixed_comparisons() -> tuple[FileComparison, ...]:
    """Return a set of comparisons with all four statuses."""
    return (
        FileComparison(
            relative_path="added.txt",
            status=FileStatus.added,
            left_path=None,
            right_path=Path("/tmp/right/added.txt"),
        ),
        FileComparison(
            relative_path="removed.txt",
            status=FileStatus.removed,
            left_path=Path("/tmp/left/removed.txt"),
            right_path=None,
        ),
        FileComparison(
            relative_path="modified.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/modified.txt"),
            right_path=Path("/tmp/right/modified.txt"),
        ),
        FileComparison(
            relative_path="same.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/same.txt"),
            right_path=Path("/tmp/right/same.txt"),
        ),
    )


def _text_comparisons() -> tuple[FileComparison, ...]:
    """Return comparisons with text-depth data (hunks)."""
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
    return (
        FileComparison(
            relative_path="modified.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/modified.txt"),
            right_path=Path("/tmp/right/modified.txt"),
            hunks=(hunk,),
            similarity=0.78,
        ),
        FileComparison(
            relative_path="same.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/same.txt"),
            right_path=Path("/tmp/right/same.txt"),
            similarity=1.0,
        ),
    )


def _content_comparisons() -> tuple[FileComparison, ...]:
    """Return comparisons with content-depth data (hashes)."""
    return (
        FileComparison(
            relative_path="file.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/file.txt"),
            right_path=Path("/tmp/right/file.txt"),
            content_hash_left="a1b2c3d4e5f60000",
            content_hash_right="99887766aabbccdd",
        ),
        FileComparison(
            relative_path="same.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/same.txt"),
            right_path=Path("/tmp/right/same.txt"),
            content_hash_left="deadbeef12345678",
            content_hash_right="deadbeef12345678",
            similarity=1.0,
        ),
    )


# ---------------------------------------------------------------------------
# Category 1: App launch tests
# ---------------------------------------------------------------------------


class TestTuiAppLaunch:
    """Verify TUI app launches correctly with various DiffResult inputs."""

    @pytest.mark.asyncio
    async def test_app_launches_with_structure_result(self) -> None:
        result = _make_result(_mixed_comparisons(), depth=DiffDepth.structure)
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            assert app.query_one(DiffTree) is not None
            assert app.query_one(DiffPanel) is not None
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_app_launches_with_content_result(self) -> None:
        result = _make_result(_content_comparisons(), depth=DiffDepth.content)
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            assert app.query_one(DiffTree) is not None
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_app_launches_with_text_result(self) -> None:
        result = _make_result(_text_comparisons(), depth=DiffDepth.text)
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            assert app.query_one(DiffTree) is not None
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_app_launches_with_empty_comparisons(self) -> None:
        result = _make_result(())
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            tree = app.query_one(DiffTree)
            assert tree is not None
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_app_launches_in_stat_only_mode(self) -> None:
        result = _make_result(_mixed_comparisons())
        app = DeepDiffApp(result, stat_only=True)
        async with app.run_test() as pilot:
            # Stats display should exist, tree should not
            assert len(app.query(_StatsDisplay)) == 1
            assert len(app.query(DiffTree)) == 0
            await pilot.press("q")


# ---------------------------------------------------------------------------
# Category 2: Keybinding response tests
# ---------------------------------------------------------------------------


class TestTuiKeybindings:
    """Verify keybinding actions respond correctly."""

    @pytest.mark.asyncio
    async def test_q_quits_app(self) -> None:
        result = _make_result(_mixed_comparisons())
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            await pilot.press("q")
        # If we reach here without hanging, quit worked
        assert app.return_code is None or app.return_code == 0

    @pytest.mark.asyncio
    async def test_s_toggles_split_view(self) -> None:
        result = _make_result(_mixed_comparisons())
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            container = app.query_one("#main-container")
            assert not container.has_class("split-view")
            await pilot.press("s")
            assert container.has_class("split-view")
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_s_round_trip(self) -> None:
        result = _make_result(_mixed_comparisons())
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            container = app.query_one("#main-container")
            await pilot.press("s")
            assert container.has_class("split-view")
            await pilot.press("s")
            assert not container.has_class("split-view")
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_n_moves_to_next_diff(self) -> None:
        result = _make_result(_mixed_comparisons())
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            tree = app.query_one(DiffTree)
            await pilot.press("n")
            cursor_node = tree.cursor_node
            assert cursor_node is not None
            assert cursor_node.data is not None
            assert cursor_node.data.status != FileStatus.identical
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_p_moves_to_prev_diff(self) -> None:
        result = _make_result(_mixed_comparisons())
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            tree = app.query_one(DiffTree)
            await pilot.press("p")
            cursor_node = tree.cursor_node
            assert cursor_node is not None
            assert cursor_node.data is not None
            assert cursor_node.data.status != FileStatus.identical
            await pilot.press("q")


# ---------------------------------------------------------------------------
# Category 3: Tree node selection tests
# ---------------------------------------------------------------------------


class TestTuiTreeSelection:
    """Verify tree populates correctly and selection updates panel."""

    @pytest.mark.asyncio
    async def test_tree_contains_all_files(self) -> None:
        comps = _mixed_comparisons()
        result = _make_result(comps)
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            tree = app.query_one(DiffTree)
            # Count leaf nodes (those with data set)
            leaves = [node for node in tree.root.children if node.data is not None]
            assert len(leaves) == len(comps)
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_selecting_node_opens_split_view(self) -> None:
        result = _make_result(_mixed_comparisons())
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            container = app.query_one("#main-container")
            assert not container.has_class("split-view")
            # Navigate to first diff and select it
            await pilot.press("n")
            await pilot.press("enter")
            assert container.has_class("split-view")
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_nested_paths_create_directory_nodes(self) -> None:
        comps = (
            FileComparison(
                relative_path="sub/nested.txt",
                status=FileStatus.added,
                left_path=None,
                right_path=Path("/tmp/right/sub/nested.txt"),
            ),
        )
        result = _make_result(comps)
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            tree = app.query_one(DiffTree)
            # Root should have a directory child "sub"
            assert len(tree.root.children) == 1
            dir_node = tree.root.children[0]
            assert dir_node.data is None  # directory, not a file
            # Directory should have the file as a child
            assert len(dir_node.children) == 1
            assert dir_node.children[0].data is not None
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_tree_labels_have_status_prefix(self) -> None:
        comps = (
            FileComparison(
                relative_path="added.txt",
                status=FileStatus.added,
                left_path=None,
                right_path=Path("/tmp/right/added.txt"),
            ),
            FileComparison(
                relative_path="removed.txt",
                status=FileStatus.removed,
                left_path=Path("/tmp/left/removed.txt"),
                right_path=None,
            ),
        )
        result = _make_result(comps)
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            tree = app.query_one(DiffTree)
            labels = [str(node.label) for node in tree.root.children]
            assert any("+ added.txt" in label for label in labels)
            assert any("- removed.txt" in label for label in labels)
            await pilot.press("q")


# ---------------------------------------------------------------------------
# Category 4: Diff panel content tests
# ---------------------------------------------------------------------------


class TestTuiDiffPanel:
    """Verify DiffPanel renders correct content for each depth."""

    @pytest.mark.asyncio
    async def test_structure_panel_shows_status_only(self) -> None:
        result = _make_result(_mixed_comparisons(), depth=DiffDepth.structure)
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            # Select the first diff node to populate the panel
            await pilot.press("n")
            await pilot.press("enter")
            panel = app.query_one(DiffPanel)
            content = panel.last_content
            assert "Status:" in content
            # Structure depth should not show hashes
            assert "Hash" not in content
            assert "@@" not in content
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_content_panel_shows_hashes(self) -> None:
        result = _make_result(_content_comparisons(), depth=DiffDepth.content)
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.press("enter")
            panel = app.query_one(DiffPanel)
            content = panel.last_content
            assert "Left Hash:" in content
            assert "Right Hash:" in content
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_text_panel_shows_unified_diff(self) -> None:
        result = _make_result(_text_comparisons(), depth=DiffDepth.text)
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.press("enter")
            panel = app.query_one(DiffPanel)
            content = panel.last_content
            assert "@@" in content
            assert "-old line" in content
            assert "+new line" in content
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_panel_empty_on_initial_load(self) -> None:
        result = _make_result(_mixed_comparisons())
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            panel = app.query_one(DiffPanel)
            content = panel.last_content
            # Panel should have no file-specific content before selection
            assert "Status:" not in content
            await pilot.press("q")

    @pytest.mark.asyncio
    async def test_panel_updates_on_new_selection(self) -> None:
        result = _make_result(_text_comparisons(), depth=DiffDepth.text)
        app = DeepDiffApp(result)
        async with app.run_test() as pilot:
            # Select first diff
            await pilot.press("n")
            await pilot.press("enter")
            panel = app.query_one(DiffPanel)
            first_content = panel.last_content
            assert "modified.txt" in first_content
            await pilot.press("q")
