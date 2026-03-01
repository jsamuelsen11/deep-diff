"""Tests for deep_diff.core.snapshot."""

from __future__ import annotations

import json
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
from deep_diff.core.snapshot import (
    SNAPSHOT_VERSION,
    BaselineComparison,
    SnapshotError,
    compare_to_baseline,
    load_snapshot,
    render_baseline,
    save_snapshot,
)


def _make_result(
    comparisons: tuple[FileComparison, ...] = (),
    *,
    left_name: str = "left",
    right_name: str = "right",
    depth: DiffDepth = DiffDepth.structure,
) -> DiffResult:
    """Build a DiffResult for testing."""
    return DiffResult(
        left_root=Path(f"/tmp/{left_name}"),
        right_root=Path(f"/tmp/{right_name}"),
        depth=depth,
        comparisons=comparisons,
        stats=DiffStats.from_comparisons(comparisons),
    )


def _make_text_result() -> DiffResult:
    """Build a DiffResult with hunks and text changes for roundtrip testing."""
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
        similarity=0.78,
    )
    return _make_result((comp,), depth=DiffDepth.text)


# ---------------------------------------------------------------------------
# save_snapshot
# ---------------------------------------------------------------------------


class TestSaveSnapshot:
    """Verify save_snapshot writes valid versioned JSON."""

    def test_creates_valid_json_file(self, tmp_path: Path) -> None:
        result = _make_result()
        out = tmp_path / "snap.json"
        save_snapshot(result, out)
        data = json.loads(out.read_text())
        assert isinstance(data, dict)

    def test_snapshot_version_field(self, tmp_path: Path) -> None:
        result = _make_result()
        out = tmp_path / "snap.json"
        save_snapshot(result, out)
        data = json.loads(out.read_text())
        assert data["snapshot_version"] == SNAPSHOT_VERSION

    def test_result_key_present(self, tmp_path: Path) -> None:
        result = _make_result()
        out = tmp_path / "snap.json"
        save_snapshot(result, out)
        data = json.loads(out.read_text())
        assert "result" in data
        assert "left_root" in data["result"]

    def test_file_ends_with_newline(self, tmp_path: Path) -> None:
        result = _make_result()
        out = tmp_path / "snap.json"
        save_snapshot(result, out)
        assert out.read_text().endswith("\n")


# ---------------------------------------------------------------------------
# load_snapshot
# ---------------------------------------------------------------------------


class TestLoadSnapshot:
    """Verify load_snapshot correctly reconstructs DiffResult."""

    def test_roundtrip_structure_depth(self, tmp_path: Path) -> None:
        comp = FileComparison(
            relative_path="a.txt",
            status=FileStatus.added,
            left_path=None,
            right_path=Path("/tmp/right/a.txt"),
        )
        original = _make_result((comp,), depth=DiffDepth.structure)
        out = tmp_path / "snap.json"
        save_snapshot(original, out)
        loaded = load_snapshot(out)
        assert loaded.depth == DiffDepth.structure
        assert len(loaded.comparisons) == 1
        assert loaded.comparisons[0].relative_path == "a.txt"
        assert loaded.comparisons[0].status == FileStatus.added

    def test_roundtrip_content_depth(self, tmp_path: Path) -> None:
        comp = FileComparison(
            relative_path="data.bin",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/data.bin"),
            right_path=Path("/tmp/right/data.bin"),
            content_hash_left="aabbcc",
            content_hash_right="ddeeff",
        )
        original = _make_result((comp,), depth=DiffDepth.content)
        out = tmp_path / "snap.json"
        save_snapshot(original, out)
        loaded = load_snapshot(out)
        assert loaded.comparisons[0].content_hash_left == "aabbcc"
        assert loaded.comparisons[0].content_hash_right == "ddeeff"

    def test_roundtrip_text_depth(self, tmp_path: Path) -> None:
        original = _make_text_result()
        out = tmp_path / "snap.json"
        save_snapshot(original, out)
        loaded = load_snapshot(out)
        assert loaded.depth == DiffDepth.text
        assert len(loaded.comparisons[0].hunks) == 1
        hunk = loaded.comparisons[0].hunks[0]
        assert hunk.start_left == 1
        assert hunk.count_left == 3
        assert len(hunk.changes) == 3
        assert hunk.changes[0].change_type == ChangeType.equal
        assert hunk.changes[1].change_type == ChangeType.delete
        assert hunk.changes[2].change_type == ChangeType.insert
        assert hunk.changes[1].line_right is None
        assert hunk.changes[2].line_left is None

    def test_roundtrip_null_paths(self, tmp_path: Path) -> None:
        comp = FileComparison(
            relative_path="new.txt",
            status=FileStatus.added,
            left_path=None,
            right_path=None,
        )
        original = _make_result((comp,))
        out = tmp_path / "snap.json"
        save_snapshot(original, out)
        loaded = load_snapshot(out)
        assert loaded.comparisons[0].left_path is None
        assert loaded.comparisons[0].right_path is None

    def test_roundtrip_null_hashes(self, tmp_path: Path) -> None:
        comp = FileComparison(
            relative_path="f.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/f.txt"),
            right_path=Path("/tmp/right/f.txt"),
        )
        original = _make_result((comp,))
        out = tmp_path / "snap.json"
        save_snapshot(original, out)
        loaded = load_snapshot(out)
        assert loaded.comparisons[0].content_hash_left is None
        assert loaded.comparisons[0].content_hash_right is None

    def test_roundtrip_null_similarity(self, tmp_path: Path) -> None:
        comp = FileComparison(
            relative_path="f.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/f.txt"),
            right_path=Path("/tmp/right/f.txt"),
        )
        original = _make_result((comp,))
        out = tmp_path / "snap.json"
        save_snapshot(original, out)
        loaded = load_snapshot(out)
        assert loaded.comparisons[0].similarity is None

    def test_roundtrip_similarity_value(self, tmp_path: Path) -> None:
        comp = FileComparison(
            relative_path="f.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/f.txt"),
            right_path=Path("/tmp/right/f.txt"),
            similarity=0.85,
        )
        original = _make_result((comp,), depth=DiffDepth.text)
        out = tmp_path / "snap.json"
        save_snapshot(original, out)
        loaded = load_snapshot(out)
        assert loaded.comparisons[0].similarity == 0.85

    def test_roundtrip_empty_comparisons(self, tmp_path: Path) -> None:
        original = _make_result(())
        out = tmp_path / "snap.json"
        save_snapshot(original, out)
        loaded = load_snapshot(out)
        assert loaded.comparisons == ()
        assert loaded.stats.total_files == 0

    def test_roundtrip_paths_are_path_objects(self, tmp_path: Path) -> None:
        comp = FileComparison(
            relative_path="a.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/a.txt"),
            right_path=Path("/tmp/right/a.txt"),
        )
        original = _make_result((comp,))
        out = tmp_path / "snap.json"
        save_snapshot(original, out)
        loaded = load_snapshot(out)
        assert isinstance(loaded.left_root, Path)
        assert isinstance(loaded.right_root, Path)
        assert isinstance(loaded.comparisons[0].left_path, Path)

    def test_roundtrip_stats_computed_correctly(self, tmp_path: Path) -> None:
        comps = (
            FileComparison("a.txt", FileStatus.identical, None, None),
            FileComparison("b.txt", FileStatus.modified, None, None),
            FileComparison("c.txt", FileStatus.added, None, None),
            FileComparison("d.txt", FileStatus.removed, None, None),
        )
        original = _make_result(comps)
        out = tmp_path / "snap.json"
        save_snapshot(original, out)
        loaded = load_snapshot(out)
        assert loaded.stats.total_files == 4
        assert loaded.stats.identical == 1
        assert loaded.stats.modified == 1
        assert loaded.stats.added == 1
        assert loaded.stats.removed == 1


# ---------------------------------------------------------------------------
# load_snapshot errors
# ---------------------------------------------------------------------------


class TestLoadSnapshotErrors:
    """Verify load_snapshot raises SnapshotError for invalid inputs."""

    def test_missing_file(self, tmp_path: Path) -> None:
        import pytest

        with pytest.raises(SnapshotError, match="not found"):
            load_snapshot(tmp_path / "nonexistent.json")

    def test_invalid_json(self, tmp_path: Path) -> None:
        import pytest

        bad = tmp_path / "bad.json"
        bad.write_text("not json {{{")
        with pytest.raises(SnapshotError, match="not valid JSON"):
            load_snapshot(bad)

    def test_wrong_version(self, tmp_path: Path) -> None:
        import pytest

        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"snapshot_version": 999, "result": {}}))
        with pytest.raises(SnapshotError, match="Unsupported snapshot version"):
            load_snapshot(bad)

    def test_missing_version(self, tmp_path: Path) -> None:
        import pytest

        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"result": {}}))
        with pytest.raises(SnapshotError, match="Unsupported snapshot version"):
            load_snapshot(bad)

    def test_malformed_result(self, tmp_path: Path) -> None:
        import pytest

        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"snapshot_version": 1, "result": {"left_root": 1}}))
        with pytest.raises(SnapshotError, match="invalid structure"):
            load_snapshot(bad)


# ---------------------------------------------------------------------------
# compare_to_baseline
# ---------------------------------------------------------------------------


class TestCompareToBaseline:
    """Verify compare_to_baseline detects changes between snapshots."""

    def test_no_changes(self) -> None:
        comp = FileComparison("a.txt", FileStatus.identical, None, None)
        baseline = _make_result((comp,))
        current = _make_result((comp,))
        result = compare_to_baseline(baseline, current)
        assert result.status_changes == ()
        assert result.files_only_in_baseline == ()
        assert result.files_only_in_current == ()

    def test_status_change_detected(self) -> None:
        base_comp = FileComparison("a.txt", FileStatus.identical, None, None)
        curr_comp = FileComparison("a.txt", FileStatus.modified, None, None)
        baseline = _make_result((base_comp,))
        current = _make_result((curr_comp,))
        result = compare_to_baseline(baseline, current)
        assert len(result.status_changes) == 1
        assert result.status_changes[0].relative_path == "a.txt"
        assert result.status_changes[0].baseline_status == FileStatus.identical
        assert result.status_changes[0].current_status == FileStatus.modified

    def test_multiple_status_changes(self) -> None:
        base = _make_result(
            (
                FileComparison("a.txt", FileStatus.identical, None, None),
                FileComparison("b.txt", FileStatus.modified, None, None),
            )
        )
        curr = _make_result(
            (
                FileComparison("a.txt", FileStatus.modified, None, None),
                FileComparison("b.txt", FileStatus.identical, None, None),
            )
        )
        result = compare_to_baseline(base, curr)
        assert len(result.status_changes) == 2

    def test_file_only_in_baseline(self) -> None:
        base = _make_result(
            (
                FileComparison("a.txt", FileStatus.identical, None, None),
                FileComparison("b.txt", FileStatus.identical, None, None),
            )
        )
        curr = _make_result((FileComparison("a.txt", FileStatus.identical, None, None),))
        result = compare_to_baseline(base, curr)
        assert result.files_only_in_baseline == ("b.txt",)
        assert result.files_only_in_current == ()

    def test_file_only_in_current(self) -> None:
        base = _make_result((FileComparison("a.txt", FileStatus.identical, None, None),))
        curr = _make_result(
            (
                FileComparison("a.txt", FileStatus.identical, None, None),
                FileComparison("new.txt", FileStatus.added, None, None),
            )
        )
        result = compare_to_baseline(base, curr)
        assert result.files_only_in_baseline == ()
        assert result.files_only_in_current == ("new.txt",)

    def test_status_changes_sorted_by_path(self) -> None:
        base = _make_result(
            (
                FileComparison("z.txt", FileStatus.identical, None, None),
                FileComparison("a.txt", FileStatus.identical, None, None),
            )
        )
        curr = _make_result(
            (
                FileComparison("z.txt", FileStatus.modified, None, None),
                FileComparison("a.txt", FileStatus.modified, None, None),
            )
        )
        result = compare_to_baseline(base, curr)
        paths = [sc.relative_path for sc in result.status_changes]
        assert paths == ["a.txt", "z.txt"]

    def test_combined_all_change_types(self) -> None:
        base = _make_result(
            (
                FileComparison("same.txt", FileStatus.identical, None, None),
                FileComparison("changed.txt", FileStatus.identical, None, None),
                FileComparison("gone.txt", FileStatus.modified, None, None),
            )
        )
        curr = _make_result(
            (
                FileComparison("same.txt", FileStatus.identical, None, None),
                FileComparison("changed.txt", FileStatus.modified, None, None),
                FileComparison("new.txt", FileStatus.added, None, None),
            )
        )
        result = compare_to_baseline(base, curr)
        assert len(result.status_changes) == 1
        assert result.status_changes[0].relative_path == "changed.txt"
        assert result.files_only_in_baseline == ("gone.txt",)
        assert result.files_only_in_current == ("new.txt",)


# ---------------------------------------------------------------------------
# render_baseline
# ---------------------------------------------------------------------------


class TestRenderBaseline:
    """Verify render_baseline produces expected Rich output."""

    def _render_to_string(self, comparison: BaselineComparison) -> str:
        from rich.console import Console

        buf = StringIO()
        console = Console(file=buf, no_color=True, width=120)
        render_baseline(comparison, console=console)
        return buf.getvalue()

    def test_renders_header_with_roots(self) -> None:
        base = _make_result((), left_name="alpha", right_name="beta")
        curr = _make_result((), left_name="gamma", right_name="delta")
        comparison = compare_to_baseline(base, curr)
        output = self._render_to_string(comparison)
        assert "alpha" in output
        assert "beta" in output
        assert "gamma" in output
        assert "delta" in output

    def test_renders_stat_delta_table(self) -> None:
        base = _make_result((FileComparison("a.txt", FileStatus.identical, None, None),))
        curr = _make_result(
            (
                FileComparison("a.txt", FileStatus.modified, None, None),
                FileComparison("b.txt", FileStatus.added, None, None),
            )
        )
        comparison = compare_to_baseline(base, curr)
        output = self._render_to_string(comparison)
        assert "Stats Delta" in output
        assert "total_files" in output

    def test_renders_status_changes(self) -> None:
        base = _make_result((FileComparison("f.txt", FileStatus.identical, None, None),))
        curr = _make_result((FileComparison("f.txt", FileStatus.modified, None, None),))
        comparison = compare_to_baseline(base, curr)
        output = self._render_to_string(comparison)
        assert "changed status" in output
        assert "f.txt" in output

    def test_renders_files_only_in_baseline(self) -> None:
        base = _make_result((FileComparison("gone.txt", FileStatus.identical, None, None),))
        curr = _make_result(())
        comparison = compare_to_baseline(base, curr)
        output = self._render_to_string(comparison)
        assert "no longer tracked" in output
        assert "gone.txt" in output

    def test_renders_files_only_in_current(self) -> None:
        base = _make_result(())
        curr = _make_result((FileComparison("new.txt", FileStatus.added, None, None),))
        comparison = compare_to_baseline(base, curr)
        output = self._render_to_string(comparison)
        assert "new file(s) tracked" in output
        assert "new.txt" in output

    def test_no_changes_message(self) -> None:
        comp = FileComparison("a.txt", FileStatus.identical, None, None)
        base = _make_result((comp,))
        curr = _make_result((comp,))
        comparison = compare_to_baseline(base, curr)
        output = self._render_to_string(comparison)
        assert "No changes from baseline" in output
