import os

def test_output_exists():
    assert os.path.exists("/app/output/count.txt"), "count.txt should exist"

def test_correct_count():
    content = open("/app/output/count.txt").read().strip()
    assert content == "7", f"Expected 7 lines, got: {content}"
