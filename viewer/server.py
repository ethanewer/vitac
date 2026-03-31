"""
VITAC Trace Viewer — FastAPI backend.

Scans the results/ directory and serves JSON APIs for the frontend SPA.
Also serves audio WAV files and static frontend assets.

Usage:
    cd viewer && uv run uvicorn server:app --reload --port 8080
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

VIEWER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = VIEWER_DIR.parent
RESULTS_DIR = PROJECT_ROOT / "results"
TASKS_DIR = PROJECT_ROOT / "tasks"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="VITAC Trace Viewer")

# Mount static assets
app.mount("/static", StaticFiles(directory=VIEWER_DIR / "static"), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    """Load and parse a JSON file, returning None on failure."""
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _infer_system_from_run(run_id: str, run_dir: Path) -> str:
    """Try to figure out which voice system was used for a run.

    Heuristics:
    1. Check ts-runner-result.json files aren't available at run level,
       so we check the run-id naming pattern.
    2. Fall back to 'unknown'.
    """
    run_lower = run_id.lower()
    if "opus" in run_lower and "medium" in run_lower:
        return "claude-opus-medium-voice"
    if "opus" in run_lower and "high" in run_lower:
        return "claude-opus-high-voice"
    if "opus" in run_lower and "max" in run_lower:
        return "claude-opus-max-voice"
    if "gpt" in run_lower and "xhigh" in run_lower:
        return "gpt-xhigh-voice"
    if "gpt" in run_lower and "high" in run_lower:
        return "gpt-high-voice"
    if "gpt" in run_lower and "medium" in run_lower:
        return "gpt-medium-voice"
    if "gpt" in run_lower and "audio" in run_lower:
        return "gpt-audio-voice"
    if "gemini" in run_lower and "flash" in run_lower:
        return "gemini-flash-voice"
    if "gemini" in run_lower and "pro" in run_lower:
        return "gemini-pro-voice"
    if "minimax" in run_lower or "m2" in run_lower:
        return "minimax-m2-voice"

    # Try to find system in a ts-runner stdout log
    for stdout_log in run_dir.rglob("ts-runner-stdout.log"):
        try:
            text = stdout_log.read_text(errors="replace")[:2000]
            for line in text.splitlines():
                if line.startswith("System: "):
                    return line.split("System: ", 1)[1].strip()
        except Exception:
            pass

    return "unknown"


def _load_task_yaml(task_id: str) -> dict[str, Any] | None:
    """Load task.yaml for a given task_id."""
    import yaml  # type: ignore

    task_yaml = TASKS_DIR / task_id / "task.yaml"
    if not task_yaml.exists():
        return None
    try:
        return yaml.safe_load(task_yaml.read_text())
    except Exception:
        return None


def _find_trial_dir(run_id: str, task_id: str, trial_name: str) -> Path | None:
    """Locate the trial directory on disk."""
    candidate = RESULTS_DIR / run_id / task_id / trial_name
    if candidate.is_dir():
        return candidate
    return None


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------


@app.get("/api/runs")
def list_runs() -> list[dict[str, Any]]:
    """List all benchmark runs with summary stats."""
    if not RESULTS_DIR.is_dir():
        return []

    runs: list[dict[str, Any]] = []
    for run_dir in sorted(RESULTS_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name
        results_json = run_dir / "results.json"
        data = _load_json(results_json)
        if data is None:
            continue

        results_list = data.get("results", [])
        n_total = len(results_list)
        n_resolved = sum(1 for r in results_list if r.get("is_resolved"))
        accuracy = n_resolved / n_total if n_total else 0.0

        system = _infer_system_from_run(run_id, run_dir)

        task_ids = sorted({r.get("task_id", "") for r in results_list})

        runs.append(
            {
                "run_id": run_id,
                "system": system,
                "n_total": n_total,
                "n_resolved": n_resolved,
                "accuracy": accuracy,
                "task_ids": task_ids,
            }
        )
    return runs


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    """Get all trial results for a specific run."""
    run_dir = RESULTS_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(404, f"Run not found: {run_id}")

    data = _load_json(run_dir / "results.json")
    if data is None:
        raise HTTPException(404, f"No results.json for run: {run_id}")

    system = _infer_system_from_run(run_id, run_dir)
    data["system"] = system

    # Enrich each trial with info about whether audio/trace is available
    for trial in data.get("results", []):
        task_id = trial.get("task_id", "")
        trial_name = trial.get("trial_name", "")
        trial_dir = _find_trial_dir(run_id, task_id, trial_name)
        trial["has_trace"] = False
        trial["has_audio"] = False
        if trial_dir:
            ts_result = trial_dir / "agent-logs" / "ts-runner-result.json"
            trial["has_trace"] = ts_result.exists()
            audio_dir = trial_dir / "agent-logs" / "ts-runner-result_audio"
            trial["has_audio"] = audio_dir.is_dir() and any(audio_dir.glob("*.wav"))

    return data


@app.get("/api/runs/{run_id}/{task_id}/{trial_name}/trace")
def get_trace(run_id: str, task_id: str, trial_name: str) -> dict[str, Any]:
    """Get the voice message trace for a specific trial."""
    trial_dir = _find_trial_dir(run_id, task_id, trial_name)
    if trial_dir is None:
        raise HTTPException(404, "Trial directory not found")

    ts_result_path = trial_dir / "agent-logs" / "ts-runner-result.json"
    data = _load_json(ts_result_path)
    if data is None:
        raise HTTPException(404, "No ts-runner-result.json for this trial")

    # Also load the trial results for metadata
    trial_results = _load_json(trial_dir / "results.json")

    # Check for audio availability
    audio_dir = trial_dir / "agent-logs" / "ts-runner-result_audio"
    has_audio = audio_dir.is_dir()

    # Load task definition for context
    task_def = _load_task_yaml(task_id)

    return {
        "trace": data,
        "trial_results": trial_results,
        "task_def": task_def,
        "has_audio": has_audio,
    }


@app.get("/api/audio/{run_id}/{task_id}/{trial_name}/{filename}")
def get_audio(run_id: str, task_id: str, trial_name: str, filename: str):
    """Serve a WAV audio file for a specific voice message."""
    trial_dir = _find_trial_dir(run_id, task_id, trial_name)
    if trial_dir is None:
        raise HTTPException(404, "Trial directory not found")

    audio_path = trial_dir / "agent-logs" / "ts-runner-result_audio" / filename
    if not audio_path.exists() or not audio_path.suffix == ".wav":
        raise HTTPException(404, f"Audio file not found: {filename}")

    return FileResponse(audio_path, media_type="audio/wav")


@app.get("/api/aggregate")
def get_aggregate() -> dict[str, Any]:
    """Aggregate pass/fail data across all runs, grouped by task and system."""
    if not RESULTS_DIR.is_dir():
        return {"tasks": {}, "systems": set()}

    # task_id -> system -> { "passed": N, "failed": N, "total": N }
    task_system_matrix: dict[str, dict[str, dict[str, int]]] = {}
    all_systems: set[str] = set()

    for run_dir in sorted(RESULTS_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name
        data = _load_json(run_dir / "results.json")
        if data is None:
            continue

        system = _infer_system_from_run(run_id, run_dir)
        all_systems.add(system)

        for trial in data.get("results", []):
            task_id = trial.get("task_id", "")
            resolved = trial.get("is_resolved", False)

            if task_id not in task_system_matrix:
                task_system_matrix[task_id] = {}
            if system not in task_system_matrix[task_id]:
                task_system_matrix[task_id][system] = {
                    "passed": 0,
                    "failed": 0,
                    "total": 0,
                }

            entry = task_system_matrix[task_id][system]
            entry["total"] += 1
            if resolved:
                entry["passed"] += 1
            else:
                entry["failed"] += 1

    return {
        "tasks": task_system_matrix,
        "systems": sorted(all_systems),
    }


# ---------------------------------------------------------------------------
# SPA fallback — serve index.html for all non-API routes
# ---------------------------------------------------------------------------


@app.get("/")
def index():
    """Serve the SPA."""
    return HTMLResponse((VIEWER_DIR / "static" / "index.html").read_text())
