import json

def _load():
    with open("/app/config/settings.json") as f:
        return json.load(f)

def test_port_is_8080():
    d = _load()
    assert d["port"] == 8080, f"port should be 8080, got {d['port']}"

def test_debug_is_false():
    d = _load()
    assert d["debug"] is False, f"debug should be False, got {d['debug']}"

def test_db_host_updated():
    d = _load()
    assert d["database"]["host"] == "db.prod.internal", f"database.host should be db.prod.internal, got {d['database']['host']}"

def test_unchanged_values_preserved():
    d = _load()
    assert d["app_name"] == "myservice", "app_name should be unchanged"
    assert d["log_level"] == "info", "log_level should be unchanged"
    assert d["database"]["port"] == 5432, "database.port should be unchanged"
    assert d["database"]["name"] == "mydb", "database.name should be unchanged"
