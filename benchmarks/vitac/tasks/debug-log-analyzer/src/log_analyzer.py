#!/usr/bin/env python3
"""Analyze application log file and generate report."""
import json
import re

def analyze_log(filepath):
    with open(filepath) as f:
        lines = f.readlines()

    total_lines = len(lines)

    # Count errors - BUG 1: regex only matches ERROR at start of line
    error_count = 0
    for line in lines:
        if re.match(r'^ERROR', line):  # BUG: should search, not match from start
            error_count += 1

    # Calculate average response time
    total_response_time = 0
    for line in lines:
        match = re.search(r'completed in (\d+)ms', line)
        if match:
            total_response_time += int(match.group(1))

    # BUG 2: divides by total_lines instead of count of lines with response times
    avg_response_time = total_response_time / total_lines if total_lines > 0 else 0

    # Count requests (lines with "completed in")
    request_count = sum(1 for line in lines if 'completed in' in line)

    return {
        "error_count": error_count,
        "avg_response_time_ms": round(avg_response_time, 2),
        "total_requests": request_count,
        "total_lines": total_lines
    }

if __name__ == "__main__":
    report = analyze_log("/app/data/app.log")
    with open("/app/output/report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
