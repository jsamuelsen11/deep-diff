"""Tests for deep_diff.core.watcher."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

from deep_diff.core.watcher import run_watch_loop

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


def _make_watcher_gen(
    *, yields: int = 0, raise_interrupt: bool = True
) -> Generator[set[Any], None, None]:
    """Create a generator that yields empty change sets then optionally raises."""
    for _ in range(yields):
        yield set()
    if raise_interrupt:
        raise KeyboardInterrupt


def _patch_watch_and_live(
    watcher_gen: Generator[set[Any], None, None],
) -> tuple[Any, Any]:
    """Return (watch_patch, live_patch) context managers."""
    watch_patch = patch(
        "deep_diff.core.watcher.watchfiles.watch",
        return_value=watcher_gen,
    )
    live_mock = MagicMock()
    live_mock.__enter__ = MagicMock(return_value=live_mock)
    live_mock.__exit__ = MagicMock(return_value=False)
    live_patch = patch("deep_diff.core.watcher.Live", return_value=live_mock)
    return watch_patch, live_patch


class TestWatchLoopInitialRender:
    """Verify the initial diff fires before watching."""

    def test_initial_render_fires(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()

        comparator = MagicMock()
        comparator.compare.return_value = MagicMock(stats=MagicMock())
        renderer = MagicMock()
        renderer.build_renderable.return_value = "initial"
        console = MagicMock()

        watch_patch, live_patch = _patch_watch_and_live(_make_watcher_gen(yields=0))
        with watch_patch, live_patch:
            run_watch_loop(
                left,
                right,
                comparator=comparator,
                renderer=renderer,
                console=console,
                stat=False,
            )

        comparator.compare.assert_called_once_with(left, right)
        renderer.build_renderable.assert_called_once()


class TestWatchLoopRerender:
    """Verify re-rendering on filesystem changes."""

    def test_rerender_on_change(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()

        comparator = MagicMock()
        comparator.compare.return_value = MagicMock(stats=MagicMock())
        renderer = MagicMock()
        renderer.build_renderable.return_value = "rendered"
        console = MagicMock()

        watch_patch, live_patch = _patch_watch_and_live(_make_watcher_gen(yields=2))
        with watch_patch, live_patch:
            run_watch_loop(
                left,
                right,
                comparator=comparator,
                renderer=renderer,
                console=console,
            )

        # Initial + 2 changes = 3 calls
        assert comparator.compare.call_count == 3
        assert renderer.build_renderable.call_count == 3


class TestWatchLoopInterrupt:
    """Verify clean exit on CTRL+C."""

    def test_keyboard_interrupt_exits_cleanly(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()

        comparator = MagicMock()
        comparator.compare.return_value = MagicMock(stats=MagicMock())
        renderer = MagicMock()
        renderer.build_renderable.return_value = "rendered"
        console = MagicMock()

        watch_patch, live_patch = _patch_watch_and_live(
            _make_watcher_gen(yields=0, raise_interrupt=True)
        )
        with watch_patch, live_patch:
            # Should not raise
            run_watch_loop(
                left,
                right,
                comparator=comparator,
                renderer=renderer,
                console=console,
            )


class TestWatchLoopStatMode:
    """Verify --stat uses build_stats_renderable."""

    def test_stat_mode_calls_build_stats_renderable(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()

        comparator = MagicMock()
        comparator.compare.return_value = MagicMock(stats=MagicMock())
        renderer = MagicMock()
        renderer.build_stats_renderable.return_value = "stats"
        console = MagicMock()

        watch_patch, live_patch = _patch_watch_and_live(_make_watcher_gen(yields=0))
        with watch_patch, live_patch:
            run_watch_loop(
                left,
                right,
                comparator=comparator,
                renderer=renderer,
                console=console,
                stat=True,
            )

        renderer.build_stats_renderable.assert_called_once()
        renderer.build_renderable.assert_not_called()


class TestWatchLoopDebounce:
    """Verify debounce is passed through to watchfiles."""

    def test_debounce_passed_to_watchfiles(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()

        comparator = MagicMock()
        comparator.compare.return_value = MagicMock(stats=MagicMock())
        renderer = MagicMock()
        renderer.build_renderable.return_value = "rendered"
        console = MagicMock()

        watch_patch, live_patch = _patch_watch_and_live(_make_watcher_gen(yields=0))
        with watch_patch as mock_watch, live_patch:
            run_watch_loop(
                left,
                right,
                comparator=comparator,
                renderer=renderer,
                console=console,
                debounce=500,
            )

        mock_watch.assert_called_once_with(
            left,
            right,
            debounce=500,
            raise_interrupt=True,
        )


class TestWatchLoopErrorResilience:
    """Verify errors during re-compare don't kill the watch loop."""

    def test_oserror_during_compare_continues_loop(self, tmp_path: Path) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()

        comparator = MagicMock()
        result_mock = MagicMock(stats=MagicMock())
        # First call (initial) succeeds, second call (in loop) raises, third succeeds
        comparator.compare.side_effect = [result_mock, OSError("gone"), result_mock]
        renderer = MagicMock()
        renderer.build_renderable.return_value = "rendered"
        console = MagicMock()

        watch_patch, live_patch = _patch_watch_and_live(_make_watcher_gen(yields=2))
        with watch_patch, live_patch:
            run_watch_loop(
                left,
                right,
                comparator=comparator,
                renderer=renderer,
                console=console,
            )

        # 3 compare calls: initial + 2 loop iterations
        assert comparator.compare.call_count == 3
        # Only 2 renderable builds: initial + third (second raised)
        assert renderer.build_renderable.call_count == 2
