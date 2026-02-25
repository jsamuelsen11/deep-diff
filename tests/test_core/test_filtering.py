"""Tests for deep_diff.core.filtering."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from deep_diff.core.filtering import FileFilter, FilterConfig


class TestFilterConfig:
    """Verify FilterConfig frozen dataclass."""

    def test_default_values(self) -> None:
        config = FilterConfig()
        assert config.respect_gitignore is True
        assert config.include_hidden is False
        assert config.include_patterns == ()
        assert config.exclude_patterns == ()

    def test_custom_values(self) -> None:
        config = FilterConfig(
            respect_gitignore=False,
            include_hidden=True,
            include_patterns=("*.py",),
            exclude_patterns=("test_*",),
        )
        assert config.respect_gitignore is False
        assert config.include_hidden is True
        assert config.include_patterns == ("*.py",)
        assert config.exclude_patterns == ("test_*",)

    def test_frozen_immutable(self) -> None:
        config = FilterConfig()
        with pytest.raises(FrozenInstanceError):
            config.respect_gitignore = False  # type: ignore[misc]

    def test_patterns_are_tuples(self) -> None:
        config = FilterConfig(include_patterns=("*.py", "*.txt"), exclude_patterns=("*.log",))
        assert isinstance(config.include_patterns, tuple)
        assert isinstance(config.exclude_patterns, tuple)


class TestFileFilterHiddenFiles:
    """Test hidden file/directory filtering."""

    def test_excludes_hidden_files_by_default(self, sample_dirs: tuple[Path, Path]) -> None:
        left, _ = sample_dirs
        config = FilterConfig(respect_gitignore=False)
        result = FileFilter(config).scan(left)
        assert ".hidden" not in result
        # Non-hidden files should be present
        assert "common.txt" in result

    def test_includes_hidden_files_when_configured(self, sample_dirs: tuple[Path, Path]) -> None:
        left, _ = sample_dirs
        config = FilterConfig(respect_gitignore=False, include_hidden=True)
        result = FileFilter(config).scan(left)
        assert ".hidden" in result

    def test_excludes_hidden_directories(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / ".secret").mkdir()
        (root / ".secret" / "data.txt").write_text("hidden\n")
        (root / "visible.txt").write_text("visible\n")

        config = FilterConfig(respect_gitignore=False)
        result = FileFilter(config).scan(root)
        assert result == ("visible.txt",)

    def test_includes_hidden_directories_when_configured(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / ".secret").mkdir()
        (root / ".secret" / "data.txt").write_text("hidden\n")
        (root / "visible.txt").write_text("visible\n")

        config = FilterConfig(respect_gitignore=False, include_hidden=True)
        result = FileFilter(config).scan(root)
        assert ".secret/data.txt" in result
        assert "visible.txt" in result


class TestFileFilterGitignore:
    """Test gitignore-based filtering."""

    def test_basic_gitignore_matching(self, sample_gitignore: Path) -> None:
        config = FilterConfig(include_hidden=True)
        result = FileFilter(config).scan(sample_gitignore)
        assert "keep.py" in result
        assert "ignore.pyc" not in result
        assert ".env" not in result

    def test_gitignore_directory_pattern(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / ".gitignore").write_text("__pycache__/\n")
        (root / "__pycache__").mkdir()
        (root / "__pycache__" / "module.cpython-311.pyc").write_text("bytecode\n")
        (root / "app.py").write_text("code\n")

        config = FilterConfig(include_hidden=True)
        result = FileFilter(config).scan(root)
        assert "app.py" in result
        assert "__pycache__/module.cpython-311.pyc" not in result
        # .gitignore itself should be present when include_hidden=True
        assert ".gitignore" in result

    def test_negation_pattern(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / ".gitignore").write_text("*.pyc\n!important.pyc\n")
        (root / "junk.pyc").write_text("junk\n")
        (root / "important.pyc").write_text("keep\n")
        (root / "app.py").write_text("code\n")

        config = FilterConfig(include_hidden=True)
        result = FileFilter(config).scan(root)
        assert "app.py" in result
        assert "important.pyc" in result
        assert "junk.pyc" not in result

    def test_nested_gitignore(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "sub").mkdir()
        (root / ".gitignore").write_text("*.log\n")
        (root / "sub" / ".gitignore").write_text("*.tmp\n")
        (root / "app.log").write_text("log\n")
        (root / "keep.txt").write_text("keep\n")
        (root / "sub" / "data.tmp").write_text("tmp\n")
        (root / "sub" / "app.log").write_text("log\n")
        (root / "sub" / "keep.txt").write_text("keep\n")

        config = FilterConfig(include_hidden=True)
        result = FileFilter(config).scan(root)
        assert "keep.txt" in result
        assert "sub/keep.txt" in result
        assert "app.log" not in result
        assert "sub/app.log" not in result
        assert "sub/data.tmp" not in result

    def test_nested_gitignore_does_not_affect_parent(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "sub").mkdir()
        (root / "sub" / ".gitignore").write_text("*.tmp\n")
        (root / "data.tmp").write_text("parent tmp\n")
        (root / "sub" / "data.tmp").write_text("child tmp\n")

        config = FilterConfig(include_hidden=True)
        result = FileFilter(config).scan(root)
        # Parent's data.tmp should NOT be ignored (sub's gitignore doesn't apply)
        assert "data.tmp" in result
        # Child's data.tmp SHOULD be ignored
        assert "sub/data.tmp" not in result

    def test_no_gitignore_file(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "a.txt").write_text("a\n")
        (root / "b.py").write_text("b\n")

        config = FilterConfig()
        result = FileFilter(config).scan(root)
        assert "a.txt" in result
        assert "b.py" in result

    def test_gitignore_disabled(self, sample_gitignore: Path) -> None:
        config = FilterConfig(respect_gitignore=False, include_hidden=True)
        result = FileFilter(config).scan(sample_gitignore)
        assert "keep.py" in result
        assert "ignore.pyc" in result
        assert ".env" in result

    def test_gitignore_with_comments_and_blank_lines(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / ".gitignore").write_text("# comment\n\n*.log\n\n# another comment\n")
        (root / "app.log").write_text("log\n")
        (root / "app.py").write_text("code\n")

        config = FilterConfig(include_hidden=True)
        result = FileFilter(config).scan(root)
        assert "app.py" in result
        assert "app.log" not in result


class TestFileFilterIncludePatterns:
    """Test include glob patterns (allowlist)."""

    def test_include_single_pattern(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "app.py").write_text("code\n")
        (root / "readme.txt").write_text("readme\n")
        (root / "data.csv").write_text("data\n")

        config = FilterConfig(respect_gitignore=False, include_patterns=("*.py",))
        result = FileFilter(config).scan(root)
        assert result == ("app.py",)

    def test_include_multiple_patterns(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "app.py").write_text("code\n")
        (root / "readme.txt").write_text("readme\n")
        (root / "data.csv").write_text("data\n")

        config = FilterConfig(respect_gitignore=False, include_patterns=("*.py", "*.txt"))
        result = FileFilter(config).scan(root)
        assert result == ("app.py", "readme.txt")

    def test_include_no_patterns_includes_all(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "a.py").write_text("a\n")
        (root / "b.txt").write_text("b\n")

        config = FilterConfig(respect_gitignore=False)
        result = FileFilter(config).scan(root)
        assert result == ("a.py", "b.txt")


class TestFileFilterExcludePatterns:
    """Test exclude glob patterns (blocklist)."""

    def test_exclude_single_pattern(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "app.py").write_text("code\n")
        (root / "debug.log").write_text("log\n")
        (root / "readme.txt").write_text("readme\n")

        config = FilterConfig(respect_gitignore=False, exclude_patterns=("*.log",))
        result = FileFilter(config).scan(root)
        assert "app.py" in result
        assert "readme.txt" in result
        assert "debug.log" not in result

    def test_exclude_multiple_patterns(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "app.py").write_text("code\n")
        (root / "debug.log").write_text("log\n")
        (root / "data.tmp").write_text("tmp\n")

        config = FilterConfig(respect_gitignore=False, exclude_patterns=("*.log", "*.tmp"))
        result = FileFilter(config).scan(root)
        assert result == ("app.py",)

    def test_exclude_overrides_include(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "app.py").write_text("code\n")
        (root / "test_app.py").write_text("test\n")

        config = FilterConfig(
            respect_gitignore=False,
            include_patterns=("*.py",),
            exclude_patterns=("test_*",),
        )
        result = FileFilter(config).scan(root)
        assert result == ("app.py",)


class TestFileFilterCombined:
    """Test interactions between all filter layers."""

    def test_all_filters_active(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "sub").mkdir()
        (root / ".gitignore").write_text("*.pyc\n")
        (root / "app.py").write_text("code\n")
        (root / "test_app.py").write_text("test\n")
        (root / "cache.pyc").write_text("bytecode\n")
        (root / ".env").write_text("secret\n")
        (root / "sub" / "lib.py").write_text("lib\n")
        (root / "sub" / "test_lib.py").write_text("test\n")

        config = FilterConfig(
            respect_gitignore=True,
            include_hidden=False,
            include_patterns=("*.py",),
            exclude_patterns=("*test_*",),
        )
        result = FileFilter(config).scan(root)
        assert result == ("app.py", "sub/lib.py")

    def test_hidden_checked_before_gitignore(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / ".gitignore").write_text("!.env\n")
        (root / ".env").write_text("secret\n")
        (root / "app.py").write_text("code\n")

        # With include_hidden=False, .env is filtered by hidden check first
        config = FilterConfig(include_hidden=False)
        result = FileFilter(config).scan(root)
        assert ".env" not in result
        assert "app.py" in result

    def test_empty_directory_tree(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()

        config = FilterConfig()
        result = FileFilter(config).scan(root)
        assert result == ()

    def test_deeply_nested_structure(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        current = root
        for part in ["a", "b", "c", "d"]:
            current = current / part
            current.mkdir(parents=True, exist_ok=True)
        (current / "deep.txt").write_text("deep\n")
        (root / "top.txt").write_text("top\n")

        config = FilterConfig(respect_gitignore=False)
        result = FileFilter(config).scan(root)
        assert "a/b/c/d/deep.txt" in result
        assert "top.txt" in result

    def test_results_are_sorted(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "z.txt").write_text("z\n")
        (root / "a.txt").write_text("a\n")
        (root / "m.txt").write_text("m\n")

        config = FilterConfig(respect_gitignore=False)
        result = FileFilter(config).scan(root)
        assert result == ("a.txt", "m.txt", "z.txt")

    def test_results_are_tuple(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / "a.txt").write_text("a\n")

        config = FilterConfig(respect_gitignore=False)
        result = FileFilter(config).scan(root)
        assert isinstance(result, tuple)


class TestFileFilterEdgeCases:
    """Test edge cases and error handling."""

    def test_nonexistent_root_raises(self, tmp_path: Path) -> None:
        config = FilterConfig()
        with pytest.raises(NotADirectoryError, match="Not a directory"):
            FileFilter(config).scan(tmp_path / "nonexistent")

    def test_file_as_root_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("data\n")
        config = FilterConfig()
        with pytest.raises(NotADirectoryError, match="Not a directory"):
            FileFilter(config).scan(f)

    def test_gitignore_dir_only_pattern_ignores_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (root / ".gitignore").write_text("build/\n")
        (root / "build").mkdir()
        (root / "build" / "output.js").write_text("built\n")
        # A file named 'build' (not a directory) should not be ignored by 'build/'
        (root / "build.txt").write_text("text\n")

        config = FilterConfig(include_hidden=True)
        result = FileFilter(config).scan(root)
        assert "build.txt" in result
        assert "build/output.js" not in result


class TestFileFilterPublicAPI:
    """Verify re-exports from core.__init__."""

    def test_filter_config_importable_from_core(self) -> None:
        from deep_diff.core import FilterConfig as FilterConfigReexport

        assert FilterConfigReexport is not None

    def test_file_filter_importable_from_core(self) -> None:
        from deep_diff.core import FileFilter as FileFilterReexport

        assert FileFilterReexport is not None

    def test_all_contains_filter_symbols(self) -> None:
        import deep_diff.core as core

        assert "FilterConfig" in core.__all__
        assert "FileFilter" in core.__all__

    def test_filter_config_identity(self) -> None:
        import deep_diff.core as core

        assert core.FilterConfig is FilterConfig

    def test_file_filter_identity(self) -> None:
        import deep_diff.core as core

        assert core.FileFilter is FileFilter
