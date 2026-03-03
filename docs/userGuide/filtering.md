# Filtering

deep-diff gives you fine-grained control over which files are included in the comparison.

## Defaults

Out of the box, deep-diff:

- **Respects `.gitignore`** rules (including nested `.gitignore` files)
- **Hides hidden files** (anything starting with `.`)

This means `node_modules/`, `.git/`, `__pycache__/`, and similar noise are excluded automatically.

## Gitignore Control

### Disable gitignore filtering

```bash
deep-diff src/ other-src/ --no-gitignore
```

Ignores all `.gitignore` files. Everything that isn't hidden will be included.

## Hidden Files

### Include hidden files and directories

```bash
deep-diff src/ other-src/ --hidden
```

Includes dotfiles like `.env`, `.github/`, `.eslintrc`, etc. Without this flag, they're skipped entirely.

Combine with `--no-gitignore` to see absolutely everything:

```bash
deep-diff src/ other-src/ --hidden --no-gitignore
```

## Include Patterns

Restrict the comparison to files matching specific glob patterns.
Only files that match **at least one** include pattern are kept.

```bash
# Only Python files
deep-diff src/ other-src/ --include "*.py"

# Short form
deep-diff src/ other-src/ -I "*.py"

# Multiple patterns (repeatable)
deep-diff src/ other-src/ -I "*.py" -I "*.pyi"
```

Patterns are matched against the **relative path** from the directory root using standard glob syntax (`*`, `?`, `[...]`).

## Exclude Patterns

Remove specific files from the comparison. Files matching **any** exclude pattern are dropped.

```bash
# Skip compiled Python files
deep-diff src/ other-src/ --exclude "*.pyc"

# Short form
deep-diff src/ other-src/ -E "*.pyc"

# Multiple patterns
deep-diff src/ other-src/ -E "*.pyc" -E "*.pyo" -E "*.egg-info"
```

## Filter Order

Filters are applied in this order. Each stage narrows the set:

```text
All files
  │
  ├─ 1. Hidden filter     (skip dotfiles unless --hidden)
  ├─ 2. Gitignore filter   (skip .gitignore matches unless --no-gitignore)
  ├─ 3. Include filter     (keep only matching files, if any -I given)
  └─ 4. Exclude filter     (drop matching files, if any -E given)
  │
  v
Files to compare
```

This means exclude always wins over include. If a file matches both `-I "*.py"` and `-E "test_*.py"`, it is excluded.

## Examples

### Compare only YAML config files

```bash
deep-diff deploy/ staging/ -I "*.yaml" -I "*.yml"
```

### Compare everything except tests

```bash
deep-diff src/ other-src/ -E "test_*" -E "*_test.py" -E "tests/*"
```

### Include hidden files but still respect gitignore

```bash
deep-diff src/ other-src/ --hidden
```

### See absolutely everything (no filtering at all)

```bash
deep-diff src/ other-src/ --hidden --no-gitignore
```

______________________________________________________________________

Next: [Git Refs](git-refs.md) | [Back to Guide](README.md)
