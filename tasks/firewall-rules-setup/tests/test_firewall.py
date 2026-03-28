import os

RULES_PATH = "/app/config/firewall.rules"

def _read_rules():
    assert os.path.exists(RULES_PATH), f"{RULES_PATH} not found"
    with open(RULES_PATH) as f:
        return f.read()

def test_file_exists():
    assert os.path.exists(RULES_PATH)

def test_ssh_restricted():
    rules = _read_rules()
    # SSH should be allowed only from 10.0.0.0/8
    assert "dport 22" in rules and "10.0.0.0/8" in rules, \
        "SSH (22) should be restricted to 10.0.0.0/8"

def test_http_open():
    rules = _read_rules()
    # Find the line with dport 80 - should NOT have a source restriction
    for line in rules.split('\n'):
        if 'dport 80' in line and 'ACCEPT' in line:
            assert '-s ' not in line or '0.0.0.0/0' in line, \
                "HTTP (80) should be open to all"
            return
    assert False, "No rule found allowing HTTP (port 80)"

def test_https_open():
    rules = _read_rules()
    for line in rules.split('\n'):
        if 'dport 443' in line and 'ACCEPT' in line:
            assert '-s ' not in line or '0.0.0.0/0' in line, \
                "HTTPS (443) should be open to all"
            return
    assert False, "No rule found allowing HTTPS (port 443)"

def test_postgres_restricted():
    rules = _read_rules()
    assert "dport 5432" in rules and "10.0.1.0/24" in rules, \
        "PostgreSQL (5432) should be restricted to 10.0.1.0/24"

def test_default_drop():
    rules = _read_rules()
    assert "INPUT DROP" in rules or ":INPUT DROP" in rules, \
        "Default INPUT policy should be DROP"

def test_output_accept():
    rules = _read_rules()
    assert "OUTPUT ACCEPT" in rules or ":OUTPUT ACCEPT" in rules, \
        "Default OUTPUT policy should be ACCEPT"

def test_established_connections():
    rules = _read_rules()
    assert "ESTABLISHED" in rules, \
        "Should allow established/related connections"

def test_no_wide_open_ssh():
    """SSH should NOT be open to everyone."""
    rules = _read_rules()
    for line in rules.split('\n'):
        if 'dport 22' in line and 'ACCEPT' in line:
            assert '10.0.0.0/8' in line, \
                f"SSH rule should restrict source to 10.0.0.0/8: {line}"
