#!/usr/bin/env python3
"""Parse CSV file and convert to JSON."""
import json

def parse_csv(filepath):
    records = []
    with open(filepath) as f:
        lines = f.readlines()

    header = lines[0].strip().split(",")  # naive split

    for line in lines[1:]:
        values = line.strip().split(",")  # BUG 1: doesn't handle quoted fields
        record = {}
        for i, col in enumerate(header):
            record[col] = values[i]  # BUG 2: IndexError on empty lines
        records.append(record)

    return records

if __name__ == "__main__":
    records = parse_csv("/app/data/input.csv")
    with open("/app/output/parsed.json", "w") as f:
        json.dump(records, f, indent=2)
    print(f"Parsed {len(records)} records")
    print(json.dumps(records, indent=2))
