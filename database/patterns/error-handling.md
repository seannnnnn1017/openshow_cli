---
title: Error Handling
tags: [errors, validation, reliability]
created: 2026-05-08
---

# Error Handling

Back to [[index]].

Error handling turns unexpected input into clear behavior.

## Common Cases

- Missing files
- Invalid command arguments
- Empty search terms
- Broken wiki links
- Unsupported terminal features

These cases appear in [[projects/notes-indexer]] and [[projects/todo-app]].

## Validation Pattern

```python
def require_note(name, notes):
    if name not in notes:
        raise ValueError(f"Unknown note: {name}")
    return notes[name]
```

Keep validation close to the boundary where user input enters the program.

## User-Facing Messages

Good messages are specific:

```text
Unknown note: architecture.md
```

Vague messages make debugging harder:

```text
Error
```

## Related Notes

- [[patterns/cli-design]] - Presenting errors consistently
- [[concepts/testing]] - Testing invalid input
- [[patterns/refactoring]] - Isolating validation code
