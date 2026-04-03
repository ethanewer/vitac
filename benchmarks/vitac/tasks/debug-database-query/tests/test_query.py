import csv
import os

def test_output_exists():
    assert os.path.exists("/app/output/user_orders.csv")

def test_four_users():
    with open("/app/output/user_orders.csv") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 4, f"Expected 4 rows (all users), got {len(rows)}"

def test_alice_orders():
    with open("/app/output/user_orders.csv") as f:
        reader = csv.DictReader(f)
        rows = {r["name"]: r for r in reader}
    assert rows["Alice"]["order_count"] == "3"
    assert float(rows["Alice"]["total_spent"]) == 150.0

def test_charlie_no_orders():
    with open("/app/output/user_orders.csv") as f:
        reader = csv.DictReader(f)
        rows = {r["name"]: r for r in reader}
    assert "Charlie" in rows, "Charlie should appear even with no orders"
    assert rows["Charlie"]["order_count"] == "0"

def test_diana_no_orders():
    with open("/app/output/user_orders.csv") as f:
        reader = csv.DictReader(f)
        rows = {r["name"]: r for r in reader}
    assert "Diana" in rows, "Diana should appear even with no orders"
    assert rows["Diana"]["order_count"] == "0"

def test_no_duplicates():
    with open("/app/output/user_orders.csv") as f:
        reader = csv.DictReader(f)
        names = [r["name"] for r in reader]
    assert len(names) == len(set(names)), f"Duplicate names found: {names}"
