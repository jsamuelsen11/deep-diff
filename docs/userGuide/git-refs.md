# Comparing Git History

deep-diff can compare snapshots from your git history using the `git:` prefix.
No need to check out branches or create temp copies — deep-diff handles it.

## Syntax

Prefix any argument with `git:` to reference a git commit, branch, or tag:

```text
deep-diff git:<ref> git:<ref>
deep-diff git:<ref> <path>
deep-diff <path> git:<ref>
```

Supported ref formats:

- Branch names: `git:main`, `git:feature/auth`
- Tags: `git:v1.0`, `git:release-2024`
- Commit SHAs: `git:abc123`
- Relative refs: `git:HEAD~2`, `git:main~5`

## Examples

### Compare two branches

```bash
deep-diff git:main git:feature/new-api --depth text
```

Extracts the full file tree from each branch into temp directories, then diffs them.

### Compare a branch to your working tree

```bash
deep-diff git:main src/
```

Useful for seeing everything that changed since you branched off.

### Compare two commits

```bash
deep-diff git:HEAD~3 git:HEAD
```

See what changed in the last 3 commits.

### Compare a tag to current

```bash
deep-diff git:v1.0 src/ --depth content
```

Check which files changed since the v1.0 release.

## How It Works

When you use a `git:` ref, deep-diff:

1. Validates the ref exists (`git rev-parse`)
1. Extracts the full file tree to a temporary directory (`git ls-tree` + `git show`)
1. Runs the normal comparison against the temp directory
1. Cleans up the temp directory when done

Both arguments can be git refs, or you can mix a git ref with a filesystem path.

## Requirements

- You must be inside a git repository (or a subdirectory of one)
- The ref must be valid and resolvable

## Limitations

- `--watch` cannot be used with git refs (git history doesn't change on disk)
- Submodule entries are skipped

______________________________________________________________________

Next: [Watch Mode](watch-mode.md) | [Back to Guide](README.md)
