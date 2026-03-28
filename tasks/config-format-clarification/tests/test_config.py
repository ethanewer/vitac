"""Tests for the config format clarification task."""
import os
import yaml


def test_config_file_exists():
    """Config file should exist in YAML format."""
    assert os.path.exists("/app/config/app_config.yaml"), \
        "Config file /app/config/app_config.yaml should exist"


def test_config_is_valid_yaml():
    """Config file should be valid YAML."""
    with open("/app/config/app_config.yaml") as f:
        config = yaml.safe_load(f)
    assert isinstance(config, dict), "Config should be a YAML mapping"


def test_app_name():
    """Config should have correct app_name."""
    with open("/app/config/app_config.yaml") as f:
        config = yaml.safe_load(f)
    assert config.get("app_name") == "widget-service"


def test_port():
    """Config should have correct port."""
    with open("/app/config/app_config.yaml") as f:
        config = yaml.safe_load(f)
    assert config.get("port") == 8080


def test_database_config():
    """Config should have correct database settings."""
    with open("/app/config/app_config.yaml") as f:
        config = yaml.safe_load(f)
    db = config.get("database", {})
    assert db.get("host") == "db.internal.example.com"
    assert db.get("port") == 5432
    assert db.get("name") == "widgets_prod"


def test_log_level():
    """Config should have correct log_level."""
    with open("/app/config/app_config.yaml") as f:
        config = yaml.safe_load(f)
    assert config.get("log_level") == "info"
