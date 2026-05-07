# Viewer Background + Nav Popup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deep-blue background to the markdown viewer and auto-hide the sidebar with a centered popup overlay when the terminal is narrower than 80 columns.

**Architecture:** All changes are in `obsidian_cli.py`. New color pairs give the viewer a 256-color deep blue background. A new `"nav_popup"` mode drives a full-screen-covering, centered panel that reuses the existing `visible_tree()` logic. Tab key behavior branches on terminal width.

**Tech Stack:** Python 3.12, curses (stdlib), unicodedata (stdlib, already imported)

---

## File Map

| File | Changes |
|---|---|
| `obsidian_cli.py` | All changes below |

---

### Task 1: 256-color detection + new color pairs

**Files:**
- Modify: `obsidian_cli.py` — `init_terminal()` (line ~213), `App.__init__()` (line ~248), `App.run()` (line ~272)

**Context:** `init_terminal()` currently returns `None` and defines pairs 1–4 with `-1` (default terminal) as background. We need pairs with color 17 (xterm-256 dark blue, `#00005f`) as background when the terminal supports 256 colors, plus pair 5 for plain-text-on-deep-blue.

- [ ] **Step 1: Change `init_terminal()` to return `bool`**

Replace the entire `init_terminal` function:

```python
def init_terminal() -> bool:
    for setup in (
        curses.use_default_colors,
        lambda: curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION),
    ):
        try:
            setup()
        except curses.error:
            pass
    has_256 = False
    try:
        if curses.has_colors():
            curses.start_color()
            has_256 = curses.COLORS >= 256
            vbg = 17 if has_256 else -1  # xterm-256 dark blue, or terminal default
            curses.init_pair(1, curses.COLOR_CYAN, vbg)
            curses.init_pair(2, curses.COLOR_YELLOW, vbg)
            curses.init_pair(3, curses.COLOR_GREEN, vbg)
            curses.init_pair(4, curses.COLOR_MAGENTA, vbg)
            if has_256:
                curses.init_pair(5, -1, 17)  # default fg on deep blue (plain text + bg fill)
    except curses.error:
        pass
    return has_256
```

- [ ] **Step 2: Add `has_256_colors` + popup state to `App.__init__()`**

After `self.edit_scroll = 0` (line ~269), add:

```python
        self.has_256_colors = False
        self.popup_index = 0
        self.popup_scroll = 0
```

- [ ] **Step 3: Store return value of `init_terminal()` in `App.run()`**

Change:
```python
        init_terminal()
```
to:
```python
        self.has_256_colors = init_terminal()
```

- [ ] **Step 4: Verify syntax**

```bash
python3 -c "import py_compile; py_compile.compile('obsidian_cli.py'); print('OK')"
```
Expected: `OK`

---

### Task 2: Viewer deep-blue background fill

**Files:**
- Modify: `obsidian_cli.py` — `draw_viewer()` (line ~611)

**Context:** We need to (a) fill every viewer row with the deep-blue background color before rendering text, so empty lines also carry the color; and (b) use `color_pair(5)` as the base attribute for plain text so it renders on the deep-blue background. Other content types already use pairs 1–4 which now have the deep-blue background baked in (Task 1).

- [ ] **Step 1: Rewrite `draw_viewer()`**

Replace the entire method:

```python
    def draw_viewer(self, top: int, left: int, height: int, width: int) -> None:
        viewer_bg = curses.color_pair(5) if self.has_256_colors else curses.A_NORMAL
        if not self.current:
            safe_addstr(self.stdscr, top, left + 1, "No note", viewer_bg)
            return
        # Fill entire viewer area with background color
        blank = " " * max(0, width - 1)
        for y in range(top, top + height):
            safe_addstr(self.stdscr, y, left, blank, viewer_bg)
        title = f" {self.current.rel} "
        safe_addstr(self.stdscr, top, left, title[: max(1, width - 1)], curses.A_REVERSE)
        content_top = top + 1
        content_height = max(1, height - 1)
        self.view_scroll = min(self.view_scroll, max(0, len(self.rendered) - content_height))
        for offset in range(content_height):
            line_index = self.view_scroll + offset
            if line_index >= len(self.rendered):
                break
            line = self.rendered[line_index]
            attr = viewer_bg
            if line.kind == "heading":
                attr = curses.A_BOLD | curses.color_pair(2)
                if line.heading_level == 1:
                    attr |= curses.A_UNDERLINE
            elif line.kind == "code":
                attr = curses.A_DIM | curses.color_pair(3)
            elif line.kind in ("meta", "table"):
                attr = curses.color_pair(1)
            elif line.kind == "table_header":
                attr = curses.A_BOLD | curses.color_pair(1)
            elif line.kind == "quote":
                attr = curses.A_DIM | curses.color_pair(4)
            elif line.kind == "rule":
                attr = curses.A_DIM | viewer_bg
            if line_index in self.search_hits:
                attr |= curses.A_REVERSE
            text = line.text
            safe_addstr(self.stdscr, content_top + offset, left + 1, text[: max(1, width - 2)], attr)
            for start, end, _, _ in line.links:
                if start < width - 2:
                    link_text = text[start:end]
                    safe_addstr(
                        self.stdscr,
                        content_top + offset,
                        left + 1 + start,
                        link_text[: max(0, width - 2 - start)],
                        curses.A_UNDERLINE | curses.A_BOLD,
                    )
```

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "import py_compile; py_compile.compile('obsidian_cli.py'); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Manual smoke test**

```bash
python3 obsidian_cli.py database
```

Expected: Viewer area shows deep blue background. Headings yellow, code green, quotes magenta — all on deep blue. Empty lines below content are also deep blue (not terminal default).

If terminal shows no color change, it may not support 256 colors. Check: `echo $TERM` should show `xterm-256color` or similar.

---

### Task 3: Auto-hide sidebar + nav_popup mode dispatch

**Files:**
- Modify: `obsidian_cli.py` — `App.draw()` (line ~562), `App.run()` (line ~272)

**Context:** When `width < 80` the sidebar must be hidden automatically (Tab cannot re-enable it). When `width >= 80` and mode is `"nav_popup"`, auto-close the popup. The run loop needs a new dispatch branch for `"nav_popup"` mode.

- [ ] **Step 1: Update `draw()` — auto-hide logic and nav_popup branch**

Replace the entire `draw()` method:

```python
    def draw(self) -> None:
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()

        # Auto-hide sidebar when terminal is too narrow
        if width < 80:
            self.sidebar_visible = False
        # Close popup if terminal expanded back
        if self.mode == "nav_popup" and width >= 80:
            self.mode = "view"

        sidebar_width = min(34, max(22, width // 4)) if self.sidebar_visible else 0
        toc_width = min(30, max(20, width // 5)) if self.mode == "toc" and width >= 80 else 0
        body_height = max(1, height - 2)
        viewer_width = max(1, width - sidebar_width - toc_width)

        if self.mode == "nav_popup":
            self.draw_nav_popup(body_height, width)
        else:
            if self.sidebar_visible:
                self.draw_sidebar(0, 0, body_height, sidebar_width)
            if self.mode == "edit":
                self.draw_editor(0, sidebar_width, body_height, width - sidebar_width)
            else:
                self.draw_viewer(0, sidebar_width, body_height, viewer_width)
                if self.mode == "toc":
                    if toc_width:
                        self.draw_toc_sidebar(0, sidebar_width + viewer_width, body_height, toc_width)
                    else:
                        self.draw_toc_inline_notice(height, width)

        self.draw_status(height - 2, width)
        self.draw_help(height - 1, width)
        self.stdscr.refresh()
```

- [ ] **Step 2: Update `run()` — add nav_popup dispatch**

Replace:
```python
            if self.mode == "edit":
                self.handle_edit_key(key)
            elif self.mode == "toc":
                self.handle_toc_key(key)
            else:
                self.handle_view_key(key)
```
with:
```python
            if self.mode == "edit":
                self.handle_edit_key(key)
            elif self.mode == "toc":
                self.handle_toc_key(key)
            elif self.mode == "nav_popup":
                self.handle_nav_popup_key(key)
            else:
                self.handle_view_key(key)
```

- [ ] **Step 3: Verify syntax**

```bash
python3 -c "import py_compile; py_compile.compile('obsidian_cli.py'); print('OK')"
```
Expected: `OK`

---

### Task 4: Tab key behavior in `handle_view_key()`

**Files:**
- Modify: `obsidian_cli.py` — `handle_view_key()` (line ~719)

**Context:** Tab (code 9) currently toggles `sidebar_visible`. When `width < 80`, it should instead open the nav popup. We read `width` from `stdscr.getmaxyx()` at the point of handling.

- [ ] **Step 1: Replace the Tab branch in `handle_view_key()`**

Change:
```python
        elif code == 9:
            self.sidebar_visible = not self.sidebar_visible
```
to:
```python
        elif code == 9:
            _, width = self.stdscr.getmaxyx()
            if width < 80:
                self.mode = "nav_popup"
                self.popup_index = self.index_for_note(self.current)
                self.popup_scroll = max(0, self.popup_index - 5)
            else:
                self.sidebar_visible = not self.sidebar_visible
```

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "import py_compile; py_compile.compile('obsidian_cli.py'); print('OK')"
```
Expected: `OK`

---

### Task 5: `draw_nav_popup()` method

**Files:**
- Modify: `obsidian_cli.py` — add method after `draw_toc_inline_notice()` (~line 707)

**Context:** Draws a solid-color full-screen fill (same deep blue as viewer background), then a centered bordered panel with title, tree items, and a help bar. Uses `visible_tree()` and `tree_prefix()` so folder structure respects current collapse state. `popup_index` / `popup_scroll` track selection within the popup independently of the sidebar's `nav_index`.

Panel structure (rows relative to `panel_y`):
```
0: ┌────────────────────┐   top border
1: │ 📂 vault/          │   title (bold)
2: ├────────────────────┤   separator
3…n+2: │ tree items     │   one per item
n+3: ├────────────────────┤   separator
n+4: │ ↑↓ Enter Esc     │   help (dim)
n+5: └────────────────────┘   bottom border
total panel_h = content_h + 6
```

- [ ] **Step 1: Add `draw_nav_popup()` after `draw_toc_inline_notice()`**

```python
    def draw_nav_popup(self, body_height: int, width: int) -> None:
        viewer_bg = curses.color_pair(5) if self.has_256_colors else curses.A_NORMAL

        # Solid background fill
        blank = " " * max(0, width - 1)
        for y in range(body_height):
            safe_addstr(self.stdscr, y, 0, blank, viewer_bg)

        visible_tree = self.visible_tree()
        panel_w = min(52, max(30, width - 4))
        inner_w = panel_w - 2  # width between the two border chars

        max_items = max(1, body_height - 8)
        content_h = min(len(visible_tree), max_items)
        panel_h = content_h + 6
        panel_x = max(0, (width - panel_w) // 2)
        panel_y = max(0, (body_height - panel_h) // 2)

        # Clamp and scroll popup_index
        self.popup_index = min(self.popup_index, max(0, len(visible_tree) - 1))
        if self.popup_index < self.popup_scroll:
            self.popup_scroll = self.popup_index
        elif self.popup_index >= self.popup_scroll + content_h:
            self.popup_scroll = self.popup_index - content_h + 1

        # Top border
        safe_addstr(self.stdscr, panel_y, panel_x,
                    "┌" + "─" * inner_w + "┐", viewer_bg)
        # Title row
        vault_name = self.vault.root.name
        title_text = f" 📂 {vault_name}/ "
        safe_addstr(self.stdscr, panel_y + 1, panel_x,
                    "│" + visual_ljust(truncate_to_display_width(title_text, inner_w), inner_w) + "│",
                    curses.A_BOLD | viewer_bg)
        # Title/items separator
        safe_addstr(self.stdscr, panel_y + 2, panel_x,
                    "├" + "─" * inner_w + "┤", viewer_bg)

        # Tree items
        for offset in range(content_h):
            idx = self.popup_scroll + offset
            row_y = panel_y + 3 + offset
            if idx >= len(visible_tree):
                safe_addstr(self.stdscr, row_y, panel_x,
                            "│" + " " * inner_w + "│", viewer_bg)
                continue
            item = visible_tree[idx]
            suffix = "/" if item.is_dir else ""
            hidden_marker = " ..." if item.path in self.collapsed_dirs else ""
            label = " " + self.tree_prefix(item, visible_tree) + item.label + suffix + hidden_marker
            is_selected = idx == self.popup_index
            is_current = bool(item.note and self.current and item.note.rel == self.current.rel)
            if is_selected:
                attr = curses.A_REVERSE
            elif is_current:
                attr = curses.A_BOLD | viewer_bg
            else:
                attr = viewer_bg
            row_text = visual_ljust(truncate_to_display_width(label, inner_w), inner_w)
            safe_addstr(self.stdscr, row_y, panel_x, "│", viewer_bg)
            safe_addstr(self.stdscr, row_y, panel_x + 1, row_text, attr)
            safe_addstr(self.stdscr, row_y, panel_x + 1 + inner_w, "│", viewer_bg)

        # Items/help separator
        sep_y = panel_y + 3 + content_h
        safe_addstr(self.stdscr, sep_y, panel_x,
                    "├" + "─" * inner_w + "┤", viewer_bg)
        # Help row
        help_text = " ↑↓ 移動 · Enter 開啟 · Esc/Tab 關閉 "
        safe_addstr(self.stdscr, sep_y + 1, panel_x,
                    "│" + visual_ljust(truncate_to_display_width(help_text, inner_w), inner_w) + "│",
                    curses.A_DIM | viewer_bg)
        # Bottom border
        safe_addstr(self.stdscr, sep_y + 2, panel_x,
                    "└" + "─" * inner_w + "┘", viewer_bg)
```

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "import py_compile; py_compile.compile('obsidian_cli.py'); print('OK')"
```
Expected: `OK`

---

### Task 6: `handle_nav_popup_key()` method

**Files:**
- Modify: `obsidian_cli.py` — add method after `handle_toc_key()` (~line 757)

**Context:** Handles keyboard input when `mode == "nav_popup"`. Up/Down move `popup_index`. Enter opens the selected note and closes the popup. Esc or Tab closes without opening. Folders are non-selectable (just skip them on Enter).

- [ ] **Step 1: Add `handle_nav_popup_key()` after `handle_toc_key()`**

```python
    def handle_nav_popup_key(self, key) -> None:
        code = key_code(key)
        visible_tree = self.visible_tree()
        if code in (ESC, 9):  # Esc or Tab — close popup
            self.mode = "view"
        elif code in (curses.KEY_UP, ord("k")):
            self.popup_index = max(0, self.popup_index - 1)
        elif code in (curses.KEY_DOWN, ord("j")):
            self.popup_index = min(max(0, len(visible_tree) - 1), self.popup_index + 1)
        elif code in (10, 13):
            if 0 <= self.popup_index < len(visible_tree):
                item = visible_tree[self.popup_index]
                if item.note:
                    self.open_note(item.note)
                    self.mode = "view"
```

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "import py_compile; py_compile.compile('obsidian_cli.py'); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Full manual test**

```bash
python3 obsidian_cli.py database
```

Checklist:
- [ ] Wide terminal (≥ 80 cols): Tab shows/hides sidebar as before
- [ ] Resize terminal to < 80 cols: sidebar disappears automatically
- [ ] Press Tab in narrow terminal: centered popup appears with tree
- [ ] ↑↓ (or j/k) move selection in popup
- [ ] Enter on a note: opens note, popup closes
- [ ] Esc: closes popup without changing note
- [ ] Tab again: reopens popup, selection starts at current note
- [ ] Resize terminal back to ≥ 80 cols while popup open: popup closes automatically
- [ ] Viewer shows deep blue background throughout

---

### Task 7: Update help bar text

**Files:**
- Modify: `obsidian_cli.py` — `draw_help()` (line ~715)

**Context:** The help bar doesn't mention the popup. Update it to reflect the width-dependent Tab behaviour.

- [ ] **Step 1: Update `draw_help()`**

Replace:
```python
    def draw_help(self, y: int, width: int) -> None:
        text = " Tab nav | Enter open/link | Ctrl+E edit | Ctrl+F find | n next | t toc | Ctrl+S save | q quit "
        safe_addstr(self.stdscr, y, 0, text[: width - 1])
```
with:
```python
    def draw_help(self, y: int, width: int) -> None:
        if width < 80:
            text = " Tab nav-popup | Enter open | Ctrl+E edit | Ctrl+F find | q quit "
        else:
            text = " Tab sidebar | Enter open/link | Ctrl+E edit | Ctrl+F find | n next | t toc | q quit "
        safe_addstr(self.stdscr, y, 0, text[: width - 1])
```

- [ ] **Step 2: Final syntax check**

```bash
python3 -c "import py_compile; py_compile.compile('obsidian_cli.py'); print('OK')"
```
Expected: `OK`
