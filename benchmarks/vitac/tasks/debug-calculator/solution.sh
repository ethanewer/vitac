#!/bin/bash
# Fix the two bugs in calculator.py
cat > /tmp/fixed_calculator.py << 'PYEOF'
#!/usr/bin/env python3
"""Calculator module with test mode."""
import sys
import json

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        return None
    return a / b

def run_tests():
    results = {}
    results["add_3_4"] = add(3, 4)
    results["subtract_10_3"] = subtract(10, 3)
    results["multiply_5_6"] = multiply(5, 6)
    results["divide_10_4"] = divide(10, 4)
    results["divide_7_2"] = divide(7, 2)

    for name, result in results.items():
        print(f"{name} = {result}")

    with open("/app/output/results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Results written to /app/output/results.json")

if __name__ == "__main__":
    if "--test" in sys.argv:
        run_tests()
    else:
        print("Usage: calculator.py --test")
PYEOF
sudo tee /app/src/calculator.py < /tmp/fixed_calculator.py > /dev/null
sudo python3 /app/src/calculator.py --test
