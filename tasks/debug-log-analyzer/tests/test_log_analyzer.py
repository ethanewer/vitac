import json
import os

def test_output_exists():
    assert os.path.exists("/app/output/report.json")

def test_error_count():
    with open("/app/output/report.json") as f:
        report = json.load(f)
    assert report["error_count"] == 4, f"Expected 4 errors, got {report['error_count']}"

def test_avg_response_time():
    with open("/app/output/report.json") as f:
        report = json.load(f)
    # (45 + 120 + 89 + 200) / 4 = 113.5
    expected = 113.5
    assert abs(report["avg_response_time_ms"] - expected) < 0.1, \
        f"Expected avg ~{expected}ms, got {report['avg_response_time_ms']}ms"

def test_request_count():
    with open("/app/output/report.json") as f:
        report = json.load(f)
    assert report["total_requests"] == 4, f"Expected 4 requests, got {report['total_requests']}"
