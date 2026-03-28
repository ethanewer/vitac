#!/bin/bash
# Fix the two bugs in pipeline.py
cat > /tmp/fixed_pipeline.py << 'PYEOF'
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
            # Parse date - fixed: use %d/%m/%Y for DD/MM/YYYY format
            date_obj = datetime.strptime(row["date"], "%d/%m/%Y")
            iso_date = date_obj.strftime("%Y-%m-%d")

            record = {
                "id": int(row["id"]),
                "date": iso_date,
                "customer": row["customer"],
                "amount": float(row["amount"]),  # fixed: convert to float
                "currency": row["currency"]
            }
            records.append(record)

    with open(output_path, "w") as f:
        json.dump(records, f, indent=2)

    print(f"Transformed {len(records)} records")
    print(json.dumps(records, indent=2))

if __name__ == "__main__":
    transform("/app/data/transactions.csv", "/app/output/transformed.json")
PYEOF
sudo tee /app/src/pipeline.py < /tmp/fixed_pipeline.py > /dev/null
sudo python3 /app/src/pipeline.py
