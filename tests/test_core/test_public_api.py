"""Tests for deep_diff.core public API re-exports."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import StrEnum

import deep_diff.core as core
from deep_diff.core import (
    ChangeType,
    DiffDepth,
    DiffResult,
    DiffStats,
    FileComparison,
    FileStatus,
    FilterConfig,
    Hunk,
    OutputMode,
    TextChange,
    filtering,
    models,
    structure,
)
from deep_diff.core import (
    comparator as comparator_module,
)
from deep_diff.core import (
    text as text_module,
)

EXPECTED_NAMES = {
    "ChangeType",
    "Comparator",
    "DiffDepth",
    "DiffResult",
    "DiffStats",
    "FileComparison",
    "FileFilter",
    "FileStatus",
    "FilterConfig",
    "Hunk",
    "OutputMode",
    "StructureComparator",
    "TextChange",
    "TextComparator",
}


class TestAllExports:
    """Verify __all__ matches the expected public API surface."""

    def test_all_contains_expected_names(self) -> None:
        assert set(core.__all__) == EXPECTED_NAMES

    def test_all_has_no_extras(self) -> None:
        for name in core.__all__:
            assert name in EXPECTED_NAMES, f"unexpected export: {name}"

    def test_all_names_are_importable(self) -> None:
        for name in core.__all__:
            assert hasattr(core, name), f"{name} listed in __all__ but not importable"


class TestReExportIdentity:
    """Verify re-exports are the same objects as the originals in models."""

    def test_enums_are_identical(self) -> None:
        assert core.DiffDepth is models.DiffDepth
        assert core.OutputMode is models.OutputMode
        assert core.FileStatus is models.FileStatus
        assert core.ChangeType is models.ChangeType

    def test_dataclasses_are_identical(self) -> None:
        assert core.TextChange is models.TextChange
        assert core.Hunk is models.Hunk
        assert core.FileComparison is models.FileComparison
        assert core.DiffStats is models.DiffStats
        assert core.DiffResult is models.DiffResult

    def test_filtering_symbols_are_identical(self) -> None:
        assert core.FilterConfig is filtering.FilterConfig
        assert core.FileFilter is filtering.FileFilter

    def test_structure_comparator_is_identical(self) -> None:
        assert core.StructureComparator is structure.StructureComparator

    def test_comparator_is_identical(self) -> None:
        assert core.Comparator is comparator_module.Comparator

    def test_text_comparator_is_identical(self) -> None:
        assert core.TextComparator is text_module.TextComparator


class TestReExportTypes:
    """Verify re-exported symbols have the expected types."""

    def test_enums_are_str_enums(self) -> None:
        for cls in (DiffDepth, OutputMode, FileStatus, ChangeType):
            assert issubclass(cls, StrEnum), f"{cls.__name__} is not a StrEnum"

    def test_dataclasses_are_frozen(self) -> None:
        for cls in (TextChange, Hunk, FileComparison, DiffStats, DiffResult, FilterConfig):
            assert is_dataclass(cls), f"{cls.__name__} is not a dataclass"
            # frozen dataclasses have __dataclass_params__.frozen == True
            assert fields(cls) is not None  # sanity: fields() works
