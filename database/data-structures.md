---
title: 資料結構筆記
tags: [data-structures, computer-science]
created: 2026-05-02
updated: 2026-05-08
---

# 資料結構筆記

回到 [[index]]

## 線性結構

| 結構 | 存取 | 插入 | 刪除 |
|------|------|------|------|
| Array | O(1) | O(n) | O(n) |
| Linked List | O(n) | O(1) | O(1) |
| Stack | O(n) | O(1) | O(1) |
| Queue | O(n) | O(1) | O(1) |

## Hash Table

以 key-value 儲存，平均存取 O(1)。

```python
cache = {}
cache["key"] = "value"
print(cache.get("key", "default"))
```

> 在 [[algorithms]] 的搜尋章節有使用 hash table 加速的範例。

## 樹狀結構

- Binary Search Tree - 查詢 O(log n)
- Heap - 優先佇列，常見於 [[algorithms#排序|排序演算法]]

## 相關筆記

- [[python-basics]] - Python 內建資料結構語法
- [[algorithms]] - 資料結構的應用
