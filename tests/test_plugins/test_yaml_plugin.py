"""Tests for deep_diff.plugins.yaml_plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deep_diff.core.models import ChangeType, FileStatus
from deep_diff.core.plugins import FileTypePlugin
from deep_diff.plugins.yaml_plugin import YamlPlugin

if TYPE_CHECKING:
    from pathlib import Path


class TestYamlPluginProtocol:
    """Verify plugin satisfies the FileTypePlugin protocol."""

    def test_satisfies_protocol(self) -> None:
        assert isinstance(YamlPlugin(), FileTypePlugin)

    def test_name_is_yaml(self) -> None:
        assert YamlPlugin().name == "yaml"

    def test_extensions_are_yaml_and_yml(self) -> None:
        assert YamlPlugin().extensions == (".yaml", ".yml")


class TestYamlPluginIdentical:
    """Verify identical YAML detection."""

    def test_identical_yaml_files(self, tmp_path: Path) -> None:
        data = "a: 1\nb: 2\n"
        left = tmp_path / "left.yaml"
        right = tmp_path / "right.yaml"
        left.write_text(data)
        right.write_text(data)

        result = YamlPlugin().compare(left, right)
        assert result.status == FileStatus.identical
        assert result.similarity == 1.0

    def test_identical_yaml_different_formatting(self, tmp_path: Path) -> None:
        left = tmp_path / "left.yaml"
        right = tmp_path / "right.yaml"
        left.write_text("a:   1\nb:   2\n")
        right.write_text("a: 1\nb: 2\n")

        result = YamlPlugin().compare(left, right)
        assert result.status == FileStatus.identical

    def test_identical_yaml_different_key_order(self, tmp_path: Path) -> None:
        left = tmp_path / "left.yaml"
        right = tmp_path / "right.yaml"
        left.write_text("b: 2\na: 1\n")
        right.write_text("a: 1\nb: 2\n")

        result = YamlPlugin().compare(left, right)
        assert result.status == FileStatus.identical


class TestYamlPluginModified:
    """Verify diff detection for modified YAML."""

    def test_value_change_detected(self, tmp_path: Path) -> None:
        left = tmp_path / "left.yaml"
        right = tmp_path / "right.yaml"
        left.write_text("a: 1\n")
        right.write_text("a: 2\n")

        result = YamlPlugin().compare(left, right)
        assert result.status == FileStatus.modified
        assert result.similarity is not None
        assert result.similarity < 1.0
        assert len(result.hunks) >= 1

    def test_nested_change_detected(self, tmp_path: Path) -> None:
        left = tmp_path / "left.yaml"
        right = tmp_path / "right.yaml"
        left.write_text("nested:\n  x: 1\n")
        right.write_text("nested:\n  x: 2\n")

        result = YamlPlugin().compare(left, right)
        assert result.status == FileStatus.modified

    def test_key_addition_detected(self, tmp_path: Path) -> None:
        left = tmp_path / "left.yaml"
        right = tmp_path / "right.yaml"
        left.write_text("a: 1\n")
        right.write_text("a: 1\nb: 2\n")

        result = YamlPlugin().compare(left, right)
        assert result.status == FileStatus.modified
        all_changes = [c for h in result.hunks for c in h.changes]
        insert_types = [c for c in all_changes if c.change_type == ChangeType.insert]
        assert len(insert_types) >= 1


class TestYamlPluginFallback:
    """Verify fallback to text diff on invalid YAML."""

    def test_invalid_yaml_falls_back_to_text(self, tmp_path: Path) -> None:
        left = tmp_path / "left.yaml"
        right = tmp_path / "right.yaml"
        left.write_text(":\n  :\n    - [invalid")
        right.write_text("valid: data\n")

        result = YamlPlugin().compare(left, right)
        assert result.status in (FileStatus.identical, FileStatus.modified)
        assert result.relative_path == "left.yaml"


class TestYamlPluginEdgeCases:
    """Verify edge case handling."""

    def test_empty_yaml(self, tmp_path: Path) -> None:
        left = tmp_path / "left.yaml"
        right = tmp_path / "right.yaml"
        left.write_text("")
        right.write_text("")

        result = YamlPlugin().compare(left, right)
        assert result.status == FileStatus.identical

    def test_relative_path_default(self, tmp_path: Path) -> None:
        left = tmp_path / "config.yml"
        right = tmp_path / "other.yml"
        left.write_text("a: 1\n")
        right.write_text("a: 1\n")

        result = YamlPlugin().compare(left, right)
        assert result.relative_path == "config.yml"

    def test_relative_path_custom(self, tmp_path: Path) -> None:
        left = tmp_path / "left.yaml"
        right = tmp_path / "right.yaml"
        left.write_text("a: 1\n")
        right.write_text("a: 1\n")

        result = YamlPlugin().compare(left, right, relative_path="conf/app.yaml")
        assert result.relative_path == "conf/app.yaml"

    def test_result_paths_set(self, tmp_path: Path) -> None:
        left = tmp_path / "left.yaml"
        right = tmp_path / "right.yaml"
        left.write_text("a: 1\n")
        right.write_text("a: 1\n")

        result = YamlPlugin().compare(left, right)
        assert result.left_path == left
        assert result.right_path == right

    def test_hunks_are_tuples(self, tmp_path: Path) -> None:
        left = tmp_path / "left.yaml"
        right = tmp_path / "right.yaml"
        left.write_text("a: 1\n")
        right.write_text("a: 2\n")

        result = YamlPlugin().compare(left, right)
        assert isinstance(result.hunks, tuple)
