# Quick Reference

## All Flags

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `<left>` | | *(required)* | Left path or `git:<ref>` |
| `<right>` | | *(required)* | Right path or `git:<ref>` |
| `--depth` | `-d` | auto | Comparison depth: `structure`, `content`, `text` (or `s`, `c`, `t`) |
| `--output` | `-o` | `rich` | Output mode: `rich`, `tui`, `json`, `html` |
| `--stat` | | off | Show summary statistics only |
| `--context` | `-C` | `3` | Context lines in text diffs |
| `--hash` | | `sha256` | Hash algorithm for content comparison |
| `--include` | `-I` | *(none)* | Glob pattern for files to include (repeatable) |
| `--exclude` | `-E` | *(none)* | Glob pattern for files to exclude (repeatable) |
| `--hidden` | | off | Include hidden files and directories |
| `--no-gitignore` | | off | Don't respect .gitignore rules |
| `--watch` | `-W` | off | Watch paths and re-diff on changes |
| `--debounce` | | `1600` | Watch debounce interval in ms (requires `--watch`) |
| `--workers` | `-w` | `0` (auto) | Parallel workers: 0=auto, 1=serial |
| `--save-snapshot` | | *(none)* | Save diff result as JSON snapshot |
| `--baseline` | | *(none)* | Compare against a previous snapshot |
| `--plugin` | `-P` | *(all)* | Enable only specific plugin(s) (repeatable) |
| `--no-plugins` | | off | Disable all file-type plugins |
| `--list-plugins` | | | List available plugins and exit |
| `--version` | `-V` | | Show version and exit |
| `--help` | | | Show help and exit |

## Recipes

### Compare two directories

```bash
deep-diff src/ other-src/
```

Auto-detects structure depth.

### Compare two files

```bash
deep-diff old.py new.py
```

Auto-detects text depth.

### Structure only — what files exist

```bash
deep-diff src/ other-src/ -d s
```

### Content — which files changed (hash-based)

```bash
deep-diff src/ other-src/ -d c
```

### Text — full line-by-line diffs

```bash
deep-diff src/ other-src/ -d t
```

### Filter to specific file types

```bash
deep-diff src/ other-src/ -I "*.py" -I "*.pyi"
```

### Exclude test files

```bash
deep-diff src/ other-src/ -E "test_*" -E "tests/*"
```

### Include hidden files

```bash
deep-diff src/ other-src/ --hidden
```

### Compare git branches

```bash
deep-diff git:main git:feature/auth -d text
```

### Compare working tree to a branch

```bash
deep-diff git:main src/
```

### Watch for changes

```bash
deep-diff src/ other-src/ -W
```

### Watch with fast debounce

```bash
deep-diff src/ other-src/ -W --debounce 500
```

### Export to JSON

```bash
deep-diff src/ other-src/ -d content -o json > diff.json
```

### Export to HTML

```bash
deep-diff src/ other-src/ -d text -o html > report.html
```

### Interactive TUI

```bash
deep-diff src/ other-src/ -d text -o tui
```

### Stats only

```bash
deep-diff src/ other-src/ --stat
```

### Save a snapshot

```bash
deep-diff src/ other-src/ -d content --save-snapshot baseline.json
```

### Compare against a baseline

```bash
deep-diff src/ other-src/ -d content --baseline baseline.json
```

### Save + baseline in one shot

```bash
deep-diff src/ other-src/ --baseline old.json --save-snapshot new.json
```

### Use only the JSON plugin

```bash
deep-diff config/ staging/ -d text -P json
```

### Disable all plugins

```bash
deep-diff config/ staging/ -d text --no-plugins
```

### Serial execution (no parallelism)

```bash
deep-diff src/ other-src/ -d content -w 1
```

### 8 parallel workers

```bash
deep-diff src/ other-src/ -d content -w 8
```

### 10 lines of context

```bash
deep-diff old.py new.py -C 10
```

### Use MD5 hashing

```bash
deep-diff src/ other-src/ -d content --hash md5
```

### See everything (no filtering)

```bash
deep-diff src/ other-src/ --hidden --no-gitignore
```
