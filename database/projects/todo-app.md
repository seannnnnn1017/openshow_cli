---
title: 待辦事項專案
tags: [project, python, cli]
created: 2026-05-05
status: in-progress
---

# 待辦事項專案

回到 [[index]]

## 概述

一個用 [[python-basics|Python]] 撰寫的命令列 Todo 工具。

## 技術選擇

- 語言：Python（見 [[python-basics]]）
- 儲存：JSON 檔案（利用 [[data-structures#Hash Table]] 結構）
- 排序：依優先度排序（參考 [[algorithms#排序]]）

## 核心功能

- [ ] 新增任務
- [ ] 刪除任務
- [x] 列出所有任務
- [ ] 標記完成

## 程式碼草稿

```python
import json
from pathlib import Path

DB_PATH = Path("tasks.json")

def load_tasks() -> dict:
    if DB_PATH.exists():
        return json.loads(DB_PATH.read_text())
    return {}

def save_tasks(tasks: dict) -> None:
    DB_PATH.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))

def add_task(title: str, priority: int = 0) -> None:
    tasks = load_tasks()
    task_id = str(len(tasks) + 1)
    tasks[task_id] = {"title": title, "priority": priority, "done": False}
    save_tasks(tasks)
```

## 相關筆記

- [[python-basics]] - 使用的語言基礎
- [[data-structures]] - 資料儲存方式
- [[algorithms]] - 排序邏輯
