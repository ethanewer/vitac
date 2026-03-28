import json
import os
import subprocess

SRC = "/app/src"

def test_models_exists():
    assert os.path.exists(f"{SRC}/models.py"), "models.py should exist"

def test_utils_exists():
    assert os.path.exists(f"{SRC}/utils.py"), "utils.py should exist"

def test_main_exists():
    assert os.path.exists(f"{SRC}/main.py"), "main.py should exist"

def test_main_runs():
    result = subprocess.run(
        ["python3", f"{SRC}/main.py"],
        capture_output=True, text=True, cwd=SRC
    )
    assert result.returncode == 0, f"main.py failed: {result.stderr}"

def test_report_generated():
    assert os.path.exists("/app/output/report.json")

def test_report_content():
    with open("/app/output/report.json") as f:
        report = json.load(f)
    assert report["total_users"] == 3
    assert report["total_products"] == 3
    assert report["total_value"] == 89.97
    assert "formatted_total" in report

def test_models_has_classes():
    with open(f"{SRC}/models.py") as f:
        content = f.read()
    assert "class User" in content
    assert "class Product" in content

def test_utils_has_functions():
    with open(f"{SRC}/utils.py") as f:
        content = f.read()
    assert "def format_currency" in content
    assert "def generate_report" in content

def test_main_imports():
    with open(f"{SRC}/main.py") as f:
        content = f.read()
    assert "from models import" in content or "import models" in content
    assert "from utils import" in content or "import utils" in content
