import os

def test_filtered_file_exists():
    assert os.path.exists("/app/output/filtered.log"), "filtered.log should exist"

def test_all_warn_lines_present():
    content = open("/app/output/filtered.log").read()
    assert "Using fallback database" in content
    assert "Deprecated API version" in content
    assert "SSL certificate expires" in content

def test_only_warn_lines():
    for line in open("/app/output/filtered.log"):
        if line.strip():
            assert "WARN" in line, f"Non-WARN line found: {line.strip()}"

def test_correct_line_count():
    lines = [l for l in open("/app/output/filtered.log") if l.strip()]
    assert len(lines) == 3, f"Expected 3 WARN lines, got {len(lines)}"

def test_no_error_lines():
    content = open("/app/output/filtered.log").read()
    assert "ERROR" not in content, "Should not contain ERROR lines"
