# Watch Mode

Watch mode monitors both paths for filesystem changes and automatically re-runs the diff,
updating the terminal output in place.

## Usage

```bash
deep-diff src/ other-src/ --watch
# Short form
deep-diff src/ other-src/ -W
```

The initial diff renders immediately. When any file in either path changes, the output refreshes in place.

```text
Watching src and other-src for changes... (CTRL+C to quit)

src vs other-src
├── + new_file.py
├──   shared.py
└── ~ config.py
```

<!-- screenshot: capture watch mode with the "Watching..." header visible -->

Press **CTRL+C** to stop watching.

## Debounce

By default, deep-diff waits 1600ms after the last filesystem event before re-diffing.
This prevents rapid re-renders when a build tool writes many files at once.

Adjust the debounce interval with `--debounce`:

```bash
# Faster response (500ms)
deep-diff src/ other-src/ -W --debounce 500

# Slower, for noisy file systems (3 seconds)
deep-diff src/ other-src/ -W --debounce 3000
```

`--debounce` requires `--watch`. Using it alone is an error.

## Works With

Watch mode pairs with other flags:

```bash
# Watch + stats only
deep-diff src/ other-src/ -W --stat

# Watch + text depth + extra context
deep-diff src/ other-src/ -W -d text --context 5

# Watch + filtering
deep-diff src/ other-src/ -W -I "*.py" --hidden
```

## Constraints

Watch mode has a few restrictions:

| Cannot combine with | Reason |
|---------------------|--------|
| `--output tui/json/html` | Only `--output rich` is supported (the default) |
| `git:` refs | Git history doesn't change on disk |
| `--save-snapshot` | Snapshots are a one-time capture |
| `--baseline` | Baseline comparison is a one-time operation |

______________________________________________________________________

Next: [Snapshots](snapshots.md) | [Back to Guide](README.md)
