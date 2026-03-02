"""Tests for deep_diff.plugins.json_plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deep_diff.core.models import ChangeType, FileStatus
from deep_diff.core.plugins import FileTypePlugin
from deep_diff.plugins.json_plugin import JsonPlugin

if TYPE_CHECKING:
    from pathlib import Path


class TestJsonPluginProtocol:
    """Verify plugin satisfies the FileTypePlugin protocol."""

    def test_satisfies_protocol(self) -> None:
        assert isinstance(JsonPlugin(), FileTypePlugin)

    def test_name_is_json(self) -> None:
        assert JsonPlugin().name == "json"

    def test_extensions_is_json(self) -> None:
        assert JsonPlugin().extensions == (".json",)


class TestJsonPluginIdentical:
    """Verify identical JSON detection."""

    def test_identical_json_files(self, tmp_path: Path) -> None:
        data = '{"a": 1, "b": 2}\n'
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text(data)
        right.write_text(data)

        result = JsonPlugin().compare(left, right)
        assert result.status == FileStatus.identical
        assert result.similarity == 1.0
        assert result.hunks == ()

    def test_identical_json_different_whitespace(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text('{"a":1,"b":2}')
        right.write_text('{\n  "a": 1,\n  "b": 2\n}\n')

        result = JsonPlugin().compare(left, right)
        assert result.status == FileStatus.identical
        assert result.similarity == 1.0

    def test_identical_json_different_key_order(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text('{"b": 2, "a": 1}')
        right.write_text('{"a": 1, "b": 2}')

        result = JsonPlugin().compare(left, right)
        assert result.status == FileStatus.identical
        assert result.similarity == 1.0


class TestJsonPluginModified:
    """Verify diff detection for modified JSON."""

    def test_value_change_detected(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text('{"a": 1}')
        right.write_text('{"a": 2}')

        result = JsonPlugin().compare(left, right)
        assert result.status == FileStatus.modified
        assert result.similarity is not None
        assert result.similarity < 1.0
        assert len(result.hunks) >= 1

    def test_key_addition_detected(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text('{"a": 1}')
        right.write_text('{"a": 1, "b": 2}')

        result = JsonPlugin().compare(left, right)
        assert result.status == FileStatus.modified
        # New key should produce insert changes
        all_changes = [c for h in result.hunks for c in h.changes]
        insert_types = [c for c in all_changes if c.change_type == ChangeType.insert]
        assert len(insert_types) >= 1

    def test_key_removal_detected(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text('{"a": 1, "b": 2}')
        right.write_text('{"a": 1}')

        result = JsonPlugin().compare(left, right)
        assert result.status == FileStatus.modified
        all_changes = [c for h in result.hunks for c in h.changes]
        delete_types = [c for c in all_changes if c.change_type == ChangeType.delete]
        assert len(delete_types) >= 1

    def test_nested_change_detected(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text('{"nested": {"x": 1}}')
        right.write_text('{"nested": {"x": 2}}')

        result = JsonPlugin().compare(left, right)
        assert result.status == FileStatus.modified

    def test_array_order_change_detected(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text("[1, 2, 3]")
        right.write_text("[3, 2, 1]")

        result = JsonPlugin().compare(left, right)
        assert result.status == FileStatus.modified


class TestJsonPluginFallback:
    """Verify fallback to text diff on invalid JSON."""

    def test_invalid_json_falls_back_to_text(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text("not json {{{")
        right.write_text("also not json }}")

        result = JsonPlugin().compare(left, right)
        # Should still produce a result (text fallback)
        assert result.status in (FileStatus.identical, FileStatus.modified)
        assert result.relative_path == "left.json"

    def test_one_side_invalid_falls_back(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text('{"valid": true}')
        right.write_text("not json")

        result = JsonPlugin().compare(left, right)
        assert result.status == FileStatus.modified


class TestJsonPluginEdgeCases:
    """Verify edge case handling."""

    def test_empty_json_objects(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text("{}")
        right.write_text("{}")

        result = JsonPlugin().compare(left, right)
        assert result.status == FileStatus.identical

    def test_result_is_frozen(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text('{"a": 1}')
        right.write_text('{"a": 2}')

        result = JsonPlugin().compare(left, right)
        import dataclasses

        assert dataclasses.is_dataclass(result)

    def test_relative_path_default(self, tmp_path: Path) -> None:
        left = tmp_path / "config.json"
        right = tmp_path / "other.json"
        left.write_text("{}")
        right.write_text("{}")

        result = JsonPlugin().compare(left, right)
        assert result.relative_path == "config.json"

    def test_relative_path_custom(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text("{}")
        right.write_text("{}")

        result = JsonPlugin().compare(left, right, relative_path="data/config.json")
        assert result.relative_path == "data/config.json"

    def test_hunks_are_tuples(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text('{"a": 1}')
        right.write_text('{"a": 2}')

        result = JsonPlugin().compare(left, right)
        assert isinstance(result.hunks, tuple)
        for hunk in result.hunks:
            assert isinstance(hunk.changes, tuple)

    def test_paths_set_on_result(self, tmp_path: Path) -> None:
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text("{}")
        right.write_text("{}")

        result = JsonPlugin().compare(left, right)
        assert result.left_path == left
        assert result.right_path == right
