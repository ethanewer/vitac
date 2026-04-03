import os

FILES_DIR = "/app/data/files"

def test_report_renamed():
    assert os.path.exists(os.path.join(FILES_DIR, "2026-03-15_report_final.txt")), \
        f"Expected 2026-03-15_report_final.txt in {os.listdir(FILES_DIR)}"

def test_data_renamed():
    assert os.path.exists(os.path.join(FILES_DIR, "2026-03-20_data.csv")), \
        f"Expected 2026-03-20_data.csv in {os.listdir(FILES_DIR)}"

def test_log_renamed():
    assert os.path.exists(os.path.join(FILES_DIR, "2026-03-28_log_backup.log")), \
        f"Expected 2026-03-28_log_backup.log in {os.listdir(FILES_DIR)}"

def test_notes_unchanged():
    assert os.path.exists(os.path.join(FILES_DIR, "notes.txt")), \
        "notes.txt should remain unchanged"

def test_old_names_gone():
    files = os.listdir(FILES_DIR)
    assert "report_20260315_final.txt" not in files, "Old filename should be gone"
    assert "data_20260320.csv" not in files, "Old filename should be gone"

def test_correct_file_count():
    files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
    assert len(files) == 4, f"Expected 4 files, got {len(files)}: {files}"
