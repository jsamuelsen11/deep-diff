"""CLI entry point for deep-diff."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from deep_diff.core.comparator import Comparator
from deep_diff.core.filtering import FilterConfig
from deep_diff.core.models import DiffDepth, OutputMode
from deep_diff.output.rich_output import RichRenderer

if TYPE_CHECKING:
    from deep_diff.output.base import Renderer

app = typer.Typer(
    name="deep-diff",
    help="Compare files and directories with clarity.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        from deep_diff import __version__

        typer.echo(f"deep-diff {__version__}")
        raise typer.Exit()


def _parse_depth(value: str | None) -> DiffDepth | None:
    """Parse depth string to DiffDepth enum, None for auto-detect."""
    if value is None:
        return None
    try:
        return DiffDepth(value)
    except ValueError:
        valid = ", ".join(d.value for d in DiffDepth)
        msg = f"Invalid depth '{value}'. Choose from: {valid}"
        raise typer.BadParameter(msg) from None


def _parse_output_mode(value: str) -> OutputMode:
    """Parse output string to OutputMode enum."""
    try:
        return OutputMode(value)
    except ValueError:
        valid = ", ".join(o.value for o in OutputMode)
        msg = f"Invalid output mode '{value}'. Choose from: {valid}"
        raise typer.BadParameter(msg) from None


def _build_filter_config(
    *,
    no_gitignore: bool,
    hidden: bool,
    include: list[str] | None,
    exclude: list[str] | None,
) -> FilterConfig:
    """Build FilterConfig from CLI flags."""
    return FilterConfig(
        respect_gitignore=not no_gitignore,
        include_hidden=hidden,
        include_patterns=tuple(include) if include else (),
        exclude_patterns=tuple(exclude) if exclude else (),
    )


def _get_renderer(output_mode: OutputMode) -> Renderer:
    """Get the appropriate renderer for the output mode.

    Args:
        output_mode: The output mode to use.

    Returns:
        A renderer instance.

    Raises:
        NotImplementedError: If the output mode is not yet supported.
    """
    if output_mode == OutputMode.rich:
        return RichRenderer()
    if output_mode == OutputMode.json:
        from deep_diff.output.json_output import JsonRenderer

        return JsonRenderer()
    if output_mode == OutputMode.html:
        from deep_diff.output.html_output import HtmlRenderer

        return HtmlRenderer()

    msg = f"Output mode '{output_mode}' is not yet implemented"
    raise NotImplementedError(msg)


@app.command()
def main(
    left: Annotated[
        str,
        typer.Argument(help="Left path or git ref (git:<ref>) to compare."),
    ],
    right: Annotated[
        str,
        typer.Argument(help="Right path or git ref (git:<ref>) to compare."),
    ],
    depth: Annotated[
        str | None,
        typer.Option("--depth", "-d", help="Comparison depth: structure, content, or text."),
    ] = None,
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output mode: rich, tui, json, or html."),
    ] = "rich",
    no_gitignore: Annotated[
        bool,
        typer.Option("--no-gitignore", help="Don't respect .gitignore rules."),
    ] = False,
    hidden: Annotated[
        bool,
        typer.Option("--hidden", help="Include hidden files and directories."),
    ] = False,
    include: Annotated[
        list[str] | None,
        typer.Option("--include", "-I", help="Glob pattern(s) for files to include."),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", "-E", help="Glob pattern(s) for files to exclude."),
    ] = None,
    stat: Annotated[
        bool,
        typer.Option("--stat", help="Show only summary statistics."),
    ] = False,
    hash_algo: Annotated[
        str,
        typer.Option("--hash", help="Hash algorithm for content comparison."),
    ] = "sha256",
    context_lines: Annotated[
        int,
        typer.Option("--context", "-C", help="Number of context lines in text diffs."),
    ] = 3,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    """Compare files and directories at multiple depth levels.

    Supports git refs with the git: prefix (e.g. git:main, git:HEAD~2).
    """
    from deep_diff.git.commands import GitError
    from deep_diff.git.resolver import GitResolver

    try:
        parsed_depth = _parse_depth(depth)
        output_mode = _parse_output_mode(output)
        filter_config = _build_filter_config(
            no_gitignore=no_gitignore,
            hidden=hidden,
            include=include,
            exclude=exclude,
        )

        comparator = Comparator(
            depth=parsed_depth,
            filter_config=filter_config,
            context_lines=context_lines,
            hash_algo=hash_algo,
        )

        with GitResolver(cwd=Path.cwd()) as resolver:
            left_path, right_path = resolver.resolve_pair(left, right)
            result = comparator.compare(left_path, right_path)

            # TUI runs its own event loop — handle before renderer
            if output_mode == OutputMode.tui:
                from deep_diff.tui import DeepDiffApp

                tui_app = DeepDiffApp(result, stat_only=stat)
                tui_app.run()
                return

            renderer = _get_renderer(output_mode)

            if stat:
                renderer.render_stats(result.stats)
            else:
                renderer.render(result)

    except (FileNotFoundError, ValueError, NotADirectoryError, GitError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from None
    except NotImplementedError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
