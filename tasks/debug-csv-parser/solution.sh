#!/bin/bash
# Fix the two bugs in parse_csv.py:
# 1. Use csv module to handle quoted fields
# 2. Skip empty lines
cat > /tmp/fixed_parse_csv.py << 'PYEOF'
#!/usr/bin/env python3
"""Parse CSV file and convert to JSON."""
import csv
import json

def parse_csv(filepath):
    records = []
    with open(filepath, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip empty lines (DictReader may yield rows with None values)
            if any(v is not None and v.strip() != '' for v in row.values()):
                records.append(dict(row))
    return records

if __name__ == "__main__":
    records = parse_csv("/app/data/input.csv")
    with open("/app/output/parsed.json", "w") as f:
        json.dump(records, f, indent=2)
    print(f"Parsed {len(records)} records")
    print(json.dumps(records, indent=2))
PYEOF
sudo tee /app/src/parse_csv.py < /tmp/fixed_parse_csv.py > /dev/null
sudo python3 /app/src/parse_csv.py
