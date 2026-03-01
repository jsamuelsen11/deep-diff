"""Snapshot persistence: save DiffResult to disk and reload for baseline comparison.

Snapshots are versioned JSON files with the structure::

    {"snapshot_version": 1, "result": { ... DiffResult fields ... }}

Path fields (left_path, right_path in FileComparison) are serialized as absolute
path strings. When loaded on a different machine, these paths may not exist but
are preserved for informational purposes.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Any

from deep_diff.core.models import (
    ChangeType,
    DiffDepth,
    DiffResult,
    DiffStats,
    FileComparison,
    FileStatus,
    Hunk,
    TextChange,
)

if TYPE_CHECKING:
    from rich.console import Console

SNAPSHOT_VERSION = 1


class SnapshotError(Exception):
    """Raised when a snapshot file cannot be read or is invalid."""


@dataclass(frozen=True)
class FileStatusChange:
    """A file whose status changed between baseline and current run."""

    relative_path: str
    baseline_status: FileStatus
    current_status: FileStatus


@dataclass(frozen=True)
class BaselineComparison:
    """Result of comparing a baseline snapshot against a current run."""

    baseline: DiffResult
    current: DiffResult
    status_changes: tuple[FileStatusChange, ...]
    files_only_in_baseline: tuple[str, ...]
    files_only_in_current: tuple[str, ...]


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class _PathEncoder(json.JSONEncoder):
    """JSON encoder that handles Path objects."""

    def default(self, o: object) -> object:
        if isinstance(o, PurePath):
            return str(o)
        return super().default(o)


def save_snapshot(result: DiffResult, path: Path) -> None:
    """Serialize a DiffResult to *path* as a versioned JSON snapshot."""
    envelope: dict[str, Any] = {
        "snapshot_version": SNAPSHOT_VERSION,
        "result": dataclasses.asdict(result),
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(envelope, f, cls=_PathEncoder, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# Deserialization
# ---------------------------------------------------------------------------


def load_snapshot(path: Path) -> DiffResult:
    """Load a snapshot file and reconstruct the DiffResult.

    Raises:
        SnapshotError: If the file is missing, malformed, or has an
            unsupported version.
    """
    try:
        with path.open(encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
    except FileNotFoundError:
        msg = f"Snapshot file not found: {path}"
        raise SnapshotError(msg) from None
    except json.JSONDecodeError as exc:
        msg = f"Snapshot file is not valid JSON: {path}: {exc}"
        raise SnapshotError(msg) from exc

    version = data.get("snapshot_version")
    if version != SNAPSHOT_VERSION:
        msg = f"Unsupported snapshot version {version!r}. Expected {SNAPSHOT_VERSION}."
        raise SnapshotError(msg)

    try:
        return _result_from_dict(data["result"])
    except (KeyError, TypeError, ValueError) as exc:
        msg = f"Snapshot has invalid structure: {exc}"
        raise SnapshotError(msg) from exc


def _result_from_dict(d: dict[str, Any]) -> DiffResult:
    return DiffResult(
        left_root=Path(d["left_root"]),
        right_root=Path(d["right_root"]),
        depth=DiffDepth(d["depth"]),
        comparisons=tuple(_comparison_from_dict(c) for c in d["comparisons"]),
        stats=_stats_from_dict(d["stats"]),
    )


def _stats_from_dict(d: dict[str, Any]) -> DiffStats:
    return DiffStats(
        total_files=int(d["total_files"]),
        identical=int(d["identical"]),
        modified=int(d["modified"]),
        added=int(d["added"]),
        removed=int(d["removed"]),
    )


def _comparison_from_dict(d: dict[str, Any]) -> FileComparison:
    left_raw = d.get("left_path")
    right_raw = d.get("right_path")
    return FileComparison(
        relative_path=str(d["relative_path"]),
        status=FileStatus(d["status"]),
        left_path=Path(left_raw) if left_raw is not None else None,
        right_path=Path(right_raw) if right_raw is not None else None,
        hunks=tuple(_hunk_from_dict(h) for h in d.get("hunks", ())),
        content_hash_left=d.get("content_hash_left"),
        content_hash_right=d.get("content_hash_right"),
        similarity=float(d["similarity"]) if d.get("similarity") is not None else None,
    )


def _hunk_from_dict(d: dict[str, Any]) -> Hunk:
    return Hunk(
        start_left=int(d["start_left"]),
        count_left=int(d["count_left"]),
        start_right=int(d["start_right"]),
        count_right=int(d["count_right"]),
        changes=tuple(_change_from_dict(c) for c in d.get("changes", ())),
    )


def _change_from_dict(d: dict[str, Any]) -> TextChange:
    return TextChange(
        change_type=ChangeType(d["change_type"]),
        content=str(d["content"]),
        line_left=int(d["line_left"]) if d.get("line_left") is not None else None,
        line_right=int(d["line_right"]) if d.get("line_right") is not None else None,
    )


# ---------------------------------------------------------------------------
# Baseline comparison
# ---------------------------------------------------------------------------


def compare_to_baseline(
    baseline: DiffResult,
    current: DiffResult,
) -> BaselineComparison:
    """Compute what changed between a *baseline* snapshot and *current* result."""
    baseline_index = {c.relative_path: c for c in baseline.comparisons}
    current_index = {c.relative_path: c for c in current.comparisons}

    status_changes: list[FileStatusChange] = []
    for rel_path, base_comp in baseline_index.items():
        curr_comp = current_index.get(rel_path)
        if curr_comp is not None and curr_comp.status != base_comp.status:
            status_changes.append(
                FileStatusChange(
                    relative_path=rel_path,
                    baseline_status=base_comp.status,
                    current_status=curr_comp.status,
                )
            )

    baseline_paths = set(baseline_index)
    current_paths = set(current_index)

    return BaselineComparison(
        baseline=baseline,
        current=current,
        status_changes=tuple(sorted(status_changes, key=lambda c: c.relative_path)),
        files_only_in_baseline=tuple(sorted(baseline_paths - current_paths)),
        files_only_in_current=tuple(sorted(current_paths - baseline_paths)),
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_baseline(
    comparison: BaselineComparison,
    console: Console | None = None,
) -> None:
    """Render a baseline comparison to the terminal using Rich."""
    from rich.console import Console as RichConsole
    from rich.table import Table

    con = console or RichConsole()
    base = comparison.baseline
    curr = comparison.current

    # Header
    con.print(
        f"[bold]Baseline:[/bold] {base.left_root.name} vs {base.right_root.name}  "
        f"[dim]({base.depth})[/dim]",
    )
    con.print(
        f"[bold]Current:[/bold]  {curr.left_root.name} vs {curr.right_root.name}  "
        f"[dim]({curr.depth})[/dim]",
    )
    con.print()

    # Stat delta table
    table = Table(title="Stats Delta", title_style="bold")
    table.add_column("Metric", style="bold")
    table.add_column("Baseline", justify="right")
    table.add_column("Current", justify="right")
    table.add_column("Delta", justify="right")
    for metric in ("total_files", "identical", "modified", "added", "removed"):
        b_val: int = getattr(base.stats, metric)
        c_val: int = getattr(curr.stats, metric)
        delta = c_val - b_val
        if delta > 0:
            delta_str = f"[green]+{delta}[/green]"
        elif delta < 0:
            delta_str = f"[red]{delta}[/red]"
        else:
            delta_str = "[dim]0[/dim]"
        table.add_row(metric, str(b_val), str(c_val), delta_str)
    con.print(table)
    con.print()

    # Files that changed status
    if comparison.status_changes:
        con.print(
            f"[bold]{len(comparison.status_changes)} file(s) changed status:[/bold]",
        )
        for sc in comparison.status_changes:
            con.print(
                f"  [yellow]{sc.relative_path}[/yellow]: "
                f"[dim]{sc.baseline_status}[/dim] -> "
                f"[yellow]{sc.current_status}[/yellow]",
            )
        con.print()

    # Files only in baseline (no longer tracked)
    if comparison.files_only_in_baseline:
        count = len(comparison.files_only_in_baseline)
        con.print(f"[bold red]{count} file(s) no longer tracked:[/bold red]")
        for p in comparison.files_only_in_baseline:
            con.print(f"  [red]- {p}[/red]")
        con.print()

    # Files only in current (newly tracked)
    if comparison.files_only_in_current:
        count = len(comparison.files_only_in_current)
        con.print(f"[bold green]{count} new file(s) tracked:[/bold green]")
        for p in comparison.files_only_in_current:
            con.print(f"  [green]+ {p}[/green]")
        con.print()

    # No changes
    if (
        not comparison.status_changes
        and not comparison.files_only_in_baseline
        and not comparison.files_only_in_current
    ):
        con.print("[green]No changes from baseline.[/green]")
