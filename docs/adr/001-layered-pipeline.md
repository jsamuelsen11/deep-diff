# ADR-001: Layered Comparator Pipeline with Frozen Dataclasses

## Status

Accepted

## Date

2025-01-01

## Context

deep-diff needs to compare files/directories at multiple depth levels
(structure, content, text). These levels are inherently incremental — content
comparison requires knowing which files exist (structure), and text diffing
requires knowing which files are modified (content).

We needed a design that:

- Allows users to stop at any depth level without wasted computation
- Makes results easy to test, serialize, and pass between components
- Avoids mutation bugs in a pipeline with multiple stages

## Decision

Use a layered pipeline where each comparator stage produces new frozen
dataclass instances that enrich the results of the previous stage:

1. `StructureComparator` walks both trees, produces `FileComparison` objects
1. `ContentComparator` takes structure results, hashes files, returns new
   `FileComparison` objects with updated status and hash fields
1. `TextComparator` takes content results, generates diffs, returns new
   `FileComparison` objects with populated `hunks`

The `Comparator` orchestrator chains only the stages needed for the requested
depth. All result types (`DiffResult`, `FileComparison`, `Hunk`, `TextChange`,
`DiffStats`) are frozen dataclasses.

## Consequences

**Positive:**

- Each stage is independently testable with known inputs/outputs
- Frozen dataclasses prevent accidental mutation between stages
- Users get fast results at shallow depths (structure is near-instant)
- Results are trivially serializable (JSON, snapshot files)

**Negative:**

- Creating new objects at each stage has a small memory overhead compared to
  in-place mutation (negligible in practice for typical directory sizes)
- Adding a new depth level requires creating a new comparator class and wiring
  it into the orchestrator

## Alternatives Considered

- **Mutable result objects** — simpler code but prone to mutation bugs and
  harder to test stage isolation
- **Single-pass comparator** — would always do full text diffing even when
  only structure is requested, wasting computation
- **Visitor pattern** — more complex with no clear benefit for a linear pipeline
