import os

def _read_env():
    d = {}
    with open("/app/config/.env") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
    return d

def test_env_file_exists():
    assert os.path.exists("/app/config/.env"), ".env file should exist"

def test_app_port():
    env = _read_env()
    assert env.get("APP_PORT") == "3000", f"APP_PORT should be 3000, got {env.get('APP_PORT')}"

def test_db_host():
    env = _read_env()
    assert env.get("DB_HOST") == "postgres.local", f"DB_HOST should be postgres.local"

def test_db_name():
    env = _read_env()
    assert env.get("DB_NAME") == "myapp", f"DB_NAME should be myapp"

def test_secret_key():
    env = _read_env()
    assert env.get("SECRET_KEY") == "supersecret123", f"SECRET_KEY should be supersecret123"
