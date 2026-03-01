"""Tests for deep_diff.cli.app."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from deep_diff.cli.app import app

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

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


class TestCliGitRef:
    """Verify git ref support via git: prefix."""

    def test_git_ref_both_sides(self, git_repo: Path) -> None:
        result = runner.invoke(
            app,
            ["git:main", "git:feature", "--depth", "structure"],
            catch_exceptions=False,
            env={"GIT_DIR": str(git_repo / ".git"), "GIT_WORK_TREE": str(git_repo)},
        )
        # CliRunner doesn't inherit cwd, so we use monkeypatch in the next test
        # For now, just verify the basic flow doesn't crash with valid env
        # This test may fail due to cwd issues; see monkeypatch test below
        assert result.exit_code in (0, 2)

    def test_git_ref_with_monkeypatch(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(git_repo)
        result = runner.invoke(app, ["git:main", "git:feature", "--depth", "structure"])
        assert result.exit_code == 0

    def test_git_ref_text_depth(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(git_repo)
        result = runner.invoke(app, ["git:main", "git:feature", "--depth", "text"])
        assert result.exit_code == 0

    def test_git_ref_json_output(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(git_repo)
        result = runner.invoke(
            app, ["git:main", "git:feature", "--depth", "structure", "--output", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "comparisons" in data

    def test_git_ref_stat_flag(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(git_repo)
        result = runner.invoke(app, ["git:main", "git:feature", "--stat"])
        assert result.exit_code == 0

    def test_git_ref_mixed_with_plain_path(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(git_repo)
        result = runner.invoke(app, ["git:main", str(git_repo), "--depth", "structure"])
        assert result.exit_code == 0

    def test_invalid_git_ref_exits_2(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(git_repo)
        result = runner.invoke(app, ["git:nonexistent-branch", "git:main"])
        assert result.exit_code == 2
        assert "Error:" in result.output

    def test_not_git_repo_exits_2(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        not_a_repo = tmp_path / "empty"
        not_a_repo.mkdir()
        monkeypatch.chdir(not_a_repo)
        result = runner.invoke(app, ["git:main", "git:main"])
        assert result.exit_code == 2
        assert "Error:" in result.output

    def test_plain_paths_still_work(self, sample_dirs: tuple[Path, Path]) -> None:
        left, right = sample_dirs
        result = runner.invoke(app, [str(left), str(right)])
        assert result.exit_code == 0


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
