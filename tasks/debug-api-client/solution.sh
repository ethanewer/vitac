#!/bin/bash
# Fix the two bugs in api_client.py
cat > /tmp/fixed_api_client.py << 'PYEOF'
#!/usr/bin/env python3
"""REST API client that fetches data from the mock server."""
import json
import urllib.request

API_URL = "http://localhost:5000/api/data"
API_TOKEN = "secret-api-key-12345"

def fetch_data():
    req = urllib.request.Request(API_URL)
    req.add_header("Authorization", f"Bearer {API_TOKEN}")

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            items = data["results"]
            return items
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP Error {e.code}: {body}")
        return []
    except KeyError as e:
        print(f"KeyError: {e} - Available keys: {list(data.keys())}")
        return []

if __name__ == "__main__":
    results = fetch_data()
    with open("/app/output/api_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"Fetched {len(results)} records")
    for r in results:
        print(f"  {r}")
PYEOF
sudo tee /app/src/api_client.py < /tmp/fixed_api_client.py > /dev/null
sudo python3 /app/src/api_client.py
