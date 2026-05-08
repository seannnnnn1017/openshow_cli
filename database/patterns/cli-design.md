---
title: CLI Design
tags: [cli, ux, design]
created: 2026-05-08
---

# CLI Design

Back to [[index]].

Good command-line tools are predictable, forgiving, and easy to inspect.

## Command Shape

Commands should use consistent verbs:

```text
notes search "graph"
notes open python-basics
notes graph --depth 2
```

The [[projects/todo-app]] follows the same pattern with `add`, `list`, and `done`.

## Feedback

Every command should make its result clear:

- What changed
- What failed
- What the user can do next

Errors should follow [[patterns/error-handling]].

## Navigation

Terminal interfaces need compact movement rules:

- Arrow keys for selection
- Enter for activation
- Escape for returning
- Tab for switching panes

This pattern appears in [[projects/notes-indexer]] and the graph viewer.

## Related Notes

- [[python-basics]]
- [[concepts/testing]]
- [[patterns/refactoring]]
