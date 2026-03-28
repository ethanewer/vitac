"""Tests for the service restart noisy task."""
import json
import os


def test_service_state_exists():
    """Service state file should exist — services were restarted."""
    assert os.path.exists("/app/service_state.json"), \
        "Service state file should exist — no services were restarted"


def test_payment_gateway_restarted():
    """payment-gateway should have been restarted."""
    with open("/app/service_state.json") as f:
        state = json.load(f)
    assert "payment-gateway" in state["restarted"], \
        "payment-gateway was not restarted"


def test_notification_service_restarted():
    """notification-service should have been restarted."""
    with open("/app/service_state.json") as f:
        state = json.load(f)
    assert "notification-service" in state["restarted"], \
        "notification-service was not restarted"


def test_auth_service_not_restarted():
    """auth-service should NOT have been restarted."""
    with open("/app/service_state.json") as f:
        state = json.load(f)
    assert "auth-service" not in state["restarted"], \
        "auth-service should NOT have been restarted"


def test_user_api_not_restarted():
    """user-api should NOT have been restarted."""
    with open("/app/service_state.json") as f:
        state = json.load(f)
    assert "user-api" not in state["restarted"], \
        "user-api should NOT have been restarted"
