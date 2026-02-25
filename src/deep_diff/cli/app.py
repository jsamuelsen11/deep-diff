"""CLI entry point for deep-diff."""

from __future__ import annotations

from typing import Annotated

import typer

app = typer.Typer(
    name="deep-diff",
    help="Compare files and directories with clarity.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def version_callback(value: bool) -> None:
    if value:
        from deep_diff import __version__

        typer.echo(f"deep-diff {__version__}")
        raise typer.Exit()


@app.command()
def main(
    left: Annotated[
        str,
        typer.Argument(help="Left path (file or directory) to compare."),
    ],
    right: Annotated[
        str,
        typer.Argument(help="Right path (file or directory) to compare."),
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
    """Compare files and directories at multiple depth levels."""
    typer.echo("deep-diff: not yet implemented")
    raise typer.Exit(code=0)
