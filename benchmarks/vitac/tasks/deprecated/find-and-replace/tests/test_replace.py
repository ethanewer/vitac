import os
import glob

def test_no_acme_remaining():
    for path in glob.glob("/app/docs/*.txt"):
        content = open(path).read()
        assert "ACME Corp" not in content, f"ACME Corp still found in {path}"

def test_globex_in_readme():
    content = open("/app/docs/readme.txt").read()
    assert "Globex Inc" in content, "readme.txt should contain Globex Inc"

def test_globex_in_contact():
    content = open("/app/docs/contact.txt").read()
    assert "Globex Inc" in content, "contact.txt should contain Globex Inc"

def test_globex_in_handbook():
    content = open("/app/docs/handbook.txt").read()
    assert "Globex Inc" in content, "handbook.txt should contain Globex Inc"

def test_notes_unchanged():
    content = open("/app/docs/notes.txt").read()
    assert "This file has no company name." in content, "notes.txt should be unchanged"
