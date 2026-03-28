#!/usr/bin/env python3
"""Merge sort implementation."""

def merge_sort(arr):
    if len(arr) <= 1:
        return []  # BUG 2: should return arr (or list(arr))

    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:  # BUG 1: should be < to avoid duplicates when equal
            result.append(left[i])
            result.append(left[i])  # BUG 1: accidentally appends twice
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

if __name__ == "__main__":
    with open("/app/data/input.txt") as f:
        numbers = [int(line.strip()) for line in f if line.strip()]

    sorted_nums = merge_sort(numbers)

    with open("/app/output/sorted.txt", "w") as f:
        for n in sorted_nums:
            f.write(f"{n}\n")

    print(f"Input: {numbers}")
    print(f"Sorted: {sorted_nums}")
