# deep-diff User Guide

Compare files and directories with clarity — from simple "what files exist" to full text diffs with syntax highlighting.

## Quick Start

```bash
# Install
uv tool install .

# Compare two directories
deep-diff src/ other-src/

# Compare two files with full text diff
deep-diff old.py new.py --depth text
```

## Guide Contents

| Page | What You'll Learn |
|------|-------------------|
| [Getting Started](getting-started.md) | Installation, first run, auto-detection |
| [Depth Levels](depth-levels.md) | Structure vs content vs text comparison |
| [Output Modes](output-modes.md) | Rich terminal, TUI, JSON, HTML, stat-only |
| [Filtering](filtering.md) | Gitignore, hidden files, include/exclude globs |
| [Git Refs](git-refs.md) | Compare branches, tags, and commits |
| [Watch Mode](watch-mode.md) | Live re-diffing on file changes |
| [Snapshots](snapshots.md) | Save results, compare against baselines |
| [Plugins](plugins.md) | JSON/YAML structural diffing |
| [Advanced](advanced.md) | Workers, hash algorithms, context lines, exit codes |
| [Quick Reference](quick-reference.md) | All flags + copy-paste recipes |
