---
title: 演算法概覽
tags: [algorithms, computer-science]
created: 2026-05-03
updated: 2026-05-08
---

# 演算法概覽

回到 [[index]]

## 排序

### Quick Sort

平均 O(n log n)，原地排序。

```python
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    mid  = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + mid + quicksort(right)
```

> 需要了解 list comprehension 語法，見 [[python-basics#List Comprehension]]。

## 搜尋

### Binary Search

需要已排序的序列，O(log n)。

```python
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```

使用 [[data-structures#Hash Table]] 也可達到 O(1) 平均查詢。

## 相關筆記

- [[data-structures]] - 演算法依賴的底層結構
- [[python-basics]] - Python 實作細節
- [[projects/todo-app]] - 實際應用範例
