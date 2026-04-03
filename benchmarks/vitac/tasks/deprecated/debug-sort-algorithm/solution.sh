#!/bin/bash
# Fix the two bugs in sort.py
cat > /tmp/fixed_sort.py << 'PYEOF'
#!/usr/bin/env python3
"""Merge sort implementation."""

def merge_sort(arr):
    if len(arr) <= 1:
        return list(arr)

    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
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
PYEOF
sudo tee /app/src/sort.py < /tmp/fixed_sort.py > /dev/null
sudo python3 /app/src/sort.py
