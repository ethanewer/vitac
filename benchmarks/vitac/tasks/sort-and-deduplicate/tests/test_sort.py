import os

def test_output_exists():
    assert os.path.exists("/app/output/clean.csv"), "clean.csv should exist"

def test_header_preserved():
    first_line = open("/app/output/clean.csv").readline().strip()
    assert first_line == "id,name,score", f"Header should be preserved, got: {first_line}"

def test_no_duplicates():
    lines = open("/app/output/clean.csv").readlines()[1:]  # skip header
    lines = [l.strip() for l in lines if l.strip()]
    assert len(lines) == len(set(lines)), f"Duplicates found: {lines}"

def test_correct_count():
    lines = [l.strip() for l in open("/app/output/clean.csv") if l.strip()]
    # header + 5 unique records
    assert len(lines) == 6, f"Expected 6 lines (header + 5 records), got {len(lines)}"

def test_sorted_by_score_descending():
    lines = open("/app/output/clean.csv").readlines()[1:]  # skip header
    scores = [int(l.strip().split(",")[2]) for l in lines if l.strip()]
    assert scores == sorted(scores, reverse=True), f"Scores should be descending: {scores}"
