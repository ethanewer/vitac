#!/usr/bin/env python3
"""Mock service control tool."""
import argparse
import json
import os
import sys

STATE_FILE = "/app/service_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"restarted": [], "actions": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

VALID_SERVICES = [
    "payment-gateway",
    "notification-service",
    "auth-service",
    "user-api",
]

def main():
    parser = argparse.ArgumentParser(description="Service control tool")
    parser.add_argument("action", choices=["restart", "status", "list"])
    parser.add_argument("service", nargs="?", help="Service name")
    args = parser.parse_args()

    state = load_state()

    if args.action == "list":
        print("Available services:")
        for svc in VALID_SERVICES:
            print(f"  - {svc}")
        return

    if args.action == "status":
        svc = args.service or "all"
        print(f"Status for {svc}: running")
        return

    if args.action == "restart":
        if not args.service:
            print("Error: service name required for restart", file=sys.stderr)
            sys.exit(1)
        if args.service not in VALID_SERVICES:
            print(f"Error: unknown service '{args.service}'", file=sys.stderr)
            sys.exit(1)

        print(f"Restarting {args.service}...")
        print(f"{args.service} restarted successfully.")

        state["restarted"].append(args.service)
        state["actions"].append({"action": "restart", "service": args.service})
        save_state(state)

if __name__ == "__main__":
    main()
