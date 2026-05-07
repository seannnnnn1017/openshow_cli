---
title: Python 基礎語法
tags: [python, programming, basics]
created: 2026-05-01
updated: 2026-05-08
---

# Python 基礎語法

回到 [[index]]

## 變數與型別

Python 是動態型別語言，常見型別：

- `int`, `float`, `str`, `bool`
- `list`, `dict`, `tuple`, `set`

## List Comprehension

```python
squares = [x**2 for x in range(10)]
filtered = [x for x in squares if x > 10]
```

## 函式

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

## 相關筆記

- [[data-structures]] - Python 中常用的資料結構
- [[algorithms]] - 搭配 Python 實作的演算法
- [[projects/todo-app]] - 用 Python 實作的小專案
