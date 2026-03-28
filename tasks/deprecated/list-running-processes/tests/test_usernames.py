import os

def test_output_exists():
    assert os.path.exists("/app/output/usernames.txt"), "usernames.txt should exist"

def test_correct_usernames():
    names = [l.strip() for l in open("/app/output/usernames.txt") if l.strip()]
    expected = ["alice", "bob", "charlie", "diana", "eve"]
    assert names == expected, f"Expected {expected}, got {names}"

def test_no_duplicates():
    names = [l.strip() for l in open("/app/output/usernames.txt") if l.strip()]
    assert len(names) == len(set(names)), f"Duplicates found: {names}"

def test_sorted():
    names = [l.strip() for l in open("/app/output/usernames.txt") if l.strip()]
    assert names == sorted(names), f"Names should be sorted: {names}"
