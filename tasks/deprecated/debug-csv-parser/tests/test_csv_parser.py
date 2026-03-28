import json
import os

def test_output_exists():
    assert os.path.exists("/app/output/parsed.json")

def test_record_count():
    with open("/app/output/parsed.json") as f:
        records = json.load(f)
    assert len(records) == 4, f"Expected 4 records, got {len(records)}"

def test_quoted_field_parsed():
    with open("/app/output/parsed.json") as f:
        records = json.load(f)
    names = [r["name"] for r in records]
    assert "Smith, John" in names, f"Quoted name not parsed correctly. Names: {names}"

def test_all_fields_present():
    with open("/app/output/parsed.json") as f:
        records = json.load(f)
    for r in records:
        assert "name" in r and "age" in r and "city" in r, f"Missing fields in {r}"

def test_no_empty_records():
    with open("/app/output/parsed.json") as f:
        records = json.load(f)
    for r in records:
        assert r["name"].strip() != "", f"Empty name in record: {r}"
