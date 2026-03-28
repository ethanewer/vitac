import os
import tarfile

def test_archive_exists():
    assert os.path.exists("/app/output/archive.tar.gz"), "archive.tar.gz should exist"

def test_archive_is_valid():
    with tarfile.open("/app/output/archive.tar.gz", "r:gz") as tar:
        names = tar.getnames()
        assert len(names) > 0, "Archive should not be empty"

def test_csv_files_included():
    with tarfile.open("/app/output/archive.tar.gz", "r:gz") as tar:
        names = tar.getnames()
        csv_names = [n for n in names if n.endswith(".csv")]
        assert len(csv_names) == 3, f"Expected 3 csv files, got {len(csv_names)}: {csv_names}"

def test_no_tmp_files():
    with tarfile.open("/app/output/archive.tar.gz", "r:gz") as tar:
        names = tar.getnames()
        tmp_names = [n for n in names if n.endswith(".tmp")]
        assert len(tmp_names) == 0, f"Archive should not contain .tmp files: {tmp_names}"

def test_no_log_files():
    with tarfile.open("/app/output/archive.tar.gz", "r:gz") as tar:
        names = tar.getnames()
        log_names = [n for n in names if n.endswith(".log")]
        assert len(log_names) == 0, f"Archive should not contain .log files: {log_names}"
