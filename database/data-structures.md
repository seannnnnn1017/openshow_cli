---
title: Data Structures
tags: [data-structures, computer-science]
created: 2026-05-02
updated: 2026-05-08
---

# Data Structures

Back to [[index]].

Data structures organize values so programs can access, update, and traverse information efficiently.

## Linear Structures

| Structure | Access | Insert | Delete | Common Use |
|-----------|--------|--------|--------|------------|
| Array | O(1) | O(n) | O(n) | Indexed sequences |
| Linked List | O(n) | O(1) | O(1) | Frequent local insertion |
| Stack | O(n) | O(1) | O(1) | Undo, parsing, DFS |
| Queue | O(n) | O(1) | O(1) | Scheduling, BFS |

Stacks and queues appear in [[algorithms#Graph Traversal]].

## Hash Table

A hash table stores key-value pairs. Average lookup is O(1), assuming a good hash function and manageable collisions.

```python
cache = {}
cache["note.md"] = {"title": "Note", "links": []}
print(cache.get("note.md", {}))
```

Hash tables are used by [[projects/notes-indexer]] to resolve links quickly.

## Trees

Trees represent parent-child relationships:

- File trees
- Abstract syntax trees
- Search trees
- Hierarchical menus

The navigation pane in this project is a tree, while [[patterns/cli-design]] explains how users move through it.

## Graphs

A graph contains nodes and edges. Markdown notes form a graph when one note links to another.

- Nodes: notes
- Edges: wiki links
- Incoming edges: backlinks
- Outgoing edges: links

The graph viewer uses concepts from [[algorithms#Graph Traversal]] and [[concepts/complexity]].

## Related Notes

- [[python-basics]] - Python container syntax
- [[algorithms]] - Traversal and search over data structures
- [[concepts/complexity]] - Comparing runtime and memory costs
- [[projects/notes-indexer]] - Practical graph-like note indexing
