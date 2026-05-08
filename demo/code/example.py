def summarize_numbers(numbers):
    total = sum(numbers)
    count = len(numbers)
    average = total / count if count else 0
    return {
        "count": count,
        "total": total,
        "average": average,
    }


if __name__ == "__main__":
    values = [3, 5, 8, 13]
    print(summarize_numbers(values))
