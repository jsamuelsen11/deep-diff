"""Tests for deep_diff.cli.app."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from deep_diff.cli.app import app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


class TestCliHelp:
    """Verify help output."""

    def test_help_flag(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Compare files and directories" in result.output

    def test_no_args_shows_usage(self) -> None:
        result = runner.invoke(app, [])
        assert "Usage" in result.output or "LEFT" in result.output


class TestCliVersion:
    """Verify version output."""

    def test_version_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "deep-diff" in result.output
        assert "0.1.0" in result.output

    def test_version_short_flag(self) -> None:
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert "deep-diff" in result.output


class TestCliDepthParsing:
    """Verify depth option parsing."""

    def test_valid_depth_structure(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--depth", "structure"])
        assert result.exit_code == 0

    def test_invalid_depth(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--depth", "invalid"])
        assert result.exit_code != 0

    def test_auto_detect_dirs(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right)])
        assert result.exit_code == 0


class TestCliOutputMode:
    """Verify output mode option."""

    def test_default_is_rich(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right)])
        assert result.exit_code == 0

    def test_invalid_output_mode(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--output", "invalid"])
        assert result.exit_code != 0


class TestCliFilterFlags:
    """Verify filter-related CLI flags are accepted."""

    def test_no_gitignore_flag(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--no-gitignore"])
        assert result.exit_code == 0

    def test_hidden_flag(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--hidden"])
        assert result.exit_code == 0

    def test_include_flag(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--include", "*.txt"])
        assert result.exit_code == 0

    def test_exclude_flag(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--exclude", "*.log"])
        assert result.exit_code == 0


class TestCliStatFlag:
    """Verify --stat flag shows summary instead of tree."""

    def test_stat_shows_summary(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--stat"])
        assert result.exit_code == 0
        assert "files compared" in result.output


class TestCliJsonOutput:
    """Verify --output json produces valid JSON."""

    def test_json_output_is_valid_json(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--output", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "comparisons" in data

    def test_json_output_has_top_level_keys(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--output", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert set(data.keys()) == {"left_root", "right_root", "depth", "comparisons", "stats"}

    def test_json_stat_flag(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--output", "json", "--stat"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "total_files" in data
        assert "comparisons" not in data

    def test_json_content_depth(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(
            app, [str(left), str(right), "--output", "json", "--depth", "content"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["depth"] == "content"

    def test_json_text_depth(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--output", "json", "--depth", "text"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["depth"] == "text"


class TestCliHtmlOutput:
    """Verify --output html produces valid HTML."""

    def test_html_output_is_valid_markup(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--output", "html"])
        assert result.exit_code == 0
        assert "<!DOCTYPE html>" in result.output
        assert "</html>" in result.output

    def test_html_stat_flag(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--output", "html", "--stat"])
        assert result.exit_code == 0
        assert "<!DOCTYPE html>" in result.output
        assert "Diff Summary" in result.output
        assert "Total Files" in result.output

    def test_html_content_depth(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(
            app, [str(left), str(right), "--output", "html", "--depth", "content"]
        )
        assert result.exit_code == 0
        assert "Left Hash" in result.output

    def test_html_text_depth(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right), "--output", "html", "--depth", "text"])
        assert result.exit_code == 0
        assert "<!DOCTYPE html>" in result.output


class TestCliErrorHandling:
    """Verify error handling for invalid inputs."""

    def test_nonexistent_left_path(self, tmp_path: Path) -> None:
        right = tmp_path / "right"
        right.mkdir()
        result = runner.invoke(app, [str(tmp_path / "nonexistent"), str(right)])
        assert result.exit_code == 2
        assert "Error:" in result.output

    def test_nonexistent_right_path(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        left.mkdir()
        result = runner.invoke(app, [str(left), str(tmp_path / "nonexistent")])
        assert result.exit_code == 2
        assert "Error:" in result.output

    def test_mixed_file_and_dir(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        a_file = left / "common.txt"
        result = runner.invoke(app, [str(a_file), str(right)])
        assert result.exit_code == 2
        assert "Error:" in result.output
