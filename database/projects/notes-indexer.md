---
title: Notes Indexer
tags: [project, markdown, search, graph]
created: 2026-05-08
status: prototype
---

# Notes Indexer

Back to [[index]].

The notes indexer scans markdown files, extracts wiki links, and builds lookup tables for search and graph navigation.

## Responsibilities

- Read markdown files with [[python-basics#File Handling]]
- Store note metadata in a [[data-structures#Hash Table]]
- Extract links and backlinks
- Support search across rendered text
- Feed local graph views with one-level and two-level relationships

## Index Shape

```python
notes_by_stem = {
    "python-basics": "database/python-basics.md",
    "algorithms": "database/algorithms.md",
}
```

## Link Graph

The indexer treats every wiki link as a directed edge:

```text
source note -> target note
```

This is the same model described in [[data-structures#Graphs]] and traversed with [[algorithms#Graph Traversal]].

## Testing Focus

- Link resolution
- Missing note handling
- Search results
- Backlink collection

See [[concepts/testing]] and [[patterns/error-handling]].

## Related Notes

- [[patterns/refactoring]] - Splitting parsing, indexing, and rendering
- [[patterns/cli-design]] - Exposing search through a small command surface
- [[concepts/complexity]] - Understanding scan cost across a large vault
