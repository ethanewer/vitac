"""Tests for the database migration correction task."""
import json
import os


def test_migration_state_exists():
    """Migration should have been run."""
    assert os.path.exists("/app/migration_state.json"), \
        "Migration state file should exist — migration was not run"


def test_migrated_to_v4():
    """The final migration target should be v4, not v5."""
    with open("/app/migration_state.json") as f:
        state = json.load(f)
    assert state["target"] == "v4", \
        f"Expected migration to v4, but got {state['target']}"


def test_migration_completed():
    """Migration should have completed (not dry run)."""
    with open("/app/migration_state.json") as f:
        state = json.load(f)
    assert state["status"] == "completed", \
        f"Expected completed migration, got status={state['status']}"
