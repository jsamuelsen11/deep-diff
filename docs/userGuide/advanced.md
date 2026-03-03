# Advanced Options

## Parallel Workers

deep-diff processes file comparisons in parallel by default. The `--workers` flag (or `-w`) controls thread pool size.

```bash
# Auto (default) — uses min(32, cpu_count + 4) threads
deep-diff src/ other-src/ -d content

# Serial — single-threaded, useful for debugging
deep-diff src/ other-src/ -d content -w 1

# Explicit — set to 8 threads
deep-diff src/ other-src/ -d content -w 8
```

| Value | Behavior |
|-------|----------|
| `0` (default) | Auto-detect based on CPU count |
| `1` | Serial execution, no thread pool |
| `N > 1` | Exactly N worker threads |

Parallelism applies to content and text depth only.
Structure comparison is always single-threaded (it's just a directory walk).

## Hash Algorithm

At `--depth content`, files are hashed to determine identity. The default algorithm is SHA-256.

```bash
# Use MD5 (faster, less collision-resistant)
deep-diff src/ other-src/ -d content --hash md5

# Use SHA-1
deep-diff src/ other-src/ -d content --hash sha1
```

Any algorithm supported by Python's `hashlib` module works: `md5`, `sha1`, `sha256`, `sha512`, `blake2b`, etc.

## Context Lines

At `--depth text`, context lines surround each change in the unified diff. The default is 3.

```bash
# More context
deep-diff old.py new.py --context 10
# Short form
deep-diff old.py new.py -C 10

# No context (changes only)
deep-diff old.py new.py -C 0
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success — comparison completed |
| `1` | User error — invalid flags, unknown plugin, bad combination |
| `2` | Runtime error — file not found, git error, invalid snapshot |

Use exit codes in scripts:

```bash
deep-diff src/ other-src/ -d content --baseline expected.json
if [ $? -ne 0 ]; then
    echo "Diff baseline check failed"
    exit 1
fi
```

______________________________________________________________________

Next: [Quick Reference](quick-reference.md) | [Back to Guide](README.md)
