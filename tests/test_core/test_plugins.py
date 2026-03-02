"""Tests for deep_diff.core.plugins."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from deep_diff.core.plugins import FileTypePlugin, PluginRegistry

if TYPE_CHECKING:
    from pathlib import Path

    from deep_diff.core.models import FileComparison


class _ValidPlugin:
    """A minimal conforming plugin for testing."""

    @property
    def name(self) -> str:
        return "test"

    @property
    def extensions(self) -> tuple[str, ...]:
        return (".test",)

    def compare(
        self,
        left: Path,
        right: Path,
        *,
        relative_path: str = "",
    ) -> FileComparison:
        raise NotImplementedError


class _AnotherPlugin:
    """A second conforming plugin for conflict testing."""

    @property
    def name(self) -> str:
        return "another"

    @property
    def extensions(self) -> tuple[str, ...]:
        return (".test",)

    def compare(
        self,
        left: Path,
        right: Path,
        *,
        relative_path: str = "",
    ) -> FileComparison:
        raise NotImplementedError


class _NonConformingPlugin:
    """Missing required protocol members."""

    pass


class TestFileTypePluginProtocol:
    """Verify runtime_checkable protocol behavior."""

    def test_conforming_class_is_instance(self) -> None:
        assert isinstance(_ValidPlugin(), FileTypePlugin)

    def test_non_conforming_class_is_not_instance(self) -> None:
        assert not isinstance(_NonConformingPlugin(), FileTypePlugin)

    def test_object_is_not_instance(self) -> None:
        assert not isinstance(object(), FileTypePlugin)


class TestPluginRegistryRegister:
    """Verify plugin registration behavior."""

    def test_register_valid_plugin(self) -> None:
        registry = PluginRegistry()
        registry.register(_ValidPlugin())
        assert "test" in registry.plugins

    def test_register_invalid_raises_type_error(self) -> None:
        registry = PluginRegistry()
        with pytest.raises(TypeError, match="does not satisfy"):
            registry.register(_NonConformingPlugin())  # type: ignore[arg-type]

    def test_registered_plugin_accessible_by_name(self) -> None:
        registry = PluginRegistry()
        plugin = _ValidPlugin()
        registry.register(plugin)
        assert registry.plugins["test"] is plugin


class TestPluginRegistryLookup:
    """Verify extension-based plugin lookup."""

    def test_get_for_path_returns_plugin(self) -> None:
        registry = PluginRegistry()
        plugin = _ValidPlugin()
        registry.register(plugin)
        assert registry.get_for_path("data/file.test") is plugin

    def test_get_for_path_case_insensitive(self) -> None:
        registry = PluginRegistry()
        plugin = _ValidPlugin()
        registry.register(plugin)
        assert registry.get_for_path("file.TEST") is plugin
        assert registry.get_for_path("file.Test") is plugin

    def test_get_for_path_unknown_extension_returns_none(self) -> None:
        registry = PluginRegistry()
        registry.register(_ValidPlugin())
        assert registry.get_for_path("file.unknown") is None

    def test_get_for_path_no_suffix_returns_none(self) -> None:
        registry = PluginRegistry()
        registry.register(_ValidPlugin())
        assert registry.get_for_path("Makefile") is None

    def test_get_for_path_nested_path(self) -> None:
        registry = PluginRegistry()
        plugin = _ValidPlugin()
        registry.register(plugin)
        assert registry.get_for_path("a/b/c/deep.test") is plugin


class TestPluginRegistryConflicts:
    """Verify duplicate extension handling."""

    def test_duplicate_extension_last_wins(self) -> None:
        registry = PluginRegistry()
        registry.register(_ValidPlugin())
        another = _AnotherPlugin()
        registry.register(another)
        assert registry.get_for_path("file.test") is another

    def test_duplicate_extension_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        registry = PluginRegistry()
        registry.register(_ValidPlugin())
        with caplog.at_level(logging.WARNING):
            registry.register(_AnotherPlugin())
        assert "overrides" in caplog.text
        assert ".test" in caplog.text


class TestPluginRegistryNames:
    """Verify names() output."""

    def test_names_returns_sorted_tuple(self) -> None:
        registry = PluginRegistry()
        registry.register(_AnotherPlugin())
        registry.register(_ValidPlugin())
        assert registry.names() == ("another", "test")

    def test_names_empty_registry(self) -> None:
        registry = PluginRegistry()
        assert registry.names() == ()


class TestPluginRegistryPlugins:
    """Verify plugins property."""

    def test_plugins_returns_dict_copy(self) -> None:
        registry = PluginRegistry()
        registry.register(_ValidPlugin())
        plugins = registry.plugins
        plugins["fake"] = _ValidPlugin()  # type: ignore[assignment]
        # Original not mutated
        assert "fake" not in registry.plugins

    def test_plugins_empty(self) -> None:
        registry = PluginRegistry()
        assert registry.plugins == {}


class TestPluginRegistryDiscover:
    """Verify entry-point discovery."""

    def test_discover_loads_entry_points(self) -> None:
        mock_ep = MagicMock()
        mock_ep.name = "test"
        mock_ep.load.return_value = _ValidPlugin

        registry = PluginRegistry()
        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            registry.discover()

        assert "test" in registry.plugins

    def test_discover_handles_failed_entry_point(self, caplog: pytest.LogCaptureFixture) -> None:
        mock_ep = MagicMock()
        mock_ep.name = "broken"
        mock_ep.load.side_effect = ImportError("missing module")

        registry = PluginRegistry()
        with (
            patch("importlib.metadata.entry_points", return_value=[mock_ep]),
            caplog.at_level(logging.WARNING),
        ):
            registry.discover()

        assert "broken" not in registry.plugins
        assert "Failed to load" in caplog.text

    def test_discover_with_no_entry_points(self) -> None:
        registry = PluginRegistry()
        with patch("importlib.metadata.entry_points", return_value=[]):
            registry.discover()
        assert registry.plugins == {}
