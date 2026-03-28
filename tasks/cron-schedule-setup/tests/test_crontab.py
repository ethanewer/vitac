import os
import re

CRONTAB_PATH = "/app/config/crontab"

def _read_lines():
    assert os.path.exists(CRONTAB_PATH), f"{CRONTAB_PATH} not found"
    with open(CRONTAB_PATH) as f:
        lines = [l.strip() for l in f if l.strip() and not l.strip().startswith('#')]
    return lines

def test_file_exists():
    assert os.path.exists(CRONTAB_PATH)

def test_five_entries():
    lines = _read_lines()
    assert len(lines) == 5, f"Expected 5 cron entries, got {len(lines)}: {lines}"

def test_daily_backup():
    lines = _read_lines()
    found = any("30 2 * * *" in l and "backup-db" in l for l in lines)
    assert found, "Missing daily backup at 2:30 AM"

def test_log_rotation():
    lines = _read_lines()
    found = any("0 */6 * * *" in l and "rotate-logs" in l for l in lines)
    assert found, "Missing 6-hourly log rotation"

def test_health_check():
    lines = _read_lines()
    found = any("*/5 * * * *" in l and "health-check" in l for l in lines)
    assert found, "Missing 5-minute health check"

def test_weekly_report():
    lines = _read_lines()
    found = any("0 8 * * 0" in l and "weekly-report" in l for l in lines)
    assert found, "Missing weekly report on Sunday 8 AM"

def test_monthly_cleanup():
    lines = _read_lines()
    found = any("0 0 1 * *" in l and "monthly-cleanup" in l for l in lines)
    assert found, "Missing monthly cleanup on 1st at midnight"

def test_valid_cron_syntax():
    """Each line should have 5 time fields + command."""
    lines = _read_lines()
    for line in lines:
        parts = line.split()
        assert len(parts) >= 6, f"Invalid cron line (need 5 time fields + command): {line}"
