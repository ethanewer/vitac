import os
import json

def _read(path):
    with open(path) as f:
        return f.read()

def test_no_old_db_password():
    for root, dirs, files in os.walk("/app"):
        if root.startswith("/app/src") or root.startswith("/tests"):
            continue
        for fname in files:
            path = os.path.join(root, fname)
            try:
                content = _read(path)
                assert "oldpass123" not in content, f"Old DB password found in {path}"
            except (UnicodeDecodeError, PermissionError):
                pass

def test_no_old_api_key():
    for root, dirs, files in os.walk("/app"):
        if root.startswith("/app/src") or root.startswith("/tests"):
            continue
        for fname in files:
            path = os.path.join(root, fname)
            try:
                content = _read(path)
                assert "sk-old-key-abc123" not in content, f"Old API key found in {path}"
            except (UnicodeDecodeError, PermissionError):
                pass

def test_no_old_jwt_secret():
    for root, dirs, files in os.walk("/app"):
        if root.startswith("/app/src") or root.startswith("/tests"):
            continue
        for fname in files:
            path = os.path.join(root, fname)
            try:
                content = _read(path)
                assert "jwt-secret-old-value" not in content, f"Old JWT secret found in {path}"
            except (UnicodeDecodeError, PermissionError):
                pass

def test_new_db_password_in_database_yml():
    content = _read("/app/config/database.yml")
    assert "Kx9mP2qL7nW" in content, "New DB password not in database.yml"

def test_new_api_key_in_api_conf():
    content = _read("/app/config/api.conf")
    assert "sk-new-key-xyz789" in content, "New API key not in api.conf"

def test_new_jwt_in_auth_config():
    content = _read("/app/services/auth/config.json")
    assert "hN4kQ8wR2vBj5mT" in content, "New JWT secret not in auth config"

def test_new_db_password_in_worker():
    content = _read("/app/services/worker/env")
    assert "Kx9mP2qL7nW" in content, "New DB password not in worker env"

def test_env_production_all_new():
    content = _read("/app/env/.env.production")
    assert "Kx9mP2qL7nW" in content, "New DB password not in .env.production"
    assert "sk-new-key-xyz789" in content, "New API key not in .env.production"
    assert "hN4kQ8wR2vBj5mT" in content, "New JWT secret not in .env.production"

def test_non_secret_values_unchanged():
    content = _read("/app/config/database.yml")
    assert "db.internal" in content, "DB host should be unchanged"
    content = _read("/app/config/api.conf")
    assert "https://api.example.com" in content, "API endpoint should be unchanged"
    content = _read("/app/services/auth/config.json")
    data = json.loads(content)
    assert data["token_expiry"] == 3600, "Token expiry should be unchanged"
