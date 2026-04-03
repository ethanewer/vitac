#!/bin/bash
# Fix the two bugs in scraper.py
cat > /tmp/fixed_scraper.py << 'PYEOF'
#!/usr/bin/env python3
"""Extract product prices from HTML file."""
import json
import re

def extract_prices(html_path):
    with open(html_path) as f:
        html = f.read()

    prices = []
    pattern = r'<span class="item-price"[^>]*data-value="([^"]*)"[^>]*>'

    for match in re.finditer(pattern, html):
        prices.append(match.group(1))

    return prices

if __name__ == "__main__":
    prices = extract_prices("/app/data/products.html")
    with open("/app/output/prices.json", "w") as f:
        json.dump(prices, f, indent=2)
    print(f"Found {len(prices)} prices: {prices}")
PYEOF
sudo tee /app/src/scraper.py < /tmp/fixed_scraper.py > /dev/null
sudo python3 /app/src/scraper.py
