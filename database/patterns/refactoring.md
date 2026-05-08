---
title: Refactoring
tags: [refactoring, design, maintenance]
created: 2026-05-08
---

# Refactoring

Back to [[index]].

Refactoring improves structure without intentionally changing behavior.

## When to Refactor

- A function has too many responsibilities
- Similar code appears in several places
- Tests are hard to write
- A new feature needs clearer boundaries

The [[projects/notes-indexer]] benefits from separating parsing, indexing, rendering, and input handling.

## Safe Refactoring Steps

1. Add or confirm tests.
2. Move one behavior at a time.
3. Keep public behavior stable.
4. Run the test suite after each meaningful change.

This works well with the testing approach in [[concepts/testing]].

## Example Split

```text
load files -> parse links -> build graph -> render view
```

Each step can become a small function with clear inputs and outputs.

## Related Notes

- [[python-basics]] - Writing small functions
- [[patterns/error-handling]] - Keeping validation focused
- [[patterns/cli-design]] - Preserving user-facing behavior
- [[concepts/complexity]] - Avoiding unnecessary work while restructuring
