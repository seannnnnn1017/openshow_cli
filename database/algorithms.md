---
title: Algorithms
tags: [algorithms, computer-science]
created: 2026-05-03
updated: 2026-05-08
---

# Algorithms

Back to [[index]].

Algorithms are repeatable procedures for solving problems. The right choice depends on input size, constraints, and data shape.

## Sorting

### Quick Sort

Quick sort has average O(n log n) runtime and can be implemented compactly in Python.

```python
def quicksort(items):
    if len(items) <= 1:
        return items
    pivot = items[len(items) // 2]
    left = [x for x in items if x < pivot]
    mid = [x for x in items if x == pivot]
    right = [x for x in items if x > pivot]
    return quicksort(left) + mid + quicksort(right)
```

This example uses list comprehension from [[python-basics#List Comprehension]].

## Searching

### Binary Search

Binary search works on sorted sequences and runs in O(log n).

```python
def binary_search(items, target):
    low, high = 0, len(items) - 1
    while low <= high:
        mid = (low + high) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
```

For repeated lookup by key, a [[data-structures#Hash Table]] is usually simpler.

## Graph Traversal

Graphs can be traversed with depth-first search or breadth-first search.

```python
def walk(start, neighbors):
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for nxt in neighbors(node):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen
```

This traversal model is useful for [[projects/notes-indexer]] and for the graph tree view.

## Related Notes

- [[data-structures]] - Containers used by algorithms
- [[concepts/complexity]] - Runtime and memory analysis
- [[python-basics]] - Python implementation details
- [[projects/todo-app]] - Sorting tasks by priority
- [[projects/notes-indexer]] - Traversing note links
