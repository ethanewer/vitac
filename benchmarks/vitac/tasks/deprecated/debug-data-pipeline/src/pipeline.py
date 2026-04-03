#!/usr/bin/env python3
"""ETL pipeline: CSV to JSON with transformations."""
import csv
import json
from datetime import datetime

def transform(input_path, output_path):
    records = []

    with open(input_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse date - BUG 1: wrong format string
            date_obj = datetime.strptime(row["date"], "%m/%d/%Y")
            iso_date = date_obj.strftime("%Y-%m-%d")

            record = {
                "id": int(row["id"]),
                "date": iso_date,
                "customer": row["customer"],
                "amount": row["amount"],  # BUG 2: should convert to float
                "currency": row["currency"]
            }
            records.append(record)

    with open(output_path, "w") as f:
        json.dump(records, f, indent=2)

    print(f"Transformed {len(records)} records")
    print(json.dumps(records, indent=2))

if __name__ == "__main__":
    transform("/app/data/transactions.csv", "/app/output/transformed.json")
