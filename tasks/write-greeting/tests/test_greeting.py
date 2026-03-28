import os

def test_greeting_file_exists():
    assert os.path.exists("/app/output/greeting.txt"), "greeting.txt should exist"

def test_greeting_exact_content():
    content = open("/app/output/greeting.txt").read().strip()
    assert content == "Dear Alice, Welcome to the team!", \
        f"Greeting should be exactly 'Dear Alice, Welcome to the team!', got: {content}"
