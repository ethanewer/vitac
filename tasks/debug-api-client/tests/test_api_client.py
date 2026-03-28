import json
import os

def test_output_exists():
    assert os.path.exists("/app/output/api_results.json")

def test_three_records():
    with open("/app/output/api_results.json") as f:
        results = json.load(f)
    assert len(results) == 3, f"Expected 3 records, got {len(results)}"

def test_record_fields():
    with open("/app/output/api_results.json") as f:
        results = json.load(f)
    for r in results:
        assert "id" in r and "name" in r and "value" in r

def test_correct_data():
    with open("/app/output/api_results.json") as f:
        results = json.load(f)
    names = [r["name"] for r in results]
    assert sorted(names) == ["Alpha", "Beta", "Gamma"]
