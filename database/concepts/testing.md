---
title: Testing
tags: [testing, python, quality]
created: 2026-05-08
---

# Testing

Back to [[index]].

Tests give small tools confidence as features are added. The best tests focus on behavior rather than implementation details.

## Unit Tests

Use unit tests for pure functions:

- Link parsing
- Search result collection
- Slug generation
- Command argument parsing

These areas are used by [[projects/notes-indexer]] and [[patterns/cli-design]].

## Integration Tests

Integration tests are useful when code reads files, updates state, or coordinates several modules.

Good candidates:

- Loading a sample vault
- Resolving backlinks
- Saving edited notes
- Rendering a graph from note relationships

## Test Data

Small fixtures should include cycles and missing links:

```text
A -> B
B -> C
C -> A
D -> Missing
```

Cycles are important when testing [[algorithms#Graph Traversal]].

## Related Notes

- [[python-basics]] - Writing small testable functions
- [[patterns/error-handling]] - Testing invalid input
- [[patterns/refactoring]] - Making code easier to test
