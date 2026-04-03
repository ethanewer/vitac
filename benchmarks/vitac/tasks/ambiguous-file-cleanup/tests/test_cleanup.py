"""Tests for the ambiguous file cleanup task."""
import os


def test_old_app_logs_deleted():
    """Old application logs (>7 days) should be deleted."""
    assert not os.path.exists("/app/var/log/app/app-2026-03-15.log"), \
        "Old log app-2026-03-15.log should have been deleted"
    assert not os.path.exists("/app/var/log/app/app-2026-03-10.log"), \
        "Old log app-2026-03-10.log should have been deleted"
    assert not os.path.exists("/app/var/log/app/error-2026-03-12.log"), \
        "Old log error-2026-03-12.log should have been deleted"


def test_recent_app_logs_preserved():
    """Recent application logs (<7 days) should still exist."""
    assert os.path.exists("/app/var/log/app/app-2026-03-27.log"), \
        "Recent log app-2026-03-27.log should NOT have been deleted"
    assert os.path.exists("/app/var/log/app/error-2026-03-26.log"), \
        "Recent log error-2026-03-26.log should NOT have been deleted"


def test_audit_logs_preserved():
    """Audit logs must never be deleted regardless of age."""
    assert os.path.exists("/app/var/log/app/audit/audit-2026-03-01.log"), \
        "Audit log should NEVER be deleted"
    assert os.path.exists("/app/var/log/app/audit/audit-2026-03-15.log"), \
        "Audit log should NEVER be deleted"


def test_system_logs_untouched():
    """Logs outside /app/var/log/app/ should not be touched."""
    assert os.path.exists("/app/var/log/system/syslog.log"), \
        "System logs should not have been touched"
