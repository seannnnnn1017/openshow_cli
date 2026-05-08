---
title: Python Basics
tags: [python, programming, basics]
created: 2026-05-01
updated: 2026-05-08
---

# Python Basics

Back to [[index]].

Python is a dynamic language with a compact syntax. It is useful for scripts, command-line tools, data processing, and automation.

## Variables and Types

Common built-in types:

- `int`, `float`, `str`, `bool`
- `list`, `dict`, `tuple`, `set`
- `None` for missing values

## Functions

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

Small functions make command-line tools easier to test. See [[concepts/testing]] for test structure.

## List Comprehension

```python
squares = [x**2 for x in range(10)]
filtered = [x for x in squares if x > 10]
```

List comprehensions are used in [[algorithms#Quick Sort]] and in [[projects/notes-indexer]] when building search results.

## File Handling

```python
from pathlib import Path

path = Path("notes.md")
text = path.read_text(encoding="utf-8")
path.write_text(text.strip() + "\n", encoding="utf-8")
```

File handling is the base of [[projects/todo-app]] and [[projects/notes-indexer]].

## Related Notes

- [[data-structures]] - Built-in containers and their tradeoffs
- [[algorithms]] - Algorithms implemented in Python
- [[patterns/error-handling]] - Handling invalid input and missing files
- [[patterns/cli-design]] - Building a predictable command-line interface
