---
title: Live Update Long Note
tags: [demo, live-update, longform]
created: 2026-05-08
---

# Live Update Long Note

This note was created to test automatic vault refresh while the terminal viewer is already running.

If the app is open, the left navigation tree should pick up this file after the next lightweight vault scan. The scan only compares file paths, modification timestamps, and file sizes before deciding whether a reload is needed.

## Purpose

The purpose of this document is to provide enough content to test scrolling, rendering, search, links, and the live update path at the same time.

It links back to [[index]], references the graph demo at [[demo_project/graph-center]], and mentions the indexing project in [[projects/notes-indexer]].

## Section 1: External File Changes

Automatic updates are useful when notes are edited outside the terminal UI. A user might change a markdown file in another editor, sync new files from another machine, or generate documentation from a script.

The viewer should not reload on every frame. Instead, it checks periodically and reloads only when the lightweight signature changes.

## Section 2: Memory Behavior

The update check avoids storing duplicate note bodies. It keeps a compact signature made of:

- Relative file path
- Nanosecond modification time
- File size

That is enough to detect normal markdown changes without holding another copy of every document in memory.

## Section 3: Navigation

After this file appears, it should be visible in the left navigation tree.

The file also gives search something larger to scan. Try searching for:

- `lightweight`
- `signature`
- `automatic updates`
- `graph demo`

## Section 4: Graph Connections

This note links to several existing notes:

- [[index]]
- [[demo_project/graph-center]]
- [[projects/notes-indexer]]
- [[concepts/testing]]
- [[patterns/refactoring]]

Those links should appear in graph and link panels after the vault reloads.

## Section 5: Long Body Text

Long markdown documents are common in note-taking systems. They may contain planning notes, design records, implementation details, meeting summaries, and working drafts.

The viewer should handle long content without changing the update strategy. Rendering happens only for the currently opened note, while the vault index holds just enough data to resolve note titles, links, and backlinks.

## Section 6: Expected Result

When this note is created:

1. The app detects a changed vault signature.
2. The status bar reports that the vault was reloaded.
3. The left navigation tree includes `live-update-long-note.md`.
4. Opening the note shows this long markdown content.
5. Graph and backlink data include the new relationships.

## Section 7: Manual Follow-Up

Edit this file externally and add another paragraph. The app should detect the modified timestamp and size on the next scan.

Delete this file externally after testing. The app should remove it from the navigation tree after the next scan.

## Closing

This document is intentionally verbose enough to make scroll behavior obvious while staying small enough to keep the demo lightweight.

## Live Edit Check

This paragraph was appended after the note was first created. If the terminal app is already open, the automatic update check should notice the changed file size and modification timestamp, reload the vault, and refresh the rendered markdown without restarting the program.

The new paragraph also links to [[patterns/error-handling]] so the link panel and graph data have one more relationship to refresh.
