# Cross-File Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 Ctrl+F 跨所有 vault 筆記搜尋，上下鍵/滾輪在有搜尋結果時直接跳 hit，ESC 清除搜尋。

**Architecture:** 抽出純函式 `collect_search_hits` 處理跨檔 hit 收集（可單元測試）；`search_hits` 型別從 `list[int]` 改為 `list[tuple[Note, int]]`；`handle_view_key` 與 `handle_mouse` 依 `search_hits` 是否非空切換行為。

**Tech Stack:** Python 3.12, curses, pytest

---

## File Map

| 動作 | 路徑 | 說明 |
|---|---|---|
| Modify | `obsidian_cli.py` | 主程式，所有改動都在這 |
| Create | `tests/test_search.py` | 單元測試 `collect_search_hits` |

---

### Task 1: 新增 `collect_search_hits` 純函式與測試

**Files:**
- Modify: `obsidian_cli.py` — 在 `class App` 定義之前新增函式
- Create: `tests/test_search.py`

- [ ] **Step 1: 建立測試檔，寫入第一個失敗測試**

建立 `tests/__init__.py`（空檔）與 `tests/test_search.py`：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from obsidian_cli import Note, RenderLine, collect_search_hits


def _render(raw: str) -> list[RenderLine]:
    return [RenderLine(line, "text") for line in raw.splitlines()]


def _note(name: str, body: str) -> Note:
    return Note(
        path=Path(f"/fake/{name}.md"),
        rel=f"{name}.md",
        stem_rel=name,
        title=name,
        raw=body,
        body=body,
    )


def test_single_note_hit():
    note = _note("a", "foo\nbar\nbaz")
    hits = collect_search_hits([note], "bar", _render)
    assert hits == [(note, 1)]


def test_cross_file():
    n1 = _note("a", "hello world")
    n2 = _note("b", "hello there")
    hits = collect_search_hits([n1, n2], "hello", _render)
    assert hits[0][0] is n1
    assert hits[1][0] is n2
    assert len(hits) == 2


def test_empty_term_returns_nothing():
    note = _note("a", "hello")
    hits = collect_search_hits([note], "", _render)
    assert hits == []


def test_case_insensitive():
    note = _note("a", "Hello World")
    hits = collect_search_hits([note], "hello", _render)
    assert len(hits) == 1


def test_multiple_hits_same_note():
    note = _note("a", "cat\ndog\ncat")
    hits = collect_search_hits([note], "cat", _render)
    assert len(hits) == 2
    assert hits[0] == (note, 0)
    assert hits[1] == (note, 2)
```

- [ ] **Step 2: 確認測試失敗（函式未定義）**

```bash
cd /home/sean/Github/obsidian_cli && python -m pytest tests/test_search.py -v 2>&1 | head -20
```

預期：`ImportError: cannot import name 'collect_search_hits'`

- [ ] **Step 3: 在 `obsidian_cli.py` 加入 `collect_search_hits`**

在 `obsidian_cli.py` 的 `def prompt(...)` 函式**之前**（約 206 行），插入：

```python
def collect_search_hits(
    notes: list[Note],
    term: str,
    render_fn,
) -> list[tuple[Note, int]]:
    hits: list[tuple[Note, int]] = []
    lower = term.lower()
    if not lower:
        return hits
    for note in notes:
        rendered = render_fn(note.raw)
        for line_index, line in enumerate(rendered):
            if lower in line.text.lower():
                hits.append((note, line_index))
    return hits
```

- [ ] **Step 4: 執行測試，確認全過**

```bash
cd /home/sean/Github/obsidian_cli && python -m pytest tests/test_search.py -v
```

預期：5 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /home/sean/Github/obsidian_cli && git add obsidian_cli.py tests/ && git commit -m "feat: add collect_search_hits pure function with tests"
```

---

### Task 2: 改 `search_hits` 型別 + 修正 `draw_viewer()` highlight

**Files:**
- Modify: `obsidian_cli.py:318` (`App.__init__` 中的型別宣告)
- Modify: `obsidian_cli.py:813-814` + `obsidian_cli.py:850` (`draw_viewer` 的 highlight 判斷)

- [ ] **Step 1: 修改 `App.__init__` 型別宣告**

找到（約第 318 行）：
```python
        self.search_hits: list[int] = []
```
改為：
```python
        self.search_hits: list[tuple[Note, int]] = []
```

- [ ] **Step 2: 修改 `draw_viewer()` — 在迴圈前建立 hit 行號集合**

在 `draw_viewer()` 中，找到這一行（約第 782 行）：
```python
        for offset in range(content_height):
```
在它**正上方**插入：
```python
        current_note_hit_lines = {li for (n, li) in self.search_hits if n is self.current}
```

- [ ] **Step 3: 替換 `draw_viewer()` 中兩處 highlight 判斷**

找到 code block 的 highlight（約第 814 行）：
```python
                if line_index in self.search_hits:
                    code_attr |= curses.A_REVERSE
```
改為：
```python
                if line_index in current_note_hit_lines:
                    code_attr |= curses.A_REVERSE
```

找到一般行的 highlight（約第 850 行）：
```python
            if line_index in self.search_hits:
                attr |= curses.A_REVERSE
```
改為：
```python
            if line_index in current_note_hit_lines:
                attr |= curses.A_REVERSE
```

- [ ] **Step 4: 確認既有測試仍過**

```bash
cd /home/sean/Github/obsidian_cli && python -m pytest tests/ -v
```

預期：全 PASSED，無新 error

- [ ] **Step 5: 手動驗證啟動不崩潰**

```bash
cd /home/sean/Github/obsidian_cli && python obsidian_cli.py database
```

應正常開啟，按 `q` 離開。

- [ ] **Step 6: Commit**

```bash
cd /home/sean/Github/obsidian_cli && git add obsidian_cli.py && git commit -m "refactor: change search_hits type to list[tuple[Note, int]]"
```

---

### Task 3: 修正 `open_note()` — 跨檔跳轉時保留搜尋狀態

**Files:**
- Modify: `obsidian_cli.py:370-371` (`open_note` 末尾的清除邏輯)

- [ ] **Step 1: 找到 `open_note()` 末尾的清除邏輯**

約第 370 行，現有：
```python
        self.search_hits = []
        self.search_hit_index = -1
        self.status = f"Opened {note.rel}"
```

- [ ] **Step 2: 改為只在沒有搜尋詞時清除**

```python
        if not self.search_term:
            self.search_hits = []
            self.search_hit_index = -1
        self.status = f"Opened {note.rel}"
```

- [ ] **Step 3: 確認測試仍過**

```bash
cd /home/sean/Github/obsidian_cli && python -m pytest tests/ -v
```

預期：全 PASSED

- [ ] **Step 4: Commit**

```bash
cd /home/sean/Github/obsidian_cli && git add obsidian_cli.py && git commit -m "fix: preserve search state when open_note is called during search"
```

---

### Task 4: 更新 `update_search()` + `find_next()` + 新增 `find_prev()` 和 `clear_search()`

**Files:**
- Modify: `obsidian_cli.py:688-705` (search 相關方法)

- [ ] **Step 1: 替換 `update_search()`**

找到（約第 698 行）：
```python
    def update_search(self, term: str) -> None:
        self.search_term = term
        lower = term.lower()
        self.search_hits = [
            index for index, line in enumerate(self.rendered) if lower and lower in line.text.lower()
        ]
        self.search_hit_index = -1
        self.find_next()
```
改為：
```python
    def update_search(self, term: str) -> None:
        self.search_term = term
        self.search_hits = collect_search_hits(self.vault.notes, term, self.render_markdown)
        self.search_hit_index = -1
        self.find_next()
```

- [ ] **Step 2: 替換 `find_next()`**

找到（約第 688 行）：
```python
    def find_next(self) -> None:
        if not self.search_hits:
            self.status = "No search hits"
            return
        self.search_hit_index = (self.search_hit_index + 1) % len(self.search_hits)
        self.focus = "viewer"
        self.view_scroll = max(0, self.search_hits[self.search_hit_index] - 2)
        self.update_toc_for_view()
        self.status = f"Find: {self.search_term} ({self.search_hit_index + 1}/{len(self.search_hits)})"
```
改為：
```python
    def find_next(self) -> None:
        if not self.search_hits:
            self.status = "No search hits"
            return
        self.search_hit_index = (self.search_hit_index + 1) % len(self.search_hits)
        self.focus = "viewer"
        note, line_index = self.search_hits[self.search_hit_index]
        if note is not self.current:
            self.open_note(note)
        self.view_scroll = max(0, line_index - 2)
        self.update_toc_for_view()
        self.status = f"Find: {self.search_term} ({self.search_hit_index + 1}/{len(self.search_hits)})"
```

- [ ] **Step 3: 在 `find_next()` 之後新增 `find_prev()` 和 `clear_search()`**

在 `find_next` 方法結尾的下一行插入：
```python
    def find_prev(self) -> None:
        if not self.search_hits:
            self.status = "No search hits"
            return
        self.search_hit_index = (self.search_hit_index - 1) % len(self.search_hits)
        self.focus = "viewer"
        note, line_index = self.search_hits[self.search_hit_index]
        if note is not self.current:
            self.open_note(note)
        self.view_scroll = max(0, line_index - 2)
        self.update_toc_for_view()
        self.status = f"Find: {self.search_term} ({self.search_hit_index + 1}/{len(self.search_hits)})"

    def clear_search(self) -> None:
        self.search_term = ""
        self.search_hits = []
        self.search_hit_index = -1
        self.status = "Search cleared"
```

- [ ] **Step 4: 確認測試仍過**

```bash
cd /home/sean/Github/obsidian_cli && python -m pytest tests/ -v
```

預期：全 PASSED

- [ ] **Step 5: 手動測試跨檔搜尋**

```bash
cd /home/sean/Github/obsidian_cli && python obsidian_cli.py database
```

按 `Ctrl+F`，輸入 `#`（所有筆記都有 heading），按 `n` 觀察是否跨檔跳轉，狀態列應顯示 `(1/N)` 計數。按 `q` 離開。

- [ ] **Step 6: Commit**

```bash
cd /home/sean/Github/obsidian_cli && git add obsidian_cli.py && git commit -m "feat: cross-file search with find_next/find_prev/clear_search"
```

---

### Task 5: 更新 `handle_view_key()` — 上下鍵/ESC 感知搜尋狀態

**Files:**
- Modify: `obsidian_cli.py:1014-1056` (`handle_view_key` 的上下鍵與 ESC 段落)

- [ ] **Step 1: 修改 KEY_UP / `k` 段**

找到（約第 1014 行）：
```python
        elif code in (curses.KEY_UP, ord("k")):
            if self.focus == "toc" and self.toc_visible:
                self.toc_index = max(0, self.toc_index - 1)
            elif self.sidebar_visible:
                self.nav_index = max(0, self.nav_index - 1)
            else:
                self.scroll_viewer(-1)
```
改為：
```python
        elif code in (curses.KEY_UP, ord("k")):
            if self.search_hits:
                self.find_prev()
            elif self.focus == "toc" and self.toc_visible:
                self.toc_index = max(0, self.toc_index - 1)
            elif self.sidebar_visible:
                self.nav_index = max(0, self.nav_index - 1)
            else:
                self.scroll_viewer(-1)
```

- [ ] **Step 2: 修改 KEY_DOWN / `j` 段**

找到（約第 1021 行）：
```python
        elif code in (curses.KEY_DOWN, ord("j")):
            if self.focus == "toc" and self.toc_visible:
                self.toc_index = min(max(0, len(self.toc) - 1), self.toc_index + 1)
            elif self.sidebar_visible:
                self.nav_index = min(len(self.visible_tree()) - 1, self.nav_index + 1)
            else:
                self.scroll_viewer(1)
```
改為：
```python
        elif code in (curses.KEY_DOWN, ord("j")):
            if self.search_hits:
                self.find_next()
            elif self.focus == "toc" and self.toc_visible:
                self.toc_index = min(max(0, len(self.toc) - 1), self.toc_index + 1)
            elif self.sidebar_visible:
                self.nav_index = min(len(self.visible_tree()) - 1, self.nav_index + 1)
            else:
                self.scroll_viewer(1)
```

- [ ] **Step 3: 新增 ESC 清除搜尋**

在 `handle_view_key()` 中，找到 `elif code == CTRL_F:` 這一段之後，插入新的 elif：

```python
        elif code == ESC:
            if self.search_hits:
                self.clear_search()
```

- [ ] **Step 4: 確認測試仍過**

```bash
cd /home/sean/Github/obsidian_cli && python -m pytest tests/ -v
```

預期：全 PASSED

- [ ] **Step 5: 手動測試鍵盤導覽**

```bash
cd /home/sean/Github/obsidian_cli && python obsidian_cli.py database
```

1. 按 `Ctrl+F`，輸入搜尋詞
2. 按 `↓` → 應跳到下一個 hit（包含跨檔）
3. 按 `↑` → 應跳到上一個 hit
4. 按 `ESC` → 狀態列顯示「Search cleared」，`↑↓` 恢復正常捲動

- [ ] **Step 6: Commit**

```bash
cd /home/sean/Github/obsidian_cli && git add obsidian_cli.py && git commit -m "feat: up/down keys and ESC navigate search hits"
```

---

### Task 6: 更新 `handle_mouse()` — 滾輪感知搜尋狀態

**Files:**
- Modify: `obsidian_cli.py:1177-1181` (`handle_mouse` viewer 區滾輪段落)

- [ ] **Step 1: 找到 viewer 區的滾輪段落**

在 `handle_mouse()` 的 `else:` 分支（viewer 區，最後的 else 段），找到（約第 1177 行）：
```python
            if button & curses.BUTTON4_PRESSED:
                self.focus = "viewer"
                self.scroll_viewer(-3)
            elif button & curses.BUTTON5_PRESSED:
                self.focus = "viewer"
                self.scroll_viewer(3)
```

- [ ] **Step 2: 替換為搜尋感知版本**

```python
            if button & curses.BUTTON4_PRESSED:
                if self.search_hits:
                    self.find_prev()
                else:
                    self.focus = "viewer"
                    self.scroll_viewer(-3)
            elif button & curses.BUTTON5_PRESSED:
                if self.search_hits:
                    self.find_next()
                else:
                    self.focus = "viewer"
                    self.scroll_viewer(3)
```

- [ ] **Step 3: 確認測試仍過**

```bash
cd /home/sean/Github/obsidian_cli && python -m pytest tests/ -v
```

預期：全 PASSED

- [ ] **Step 4: 手動測試滾輪**

```bash
cd /home/sean/Github/obsidian_cli && python obsidian_cli.py database
```

1. 按 `Ctrl+F`，輸入搜尋詞
2. 向下滾動滑鼠 → 應跳到下一個 hit
3. 向上滾動滑鼠 → 應跳到上一個 hit
4. 按 `ESC` 清除搜尋後，確認滾輪恢復正常捲動

- [ ] **Step 5: Commit**

```bash
cd /home/sean/Github/obsidian_cli && git add obsidian_cli.py && git commit -m "feat: mouse scroll navigates search hits when search is active"
```

---

### Task 7: 更新 `draw_status()` — 搜尋中顯示 SEARCH 模式

**Files:**
- Modify: `obsidian_cli.py:985-989` (`draw_status`)

- [ ] **Step 1: 修改 `draw_status()`**

找到（約第 985 行）：
```python
    def draw_status(self, y: int, width: int) -> None:
        mode = self.mode.upper()
        current = self.current.rel if self.current else "-"
        msg = f" {mode} | {current} | {self.status}"
        safe_addstr(self.stdscr, y, 0, msg[: width - 1].ljust(width - 1), curses.A_REVERSE)
```
改為：
```python
    def draw_status(self, y: int, width: int) -> None:
        mode = "SEARCH" if self.search_hits else self.mode.upper()
        current = self.current.rel if self.current else "-"
        msg = f" {mode} | {current} | {self.status}"
        safe_addstr(self.stdscr, y, 0, msg[: width - 1].ljust(width - 1), curses.A_REVERSE)
```

- [ ] **Step 2: 確認測試仍過**

```bash
cd /home/sean/Github/obsidian_cli && python -m pytest tests/ -v
```

預期：全 PASSED

- [ ] **Step 3: 手動驗證狀態列**

```bash
cd /home/sean/Github/obsidian_cli && python obsidian_cli.py database
```

按 `Ctrl+F` 輸入搜尋詞後，底部狀態列左側應顯示 `SEARCH`；按 `ESC` 後恢復 `VIEW`。

- [ ] **Step 4: Commit**

```bash
cd /home/sean/Github/obsidian_cli && git add obsidian_cli.py && git commit -m "feat: show SEARCH in status bar when search is active"
```

---

## 完成驗收清單

- [ ] `Ctrl+F` 搜尋橫跨 vault 所有 note
- [ ] `↓` / `j` 跳到下一個 hit（跨檔自動切換）
- [ ] `↑` / `k` 跳到上一個 hit（跨檔自動切換）
- [ ] 滾輪向下跳下一個 hit，向上跳上一個 hit
- [ ] ESC 清除搜尋，還原正常導覽行為
- [ ] 搜尋中狀態列顯示 `SEARCH`
- [ ] `n` 鍵仍可用（find_next）
- [ ] 所有單元測試通過
