# Viewer 背景色 + 導覽彈出框設計

**日期：** 2026-05-08
**範圍：** `obsidian_cli.py` — `App` 類別的繪製與輸入處理邏輯

---

## 功能一：Viewer 深藍背景色

### 目標
為 markdown viewer 區域加上深海藍背景色，提升閱讀對比與視覺辨識度。

### 色彩規格
- 背景色：`#0a0e1a`（深海藍）— 對應 256 色終端機的 color 233 附近
- 實作方式：新增一個 curses color pair，專用於 viewer 區域背景
- viewer 區域填色：每列顯示前先用空白字串 + 背景色 pair 填滿整行，再繪製內容

### 限制
- 需要終端機支援 256 色（`TERM=xterm-256color` 或相容）
- 若不支援 256 色，退回預設背景（`-1`），不崩潰

### 實作位置
- `init_terminal()`：新增 256 色 pair（pair 5）
- `draw_viewer()`：每行先以背景色填滿，再繪製文字

---

## 功能二：自動收合側邊欄 + 置中彈出框

### 自動收合邏輯
- 當 `width < 80` 時，側邊欄強制隱藏（`sidebar_visible` 保持 False，不允許手動展開）
- 當 `width >= 80` 時，Tab 鍵維持原有「切換側邊欄顯示/隱藏」行為

### 彈出框（Nav Popup）
視窗寬度 `< 80` 時，Tab 鍵改為開/關彈出框。

**外觀：**
- 全畫面以純色（`#0a0e1a`，同 viewer 背景）覆蓋
- 置中浮動面板，寬度固定 `min(50, width - 4)` 欄，高度 `min(len(tree) + 4, height - 4)` 列
- 面板背景：深藍灰（color pair 6）
- 頂部標題列：`📂 <vault_name>/`
- 樹狀導覽項目（與現有 sidebar 相同的 tree 邏輯）
- 底部提示列：`↑↓ 移動 · Enter 開啟 · Esc/Tab 關閉`
- 當前選中項目以反白 + 左側 border 標示
- 樹狀內容沿用 `visible_tree()`（尊重已折疊的資料夾狀態）

**狀態：**
- 新增 `mode = "nav_popup"` 狀態
- `popup_index`：彈出框內的游標位置（獨立於 `nav_index`）；開啟時初始化為當前筆記在 tree 中的位置
- `popup_scroll`：彈出框捲動偏移

**鍵盤行為：**

| 鍵 | 行為 |
|---|---|
| Tab（寬 ≥ 80）| 切換側邊欄 |
| Tab（寬 < 80）| 開/關彈出框 |
| ↑ / k | 彈出框內向上移動 |
| ↓ / j | 彈出框內向下移動 |
| Enter | 開啟選中筆記，關閉彈出框 |
| Esc | 關閉彈出框（不開啟筆記） |

**視窗大小改變（resize）：**
- 每次 `draw()` 開頭重新判斷寬度
- 若 resize 後 `width >= 80` 且在 `nav_popup` 模式，關閉彈出框（回到 view 模式）

---

## 架構變更摘要

| 項目 | 變更 |
|---|---|
| `init_terminal()` | 新增 color pair 5（viewer 背景），pair 6（popup 面板） |
| `draw_viewer()` | 每行填滿背景色 |
| `draw()` | 加入寬度偵測邏輯，寬 < 80 時強制 sidebar 隱藏 |
| `draw_nav_popup()` | 新方法，繪製置中彈出框 |
| `handle_view_key()` | Tab 行為依寬度分流 |
| `handle_nav_popup_key()` | 新方法，處理彈出框鍵盤輸入 |
| `App.__init__()` | 新增 `popup_index`, `popup_scroll` 狀態 |

---

## 不在範圍內
- 滑鼠點擊彈出框（只做鍵盤）
- 彈出框內展開/收合資料夾（沿用現有折疊狀態，不支援在彈出框內切換）
- 動畫效果
