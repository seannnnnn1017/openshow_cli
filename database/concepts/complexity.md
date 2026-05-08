---
title: Complexity
tags: [complexity, algorithms, performance]
created: 2026-05-08
---

# Complexity

Back to [[index]].

Complexity describes how runtime or memory grows as input size increases.

## Common Classes

| Class | Name | Example |
|-------|------|---------|
| O(1) | Constant | Hash table lookup |
| O(log n) | Logarithmic | Binary search |
| O(n) | Linear | Scanning notes |
| O(n log n) | Linearithmic | Efficient sorting |
| O(n^2) | Quadratic | Comparing all pairs |

## Practical Notes

Big-O ignores constants, but constants still matter in small command-line tools. A clear O(n) scan may be better than a complex cache until the dataset grows.

## Examples in This Vault

- [[algorithms#Binary Search]] demonstrates O(log n).
- [[data-structures#Hash Table]] demonstrates average O(1) lookup.
- [[projects/notes-indexer]] scans files and builds indexes.
- [[patterns/refactoring]] helps isolate performance-sensitive code.

## Related Notes

- [[algorithms]]
- [[data-structures]]
- [[concepts/testing]]
