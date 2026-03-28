#!/usr/bin/env python3
"""Extract product prices from HTML file."""
import json
import re

def extract_prices(html_path):
    with open(html_path) as f:
        html = f.read()

    prices = []
    # BUG 1: wrong class name - should be "item-price" not "price"
    pattern = r'<span class="price"[^>]*href="([^"]*)"[^>]*>'  # BUG 2: extracts href, should extract data-value

    for match in re.finditer(pattern, html):
        prices.append(match.group(1))

    return prices

if __name__ == "__main__":
    prices = extract_prices("/app/data/products.html")
    with open("/app/output/prices.json", "w") as f:
        json.dump(prices, f, indent=2)
    print(f"Found {len(prices)} prices: {prices}")
