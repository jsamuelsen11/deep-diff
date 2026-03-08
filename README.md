# Compare files and directories with clarity

![deep-diff](docs/images/deepDiffLogo.png)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/downloads/)
[![Coverage 80%+](https://img.shields.io/badge/coverage-80%25+-brightgreen)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-d4aa00)](https://docs.astral.sh/ruff/)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue)](https://mypy-lang.org/)
[![Built with: uv](https://img.shields.io/badge/built%20with-uv-purple)](https://docs.astral.sh/uv/)

A Python CLI/TUI tool that performs diff operations at multiple depth levels --
from simple "what files exist" to full text diffs with syntax highlighting.

## Features

- **Structure comparison** -- which files exist in each directory (contents don't matter)
- **Content comparison** -- which files are identical vs modified (hash-based)
- **Text comparison** -- line-by-line diffs with context and syntax highlighting
- **Smart defaults** -- respects `.gitignore`, ignores hidden files, auto-detects depth
- **Multiple outputs** -- Rich terminal, interactive TUI, JSON, HTML export
- **Flexible filtering** -- glob include/exclude, gitignore override, hidden file toggle

## Installation

```bash
# Install from source with uv
uv tool install .

# Or run directly during development
uv run deep-diff --help
```

## Usage

```bash
# Compare two directories (auto-detects: structure comparison)
deep-diff src/ other-src/

# Compare two files (auto-detects: text diff)
deep-diff file_a.py file_b.py

# Explicit depth levels
deep-diff src/ other-src/ --depth structure   # which files exist
deep-diff src/ other-src/ --depth content     # binary same/different
deep-diff src/ other-src/ --depth text        # full text diffs

# Short form
deep-diff src/ other-src/ -d s    # structure
deep-diff src/ other-src/ -d c    # content
deep-diff src/ other-src/ -d t    # text

# Output modes
deep-diff src/ other-src/ --output tui     # interactive TUI
deep-diff src/ other-src/ --output json    # machine-readable JSON
deep-diff src/ other-src/ --output html    # HTML export

# Filtering
deep-diff src/ other-src/ --no-gitignore       # don't respect .gitignore
deep-diff src/ other-src/ --hidden             # include hidden files
deep-diff src/ other-src/ --include "*.py"     # only Python files
deep-diff src/ other-src/ --exclude "*.pyc"    # exclude compiled files

# Other options
deep-diff src/ other-src/ --stat               # summary statistics only
deep-diff src/ other-src/ --context 5          # 5 lines of context (text depth)
deep-diff src/ other-src/ --hash md5           # use MD5 instead of SHA-256
```

## Defaults

| Setting | Default | Override |
|---------|---------|---------|
| Respect .gitignore | Yes | `--no-gitignore` |
| Include hidden files | No | `--hidden` |
| Depth (directories) | structure | `--depth content\|text` |
| Depth (files) | text | `--depth structure\|content` |
| Output mode | rich | `--output tui\|json\|html` |
| Context lines | 3 | `--context N` |
| Hash algorithm | sha256 | `--hash ALGO` |

## Documentation

For the full user guide, see **[docs/userGuide](docs/userGuide/README.md)**. Highlights:

- [Depth Levels](docs/userGuide/depth-levels.md) -- structure vs content vs text
- [Output Modes](docs/userGuide/output-modes.md) -- Rich, TUI, JSON, HTML
- [Filtering](docs/userGuide/filtering.md) -- gitignore, hidden files, include/exclude globs
- [Git Refs](docs/userGuide/git-refs.md) -- compare branches, tags, and commits
- [Watch Mode](docs/userGuide/watch-mode.md) -- live re-diffing on file changes
- [Snapshots](docs/userGuide/snapshots.md) -- save results, compare against baselines
- [Plugins](docs/userGuide/plugins.md) -- JSON/YAML structural diffing
- [Quick Reference](docs/userGuide/quick-reference.md) -- all flags + copy-paste recipes

## Development

```bash
# Install dependencies (including dev group)
uv sync --all-groups

# Run the CLI
uv run deep-diff --help

# Run tests
uv run pytest

# Run linter
uv run ruff check src/

# Run formatter
uv run ruff format src/

# Run type checker
uv run mypy src/

# Install git hooks (requires lefthook)
lefthook install
```

## Architecture

deep-diff uses a layered comparison pipeline:

```mermaid
graph TD
    CLI["🖥️ CLI (Typer)"]:::entry --> Filter

    subgraph Comparator["⚙️ Comparator Pipeline"]
        Filter["FileFilter\n(gitignore + globs + hidden files)"]:::filter
        Structure["StructureComparator\n(file existence)"]:::compare
        Content["ContentComparator\n(hash-based identity)"]:::compare
        Text["TextComparator\n(line-by-line diffs)"]:::compare
        Filter --> Structure --> Content --> Text
    end

    Text --> Result["📦 DiffResult"]:::result

    subgraph Renderer["🎨 Renderers"]
        Rich["Rich"]:::render
        TUI["TUI"]:::render
        JSON["JSON"]:::render
        HTML["HTML"]:::render
    end

    Result --> Rich
    Result --> TUI
    Result --> JSON
    Result --> HTML

    classDef entry fill:#6366f1,stroke:#4f46e5,color:#fff,font-weight:bold
    classDef filter fill:#f59e0b,stroke:#d97706,color:#fff
    classDef compare fill:#3b82f6,stroke:#2563eb,color:#fff
    classDef result fill:#10b981,stroke:#059669,color:#fff,font-weight:bold
    classDef render fill:#8b5cf6,stroke:#7c3aed,color:#fff

    style Comparator fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,color:#1e40af
    style Renderer fill:#f5f3ff,stroke:#8b5cf6,stroke-width:2px,color:#5b21b6
```

Each stage produces immutable results. Higher stages enrich lower-stage results without mutation.

## License

MIT
