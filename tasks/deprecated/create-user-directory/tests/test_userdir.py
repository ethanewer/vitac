import os

def test_user_dir_exists():
    assert os.path.isdir("/app/users/jdoe"), "User directory /app/users/jdoe should exist"

def test_documents_dir():
    assert os.path.isdir("/app/users/jdoe/documents"), "documents subdir should exist"

def test_downloads_dir():
    assert os.path.isdir("/app/users/jdoe/downloads"), "downloads subdir should exist"

def test_projects_dir():
    assert os.path.isdir("/app/users/jdoe/projects"), "projects subdir should exist"
