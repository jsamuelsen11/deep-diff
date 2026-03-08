"""CLI test configuration."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_rich_forced_colors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent Rich from forcing ANSI color in CI environments.

    GitHub Actions sets GITHUB_ACTIONS=true, which Rich interprets as
    force_terminal=True.  This injects ANSI escape codes into Typer's
    help output even inside CliRunner (where color is off by default),
    breaking substring assertions like ``"--watch" in result.output``.
    """
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
