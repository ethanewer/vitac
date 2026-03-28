#!/usr/bin/env python3
"""Monolithic application - needs refactoring into modules."""
import json
from datetime import datetime

# --- Models ---
class User:
    def __init__(self, name, email, role="member"):
        self.name = name
        self.email = email
        self.role = role
        self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return {
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at
        }

class Product:
    def __init__(self, name, price, category):
        self.name = name
        self.price = price
        self.category = category

    def to_dict(self):
        return {
            "name": self.name,
            "price": self.price,
            "category": self.category
        }

# --- Utils ---
def format_currency(amount):
    return f"${amount:,.2f}"

def validate_email(email):
    return "@" in email and "." in email.split("@")[1]

def generate_report(users, products):
    report = {
        "total_users": len(users),
        "total_products": len(products),
        "total_value": sum(p.price for p in products),
        "users": [u.to_dict() for u in users],
        "products": [p.to_dict() for p in products]
    }
    return report

# --- Main ---
def main():
    users = [
        User("Alice", "alice@example.com", "admin"),
        User("Bob", "bob@example.com"),
        User("Charlie", "charlie@example.com"),
    ]

    products = [
        Product("Widget", 29.99, "tools"),
        Product("Gadget", 49.99, "electronics"),
        Product("Doohickey", 9.99, "misc"),
    ]

    report = generate_report(users, products)
    report["formatted_total"] = format_currency(report["total_value"])

    with open("/app/output/report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"Generated report: {len(users)} users, {len(products)} products")
    print(f"Total value: {format_currency(report['total_value'])}")

if __name__ == "__main__":
    main()
