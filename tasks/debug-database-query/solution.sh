#!/bin/bash
# Fix the two bugs in query.py:
# 1. INNER JOIN -> LEFT JOIN (include users without orders)
# 2. Add GROUP BY clause (prevent duplicate rows)
cat > /tmp/fixed_query.py << 'PYEOF'
#!/usr/bin/env python3
"""Query user orders from SQLite database."""
import csv
import sqlite3

def query_user_orders(db_path, output_path):
    conn = sqlite3.connect(db_path)

    query = """
        SELECT u.name, u.email, COUNT(o.id) as order_count, COALESCE(SUM(o.amount), 0) as total_spent
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        GROUP BY u.id, u.name, u.email
    """

    cursor = conn.execute(query)
    rows = cursor.fetchall()

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "email", "order_count", "total_spent"])
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(rows)} rows to {output_path}")
    for row in rows:
        print(f"  {row}")

    conn.close()

if __name__ == "__main__":
    query_user_orders("/app/data/store.db", "/app/output/user_orders.csv")
PYEOF
sudo tee /app/src/query.py < /tmp/fixed_query.py > /dev/null
sudo python3 /app/src/query.py
