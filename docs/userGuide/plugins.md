# Plugins

Plugins provide file-type-aware comparison. Instead of diffing raw text,
a plugin can normalize the file's structure first — so cosmetic changes
(like key reordering in JSON) don't show up as diffs.

Plugins only apply at `--depth text`.

## Built-in Plugins

deep-diff ships with two plugins:

| Plugin | Extensions | What It Does |
|--------|-----------|--------------|
| `json` | `.json` | Normalizes keys + indentation before diffing. Key reorder = no diff. |
| `yaml` | `.yaml`, `.yml` | Converts to sorted JSON then diffs. Formatting and key order ignored. |

Both plugins **fall back to raw text diff** if parsing fails (e.g., invalid JSON/YAML).

## Listing Available Plugins

```bash
deep-diff --list-plugins
```

```text
  json: .json
  yaml: .yaml, .yml
```

## Using Plugins

By default, all installed plugins are active. When you compare at `--depth text`,
files with matching extensions are automatically routed through the plugin.

```bash
# JSON plugin kicks in automatically for .json files
deep-diff config/ staging/ -d text
```

### Enable only specific plugins

Use `--plugin` (or `-P`) to whitelist specific plugins. Only named plugins will be active:

```bash
# Only use the JSON plugin, skip YAML
deep-diff config/ staging/ -d text --plugin json

# Enable multiple plugins explicitly
deep-diff config/ staging/ -d text -P json -P yaml
```

### Disable all plugins

```bash
deep-diff config/ staging/ -d text --no-plugins
```

All files are compared as raw text, regardless of extension.

### Mutual exclusivity

`--plugin` and `--no-plugins` cannot be used together:

```bash
# This is an error
deep-diff config/ staging/ --plugin json --no-plugins
```

```text
Error: --no-plugins and --plugin are mutually exclusive.
```

## How Plugins Work

When a plugin is active and a file's extension matches:

1. The plugin reads both files
1. It parses and normalizes the content (e.g., sorted keys, consistent indent)
1. It diffs the normalized versions
1. The result is a standard `FileComparison` — identical to what the default text comparator produces

This means plugin results render the same way in all output modes (rich, TUI, JSON, HTML).

## Writing Custom Plugins

Plugins are discovered via Python entry points. To create your own:

1. Write a class that satisfies the `FileTypePlugin` protocol:

   - `name` property (str)
   - `extensions` property (tuple of strings with leading dots)
   - `compare(left, right, *, relative_path, context_lines)` method returning `FileComparison`

1. Register it in your package's `pyproject.toml`:

```toml
[project.entry-points."deep_diff.plugins"]
my_plugin = "my_package.my_module:MyPlugin"
```

1. Install your package and deep-diff will discover it automatically.

______________________________________________________________________

Next: [Advanced](advanced.md) | [Back to Guide](README.md)
