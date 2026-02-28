"""Tests for deep_diff.output.json_output."""

from __future__ import annotations

import json
import sys
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
from deep_diff.output.json_output import JsonRenderer


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


class TestJsonRendererInit:
    """Verify JsonRenderer constructor."""

    def test_default_output_is_stdout(self) -> None:
        r = JsonRenderer()
        assert r._output is sys.stdout

    def test_custom_output(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        assert r._output is buf

    def test_custom_indent(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf, indent=4)
        result = _make_result(())
        r.render(result)
        output = buf.getvalue()
        # 4-space indent means we should see "    " in the output
        assert "    " in output


class TestJsonRendererRender:
    """Verify render() serialization."""

    def test_empty_result_is_valid_json(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        result = _make_result(())
        r.render(result)
        data = json.loads(buf.getvalue())
        assert data["comparisons"] == []

    def test_structure_depth_roundtrip(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        comp = FileComparison(
            relative_path="a.txt",
            status=FileStatus.added,
            left_path=None,
            right_path=Path("/tmp/right/a.txt"),
        )
        result = _make_result((comp,))
        r.render(result)
        data = json.loads(buf.getvalue())
        assert data["comparisons"][0]["relative_path"] == "a.txt"
        assert data["comparisons"][0]["status"] == "added"
        assert data["comparisons"][0]["left_path"] is None
        assert data["comparisons"][0]["right_path"] == "/tmp/right/a.txt"

    def test_content_depth_with_hashes(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        comp = FileComparison(
            relative_path="data.bin",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/data.bin"),
            right_path=Path("/tmp/right/data.bin"),
            content_hash_left="aabbccdd11223344",
            content_hash_right="99887766aabbccdd",
        )
        result = _make_result((comp,), depth=DiffDepth.content)
        r.render(result)
        data = json.loads(buf.getvalue())
        c = data["comparisons"][0]
        assert c["content_hash_left"] == "aabbccdd11223344"
        assert c["content_hash_right"] == "99887766aabbccdd"

    def test_text_depth_with_hunks(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
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
        result = _make_result((comp,), depth=DiffDepth.text)
        r.render(result)
        data = json.loads(buf.getvalue())
        h = data["comparisons"][0]["hunks"][0]
        assert h["start_left"] == 1
        assert h["count_left"] == 3
        assert len(h["changes"]) == 3
        assert h["changes"][1]["change_type"] == "delete"
        assert h["changes"][1]["content"] == "old\n"

    def test_paths_serialized_as_strings(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        result = _make_result((), left_name="alpha", right_name="beta")
        r.render(result)
        data = json.loads(buf.getvalue())
        assert data["left_root"] == "/tmp/alpha"
        assert data["right_root"] == "/tmp/beta"
        assert isinstance(data["left_root"], str)

    def test_enums_serialized_as_values(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        comp = FileComparison(
            relative_path="f.txt",
            status=FileStatus.modified,
            left_path=Path("/tmp/left/f.txt"),
            right_path=Path("/tmp/right/f.txt"),
        )
        result = _make_result((comp,), depth=DiffDepth.content)
        r.render(result)
        data = json.loads(buf.getvalue())
        assert data["depth"] == "content"
        assert data["comparisons"][0]["status"] == "modified"

    def test_null_paths_preserved(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        comp = FileComparison(
            relative_path="new.txt",
            status=FileStatus.added,
            left_path=None,
            right_path=Path("/tmp/right/new.txt"),
        )
        result = _make_result((comp,))
        r.render(result)
        data = json.loads(buf.getvalue())
        assert data["comparisons"][0]["left_path"] is None

    def test_null_hashes_preserved(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        comp = FileComparison(
            relative_path="f.txt",
            status=FileStatus.identical,
            left_path=Path("/tmp/left/f.txt"),
            right_path=Path("/tmp/right/f.txt"),
        )
        result = _make_result((comp,))
        r.render(result)
        data = json.loads(buf.getvalue())
        assert data["comparisons"][0]["content_hash_left"] is None
        assert data["comparisons"][0]["similarity"] is None

    def test_output_ends_with_newline(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        result = _make_result(())
        r.render(result)
        assert buf.getvalue().endswith("\n")

    def test_top_level_keys(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        result = _make_result(())
        r.render(result)
        data = json.loads(buf.getvalue())
        assert set(data.keys()) == {"left_root", "right_root", "depth", "comparisons", "stats"}


class TestJsonRendererStats:
    """Verify render_stats() serialization."""

    def test_stats_is_valid_json(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        stats = DiffStats(total_files=5, identical=2, modified=1, added=1, removed=1)
        r.render_stats(stats)
        data = json.loads(buf.getvalue())
        assert set(data.keys()) == {"total_files", "identical", "modified", "added", "removed"}

    def test_stats_values_correct(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        stats = DiffStats(total_files=10, identical=4, modified=3, added=2, removed=1)
        r.render_stats(stats)
        data = json.loads(buf.getvalue())
        assert data["total_files"] == 10
        assert data["identical"] == 4
        assert data["modified"] == 3
        assert data["added"] == 2
        assert data["removed"] == 1

    def test_stats_zero_counts(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        stats = DiffStats(total_files=0, identical=0, modified=0, added=0, removed=0)
        r.render_stats(stats)
        data = json.loads(buf.getvalue())
        assert all(v == 0 for v in data.values())

    def test_stats_ends_with_newline(self) -> None:
        buf = StringIO()
        r = JsonRenderer(output=buf)
        stats = DiffStats(total_files=1, identical=1, modified=0, added=0, removed=0)
        r.render_stats(stats)
        assert buf.getvalue().endswith("\n")


class TestJsonRendererProtocol:
    """Verify JsonRenderer satisfies the Renderer protocol."""

    def test_isinstance_check(self) -> None:
        r = JsonRenderer()
        assert isinstance(r, Renderer)
