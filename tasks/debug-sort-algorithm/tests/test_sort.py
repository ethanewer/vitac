import os

def test_output_exists():
    assert os.path.exists("/app/output/sorted.txt")

def test_correct_count():
    with open("/app/output/sorted.txt") as f:
        lines = [l.strip() for l in f if l.strip()]
    assert len(lines) == 10, f"Expected 10 numbers, got {len(lines)}"

def test_sorted_ascending():
    with open("/app/output/sorted.txt") as f:
        numbers = [int(l.strip()) for l in f if l.strip()]
    assert numbers == sorted(numbers), f"Not sorted: {numbers}"

def test_no_duplicates():
    with open("/app/output/sorted.txt") as f:
        numbers = [int(l.strip()) for l in f if l.strip()]
    assert len(numbers) == len(set(numbers)), f"Contains duplicates: {numbers}"

def test_all_original_values_present():
    expected = {8, 12, 17, 23, 31, 42, 55, 64, 76, 93}
    with open("/app/output/sorted.txt") as f:
        numbers = {int(l.strip()) for l in f if l.strip()}
    assert numbers == expected, f"Missing or extra values. Expected {expected}, got {numbers}"
