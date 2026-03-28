import json
import os

def test_output_exists():
    assert os.path.exists("/app/output/transformed.json")

def test_record_count():
    with open("/app/output/transformed.json") as f:
        records = json.load(f)
    assert len(records) == 4

def test_dates_are_iso():
    with open("/app/output/transformed.json") as f:
        records = json.load(f)
    expected_dates = ["2026-03-15", "2026-03-22", "2026-01-07", "2026-02-28"]
    actual_dates = [r["date"] for r in records]
    assert actual_dates == expected_dates, f"Expected {expected_dates}, got {actual_dates}"

def test_amounts_are_numbers():
    with open("/app/output/transformed.json") as f:
        records = json.load(f)
    for r in records:
        assert isinstance(r["amount"], (int, float)), \
            f"Amount should be numeric, got {type(r['amount'])}: {r['amount']}"

def test_first_record_correct():
    with open("/app/output/transformed.json") as f:
        records = json.load(f)
    r = records[0]
    assert r["id"] == 1
    assert r["date"] == "2026-03-15"
    assert r["customer"] == "Alice Johnson"
    assert r["amount"] == 1250.50
    assert r["currency"] == "USD"

def test_amounts_correct():
    with open("/app/output/transformed.json") as f:
        records = json.load(f)
    expected = [1250.50, 890.75, 2100.00, 450.25]
    actual = [r["amount"] for r in records]
    assert actual == expected, f"Expected {expected}, got {actual}"
