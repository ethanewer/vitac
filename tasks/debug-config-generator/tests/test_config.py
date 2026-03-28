import os


def test_output_exists():
    assert os.path.exists("/app/output/nginx.conf")


def test_correct_server_name():
    with open("/app/output/nginx.conf") as f:
        content = f.read()
    assert "server_name app.example.com" in content, \
        "server_name should be app.example.com"


def test_correct_proxy_pass():
    with open("/app/output/nginx.conf") as f:
        content = f.read()
    assert "proxy_pass http://backend:3000;" in content, \
        "proxy_pass should use backend:3000 with semicolon"


def test_proxy_pass_semicolon():
    with open("/app/output/nginx.conf") as f:
        content = f.read()
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('proxy_pass'):
            assert stripped.endswith(';'), f"proxy_pass missing semicolon: '{stripped}'"


def test_listen_port():
    with open("/app/output/nginx.conf") as f:
        content = f.read()
    assert "listen 80" in content


def test_no_localhost():
    with open("/app/output/nginx.conf") as f:
        content = f.read()
    assert "server_name localhost" not in content, "Should use domain, not localhost"
