---
title: Todo App
tags: [project, python, cli]
created: 2026-05-05
status: in-progress
---

# Todo App

Back to [[index]].

This project is a small command-line task manager written in [[python-basics|Python]].

## Goals

- Store tasks locally
- List tasks in priority order
- Mark tasks as complete
- Keep the command syntax predictable

## Technical Choices

- Language: [[python-basics]]
- Storage: JSON files backed by a [[data-structures#Hash Table]]
- Sorting: priority sort inspired by [[algorithms#Sorting]]
- Interface: command patterns from [[patterns/cli-design]]
- Validation: defensive checks from [[patterns/error-handling]]

## Draft Data Model

```python
from dataclasses import dataclass

@dataclass
class Task:
    title: str
    priority: int = 0
    done: bool = False
```

## Command Examples

```text
todo add "Write graph view" --priority 2
todo list --open
todo done 3
```

## Related Notes

- [[projects/notes-indexer]] - Another CLI project with file scanning
- [[concepts/testing]] - Testing command behavior
- [[patterns/refactoring]] - Keeping the command handlers small
