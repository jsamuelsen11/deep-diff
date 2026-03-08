# ADR-002: Protocol Over ABC for Renderers

## Status

Accepted

## Date

2025-01-01

## Context

deep-diff supports multiple output formats (Rich terminal, TUI, JSON, HTML)
and needs an extensible renderer interface. We needed to decide between
abstract base classes (`ABC`) and structural subtyping (`Protocol`) for
defining the renderer contract.

Renderers have two main methods:

- `render(result: DiffResult) -> None` — write diff output
- `render_stats(stats: DiffStats) -> None` — write summary statistics

A secondary `WatchRenderer` protocol adds methods for building Rich
renderables for live-updating watch mode.

## Decision

Use `typing.Protocol` with `@runtime_checkable` instead of ABC inheritance.

```python
@runtime_checkable
class Renderer(Protocol):
    def render(self, result: DiffResult) -> None: ...
    def render_stats(self, stats: DiffStats) -> None: ...
```

## Consequences

**Positive:**

- Any class with the right method signatures is a valid renderer — no need
  to import or inherit from a base class
- Third-party renderers can be added without depending on deep-diff internals
- Works naturally with mypy's structural type checking
- `@runtime_checkable` allows `isinstance()` checks when needed

**Negative:**

- No built-in mechanism for shared default behavior (unlike ABC with concrete
  methods). Not needed here since renderers have no shared logic.
- Slightly less discoverable for contributors unfamiliar with Protocol

## Alternatives Considered

- **ABC with abstract methods** — requires inheritance coupling, makes
  third-party renderers depend on deep-diff's base class
- **Duck typing without Protocol** — no static type checking, harder to
  document the expected interface
