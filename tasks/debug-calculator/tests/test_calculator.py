import json
import os

def test_results_file_exists():
    assert os.path.exists("/app/output/results.json"), "Results file not created"

def test_add():
    with open("/app/output/results.json") as f:
        results = json.load(f)
    assert results["add_3_4"] == 7

def test_subtract():
    with open("/app/output/results.json") as f:
        results = json.load(f)
    assert results["subtract_10_3"] == 7, f"Expected 7, got {results['subtract_10_3']}"

def test_multiply():
    with open("/app/output/results.json") as f:
        results = json.load(f)
    assert results["multiply_5_6"] == 30

def test_divide_exact():
    with open("/app/output/results.json") as f:
        results = json.load(f)
    assert results["divide_10_4"] == 2.5, f"Expected 2.5, got {results['divide_10_4']}"

def test_divide_remainder():
    with open("/app/output/results.json") as f:
        results = json.load(f)
    assert results["divide_7_2"] == 3.5, f"Expected 3.5, got {results['divide_7_2']}"
