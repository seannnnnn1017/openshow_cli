# 跨檔案搜尋設計

**日期：** 2026-05-08  
**範圍：** `obsidian_cli.py` — `App` 類別的搜尋、導覽、鍵盤與滑鼠邏輯

---

## 功能目標

1. Ctrl+F 搜尋可橫跨 vault 所有 note（跨檔案）
2. 上下鍵 / 滾輪在有搜尋結果時直接跳 hit，不再需要按 `n`
3. ESC 清除搜尋，恢復正常上下鍵/滾輪行為

---

## 資料結構改動

### `search_hits` 型別變更

| | 舊 | 新 |
|---|---|---|
| `search_hits` | `list[int]` — 當前 note rendered 行號 | `list[tuple[Note, int]]` — 全 vault (note, rendered\_line\_index) |
| `search_hit_index` | `int` | `int`（不變） |

---

## 方法改動

### `update_search(term: str)`

1. 設定 `self.search_term = term`
2. 迭代 `self.vault.notes`（依 vault 排序）
3. 對每個 note 呼叫 `self.render_markdown(note.raw)`，產生臨時 rendered list
4. 找出所有 `lower in line.text.lower()` 的行，附上 `(note, line_index)` 加入 `self.search_hits`
5. `self.search_hit_index = -1`
6. 呼叫 `self.find_next()`

### `find_next()`

1. 若 `search_hits` 為空 → 顯示「No search hits」並 return
2. `self.search_hit_index = (self.search_hit_index + 1) % len(self.search_hits)`
3. 取出 `(note, line_index) = self.search_hits[self.search_hit_index]`
4. 若 `note != self.current` → `self.open_note(note)`（不會清除 search_hits，open_note 末尾會清除；需修正：open_note 不清除搜尋狀態）
5. 設定 `self.view_scroll = max(0, line_index - 2)`
6. 更新 status：`Find: {term} ({index+1}/{total})`

### `find_prev()` — 新增

同 `find_next()` 但方向：`(self.search_hit_index - 1) % len(self.search_hits)`

### `clear_search()` — 新增

```
self.search_term = ""
self.search_hits = []
self.search_hit_index = -1
self.status = "Search cleared"
```

### `open_note()` 修正

目前 `open_note()` 末尾會執行：
```python
self.search_hits = []
self.search_hit_index = -1
```
改為：若 `self.search_term` 不為空，則保留 `search_hits` 與 `search_hit_index`（跨檔跳轉時不清除搜尋狀態）。

---

## 鍵盤行為

### `handle_view_key()` 改動

| 按鍵 | `search_hits` 非空時 | `search_hits` 為空時 |
|---|---|---|
| `↑` / `k` | `find_prev()` | 原本行為（nav\_index / scroll） |
| `↓` / `j` | `find_next()` | 原本行為 |
| `ESC` | `clear_search()` | 無效果 |
| `n` | `find_next()`（保留） | 無效果 |

### `handle_mouse()` 改動（viewer 區滾輪）

| 事件 | `search_hits` 非空時 | `search_hits` 為空時 |
|---|---|---|
| `BUTTON4_PRESSED`（scroll up） | `find_prev()` | `scroll_viewer(-3)` |
| `BUTTON5_PRESSED`（scroll down） | `find_next()` | `scroll_viewer(3)` |

---

## 狀態列顯示

`draw_status()` 中 mode 欄位：
- 有 `search_hits` 時顯示 `SEARCH` 而非 `VIEW`

---

## draw_viewer() highlight 改動

目前以 `line_index in self.search_hits` 判斷高亮，需改為：
```python
current_search_hit_line = (
    self.search_hits[self.search_hit_index][1]
    if self.search_hits and self.search_hit_index >= 0
    and self.search_hits[self.search_hit_index][0] == self.current
    else None
)
```
高亮邏輯改為：當前 note 所有 hit 行皆高亮（`line_index in current_note_hit_lines`），當前游標所在 hit 額外加粗。

`current_note_hit_lines`：
```python
{li for (n, li) in self.search_hits if n == self.current}
```

---

## 不在範圍內

- 搜尋進度/預覽彈窗
- 正則表達式搜尋
- 大小寫敏感選項
- 即時搜尋（邊打邊找）
