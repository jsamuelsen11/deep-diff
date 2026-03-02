"""Watch mode: re-diff on filesystem changes with live terminal refresh."""

from __future__ import annotations

from typing import TYPE_CHECKING

import watchfiles
from rich.live import Live

if TYPE_CHECKING:
    from pathlib import Path

    from rich.console import Console, RenderableType

    from deep_diff.core.comparator import Comparator
    from deep_diff.output.rich_output import RichRenderer


def run_watch_loop(
    left: Path,
    right: Path,
    *,
    comparator: Comparator,
    renderer: RichRenderer,
    console: Console,
    stat: bool = False,
    debounce: int = 1600,
) -> None:
    """Run the diff in a watch loop, re-rendering on filesystem changes.

    Uses ``watchfiles.watch()`` to block on efficient cross-platform FS
    events.  Output is refreshed in-place via ``rich.live.Live``.

    Blocks until CTRL+C (KeyboardInterrupt) is received.

    Args:
        left: Left path to watch and compare.
        right: Right path to watch and compare.
        comparator: Pre-configured Comparator instance.
        renderer: RichRenderer whose ``build_renderable`` is called each cycle.
        console: Rich Console used for status messages and the Live context.
        stat: If True, render stats only (mirrors --stat flag).
        debounce: Debounce interval in milliseconds passed to watchfiles.
    """

    def _build_output() -> RenderableType:
        result = comparator.compare(left, right)
        if stat:
            return renderer.build_stats_renderable(result.stats)
        return renderer.build_renderable(result)

    initial = _build_output()

    console.print(
        f"[dim]Watching [bold]{left}[/bold] and [bold]{right}[/bold] "
        f"for changes... (CTRL+C to quit)[/dim]\n"
    )

    try:
        with Live(initial, console=console, refresh_per_second=1) as live:
            for _changes in watchfiles.watch(
                left,
                right,
                debounce=debounce,
                raise_interrupt=True,
            ):
                try:
                    renderable = _build_output()
                except (FileNotFoundError, OSError) as exc:
                    console.print(f"[yellow]Warning: {exc}[/yellow]")
                    continue
                live.update(renderable, refresh=True)
    except KeyboardInterrupt:
        console.print("\n[dim]Watch stopped.[/dim]")
