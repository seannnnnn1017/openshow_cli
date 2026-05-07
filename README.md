# Obsidian CLI

A small terminal UI prototype for browsing and editing a local Markdown vault.

The left navigation renders the vault in a tree-style layout:

```text
database/
├── index.md
├── projects/
│   └── todo-app.md
└── python-basics.md
```

## Run

```bash
python3 obsidian_cli.py database
```

## Keys

- `Tab`: show or hide the left navigation tree
- `Up` / `Down`: move through the navigation tree when it is visible
- `Enter`: open the selected note, or expand/collapse the selected folder
- `Mouse click`: open notes or expand/collapse folders from the tree
- `Mouse click`: follow visible wiki links in the viewer
- `Mouse wheel`: scroll the navigation tree or the viewer
- `Ctrl+E`: enter edit mode, or return to viewer from edit mode
- `Ctrl+S`: save while editing
- `Ctrl+F`: find text in the current note
- `n`: jump to the next find result
- `t`: open or close the right-side table of contents
- `Enter`: jump to the selected heading while the table of contents is open
- `q`: quit from viewer mode

## Markdown Links

The viewer recognizes Obsidian-style wiki links:

```markdown
[[python-basics]]
[[data-structures#Hash Table]]
[[projects/todo-app|Todo App]]
```

Click a rendered link in the viewer to jump to the target note. When the sidebar
is hidden, pressing `Enter` follows the first link on the currently visible top
line.

## Markdown Preview

The preview is inspired by Leaf's terminal Markdown presentation style:

- YAML frontmatter renders as a compact metadata block
- Headings, blockquotes, code blocks, rules, lists, and tables get distinct terminal styling
- Markdown tables are aligned without borders to avoid terminal width glitches
- Inline emphasis markers are cleaned up for preview readability
