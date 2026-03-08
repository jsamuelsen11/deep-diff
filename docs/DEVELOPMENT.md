# Development Guide

## Prerequisites

- [Python 3.11+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/) — package manager and task runner
- [lefthook](https://github.com/evilmartians/lefthook) — git hooks manager

## Setup

```bash
# Clone the repository
git clone git@github.com:jsamuelsen11/deep-diff.git
cd deep-diff

# Install all dependencies (including dev group)
uv sync --all-groups

# Install git hooks
lefthook install
```

## Running the CLI

```bash
uv run deep-diff --help
uv run deep-diff dir_a/ dir_b/ --depth text
```

## Running Tests

```bash
# Basic test run
uv run pytest

# With coverage reporting
uv run pytest --cov=deep_diff --cov-report=term-missing

# Run a specific test file
uv run pytest tests/test_core/test_structure.py

# Run tests matching a keyword
uv run pytest -k "test_filter"
```

The coverage threshold is **80%**, enforced in `pyproject.toml` when using `--cov`.

## Code Quality

```bash
# Format code
uv run ruff format src/ tests/

# Lint (with auto-fix)
uv run ruff check --fix src/ tests/

# Type check
uv run mypy src/ --strict

# Format markdown
uv run mdformat docs/ README.md CONTRIBUTING.md

# Lint markdown
uv run pymarkdown -c .pymarkdown.yml scan docs/ README.md CONTRIBUTING.md
```

These checks run automatically via lefthook:

- **Pre-commit:** ruff format, ruff lint (with auto-fix), mypy, mdformat, pymarkdown
- **Pre-push:** full pytest suite, mypy strict

## Project Structure

```text
src/deep_diff/
├── cli/            # Typer CLI entry point
├── core/           # Comparator pipeline
│   ├── models.py       # Data models and enums
│   ├── filtering.py    # FileFilter (gitignore + globs)
│   ├── structure.py    # StructureComparator (file existence)
│   ├── content.py      # ContentComparator (hash-based)
│   ├── text.py         # TextComparator (line-by-line diffs)
│   ├── comparator.py   # Orchestrator
│   ├── plugins.py      # Plugin system
│   ├── snapshot.py     # Snapshot save/load
│   └── watcher.py      # File watcher
├── git/            # Git ref resolution and commands
├── output/         # Renderers (Rich, JSON, HTML)
├── plugins/        # Built-in plugins (JSON, YAML)
└── tui/            # Textual TUI application

tests/              # Mirrors src/ structure
├── fixtures/       # Test data directories
├── test_cli/
├── test_core/
├── test_git/
├── test_output/
├── test_plugins/
└── test_tui/
```

## Building and Installing

```bash
# Build the package
uv build

# Install as a CLI tool
uv tool install .

# Or install from the built wheel
uv tool install dist/deep_diff-*.whl
```
