def test_hosts_file_exists():
    import os
    assert os.path.exists("/app/etc/hosts"), "hosts file should exist"

def test_original_entries_preserved():
    content = open("/app/etc/hosts").read()
    assert "127.0.0.1" in content, "Original localhost entry should be preserved"

def test_new_entry_present():
    content = open("/app/etc/hosts").read()
    assert "10.0.1.50" in content, "New IP should be in hosts file"
    assert "api.internal.corp" in content, "New hostname should be in hosts file"

def test_new_entry_on_same_line():
    for line in open("/app/etc/hosts"):
        if "10.0.1.50" in line and "api.internal.corp" in line:
            return
    assert False, "IP and hostname should be on the same line"
