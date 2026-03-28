import os

def test_db_port_fixed():
    with open("/app/config/db.conf") as f:
        content = f.read()
    assert "port=5433" in content, f"DB port should be 5433, got: {content}"
    assert "port=5432" not in content, "Old port 5432 should be replaced"

def test_old_cache_cleared():
    cache_files = os.listdir("/app/cache/")
    for f in ["old1.tmp", "old2.tmp", "old3.tmp"]:
        assert f not in cache_files, f"Old cache file {f} should be deleted"

def test_recent_cache_kept():
    assert os.path.exists("/app/cache/recent.tmp"), "Recent cache should be kept"

def test_important_data_kept():
    assert os.path.exists("/app/cache/important.dat"), "important.dat should be kept"

def test_cert_renewed():
    with open("/app/certs/active/server.pem") as f:
        content = f.read()
    assert "RENEWED" in content, f"Active cert should be the renewed one, got: {content}"
    assert "EXPIRED" not in content, "Expired cert should be replaced"

def test_db_host_unchanged():
    with open("/app/config/db.conf") as f:
        content = f.read()
    assert "host=db.internal" in content, "DB host should remain unchanged"
