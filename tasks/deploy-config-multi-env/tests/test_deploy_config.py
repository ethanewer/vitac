import json
import os

def _load(env):
    path = f"/app/deploy/{env}.json"
    assert os.path.exists(path), f"{path} not found"
    with open(path) as f:
        return json.load(f)

def test_dev_exists():
    _load("dev")

def test_staging_exists():
    _load("staging")

def test_prod_exists():
    _load("prod")

def test_dev_database():
    c = _load("dev")
    assert c["database"]["host"] == "localhost"
    assert c["database"]["name"] == "myservice_dev"
    assert c["database"]["pool_size"] == 5

def test_staging_database():
    c = _load("staging")
    assert c["database"]["host"] == "staging-db.internal"
    assert c["database"]["name"] == "myservice_staging"
    assert c["database"]["pool_size"] == 10

def test_prod_database():
    c = _load("prod")
    assert c["database"]["host"] == "prod-db.internal"
    assert c["database"]["name"] == "myservice_prod"
    assert c["database"]["pool_size"] == 50

def test_dev_cache():
    c = _load("dev")
    assert c["cache"]["host"] == "localhost"

def test_staging_cache():
    c = _load("staging")
    assert c["cache"]["host"] == "staging-cache.internal"

def test_prod_cache():
    c = _load("prod")
    assert c["cache"]["host"] == "prod-cache.internal"

def test_prod_no_beta():
    c = _load("prod")
    assert c["features"]["beta_features"] == False

def test_dev_beta_enabled():
    c = _load("dev")
    assert c["features"]["beta_features"] == True

def test_replicas():
    assert _load("dev")["replicas"] == 1
    assert _load("staging")["replicas"] == 2
    assert _load("prod")["replicas"] == 5

def test_log_levels():
    assert _load("dev")["log_level"] == "debug"
    assert _load("staging")["log_level"] == "info"
    assert _load("prod")["log_level"] == "warn"
