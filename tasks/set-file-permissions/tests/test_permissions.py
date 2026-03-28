import os
import stat

def test_file_exists():
    assert os.path.exists("/app/data/report.csv"), "report.csv should exist"

def test_permissions_750():
    st = os.stat("/app/data/report.csv")
    mode = oct(st.st_mode)[-3:]
    assert mode == "750", f"Permissions should be 750, got {mode}"
