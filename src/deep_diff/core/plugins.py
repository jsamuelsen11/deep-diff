"""Plugin system for file-type-specific comparators."""

from __future__ import annotations

import importlib.metadata
import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from deep_diff.core.models import FileComparison

logger = logging.getLogger(__name__)


@runtime_checkable
class FileTypePlugin(Protocol):
    """Protocol for file-type-specific comparators.

    Plugins implement structural or semantic comparison for specific
    file types (e.g., JSON, YAML). They produce the same FileComparison
    result as the default TextComparator, enabling drop-in replacement.
    """

    @property
    def name(self) -> str:
        """Human-readable plugin name (e.g., 'json', 'yaml')."""
        ...

    @property
    def extensions(self) -> tuple[str, ...]:
        """File extensions this plugin handles (e.g., ('.json',)).

        Extensions include the leading dot and are matched case-insensitively.
        """
        ...

    def compare(
        self,
        left: Path,
        right: Path,
        *,
        relative_path: str = "",
        context_lines: int = 3,
    ) -> FileComparison:
        """Compare two files using type-specific logic.

        Args:
            left: Path to the left file.
            right: Path to the right file.
            relative_path: Display path label. Defaults to left.name when empty.
            context_lines: Number of context lines around each change.

        Returns:
            A FileComparison with status, hunks, and similarity.
        """
        ...


class PluginRegistry:
    """Discovers, stores, and resolves file-type plugins.

    Plugins are registered via:
    1. Programmatic API: ``registry.register(plugin)``
    2. Entry points: ``[project.entry-points."deep_diff.plugins"]``
    """

    ENTRY_POINT_GROUP = "deep_diff.plugins"

    def __init__(self) -> None:
        self._plugins: dict[str, FileTypePlugin] = {}
        self._extension_map: dict[str, FileTypePlugin] = {}

    def register(self, plugin: FileTypePlugin) -> None:
        """Register a plugin instance.

        Args:
            plugin: A FileTypePlugin-conforming object.

        Raises:
            TypeError: If plugin does not satisfy the FileTypePlugin protocol.
        """
        if not isinstance(plugin, FileTypePlugin):
            msg = f"Plugin {plugin!r} does not satisfy the FileTypePlugin protocol"
            raise TypeError(msg)

        self._plugins[plugin.name] = plugin
        for ext in plugin.extensions:
            normalized = ext.lower()
            if normalized in self._extension_map:
                existing = self._extension_map[normalized]
                logger.warning(
                    "Plugin '%s' overrides '%s' for extension '%s'",
                    plugin.name,
                    existing.name,
                    normalized,
                )
            self._extension_map[normalized] = plugin

    def discover(self) -> None:
        """Load plugins from entry points."""
        for ep in importlib.metadata.entry_points(group=self.ENTRY_POINT_GROUP):
            try:
                plugin_factory = ep.load()
                plugin = plugin_factory()
                self.register(plugin)
            except Exception:
                logger.warning(
                    "Failed to load plugin entry point '%s'",
                    ep.name,
                    exc_info=True,
                )

    def get_for_path(self, path_str: str) -> FileTypePlugin | None:
        """Look up a plugin by file path suffix.

        Args:
            path_str: Relative path string (e.g., 'data/config.json').

        Returns:
            Matching plugin or None.
        """
        from pathlib import PurePosixPath

        suffix = PurePosixPath(path_str).suffix
        if not suffix:
            return None
        return self._extension_map.get(suffix.lower())

    def names(self) -> tuple[str, ...]:
        """Return sorted tuple of registered plugin names."""
        return tuple(sorted(self._plugins))

    @property
    def plugins(self) -> dict[str, FileTypePlugin]:
        """Return all registered plugins keyed by name."""
        return dict(self._plugins)
