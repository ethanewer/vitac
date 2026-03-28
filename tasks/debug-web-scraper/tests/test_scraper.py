import json
import os

def test_output_exists():
    assert os.path.exists("/app/output/prices.json")

def test_found_four_prices():
    with open("/app/output/prices.json") as f:
        prices = json.load(f)
    assert len(prices) == 4, f"Expected 4 prices, got {len(prices)}"

def test_prices_are_numeric():
    with open("/app/output/prices.json") as f:
        prices = json.load(f)
    for p in prices:
        assert float(p), f"Price {p} is not numeric"

def test_correct_prices():
    with open("/app/output/prices.json") as f:
        prices = json.load(f)
    expected = ["19.99", "29.50", "9.75", "45.00"]
    assert sorted(prices) == sorted(expected), f"Expected {expected}, got {prices}"
