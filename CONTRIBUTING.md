# Contributing to deep-diff

Thanks for your interest in contributing! This guide covers everything you need
to get started.

## Getting Started

See the [Development Guide](docs/DEVELOPMENT.md) for environment setup,
running the CLI, tests, and linting.

## How to Contribute

### Reporting Bugs

Open a [bug report](https://github.com/jsamuelsen11/deep-diff/issues/new?template=bug_report.yml)
with steps to reproduce, expected vs actual behavior, and your environment details.

### Suggesting Features

Open a [feature request](https://github.com/jsamuelsen11/deep-diff/issues/new?template=feature_request.yml)
describing the problem you're solving and your proposed approach.

### Submitting Code

1. Fork the repository and create a branch from `main`
1. Make your changes following the coding standards below
1. Add or update tests as needed
1. Ensure all checks pass locally (`uv run pytest`, `uv run mypy src/ --strict`)
1. Open a pull request using the PR template

## Pull Request Process

- Branch from `main`, target `main` for your PR
- Fill out the PR template (What / Why / How / Testing)
- CI must pass (tests, lint, type check)
- One approval from a code owner is required

## Coding Standards

### General Patterns

- **Immutable results** — all result types are frozen dataclasses
- **Protocol over ABC** — renderers implement a `Protocol`, not inherit from `ABC`
- **Lazy imports** — TUI is only imported when `--output tui` is used
- **Layered enrichment** — each comparator stage builds on prior results without mutation

### StrEnum Naming

Avoid member names that shadow `str` methods. For example, `ChangeType` uses
`substitute` instead of `replace` to avoid conflicts under mypy strict.

### Import Conventions

Stdlib imports used only for type annotations must be inside a
`TYPE_CHECKING` block (ruff rule TCH003). Use `from __future__ import annotations`
and prefer `X | None` over `Optional[X]` (ruff rule UP045).

### Formatting and Linting

- **Formatter:** ruff (line length 100)
- **Linter:** ruff with rules E, W, F, I, N, UP, B, SIM, TCH, RUF
- **Type checker:** mypy in strict mode, targeting Python 3.11

These run automatically via lefthook on commit and push.

## Testing

- Tests live in `tests/`, mirroring the `src/deep_diff/` structure
- Use shared fixtures from `tests/conftest.py` and `tests/fixtures/`
- Coverage threshold is **80%** (enforced in `pyproject.toml`)
- Run with coverage: `uv run pytest --cov=deep_diff --cov-report=term-missing`

## Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Use |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `chore:` | Maintenance, config |
| `ci:` | CI/CD changes |
| `test:` | Test additions or fixes |
| `refactor:` | Code restructuring (no behavior change) |

Example: `feat: add YAML plugin for structural diffing`

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE).
