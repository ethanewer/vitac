"""Dataset loading and task discovery."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from vitac.types import TaskDef

logger = logging.getLogger(__name__)

REQUIRED_TASK_FILES = ["task.yaml", "Dockerfile", "docker-compose.yaml", "run-tests.sh"]


class Dataset:
    """Load and manage a collection of tasks from a directory."""

    def __init__(
        self,
        path: Path,
        task_ids: list[str] | None = None,
        exclude_task_ids: list[str] | None = None,
        categories: list[str] | None = None,
    ):
        self._path = Path(path)
        self._task_ids = task_ids
        self._exclude_task_ids = set(exclude_task_ids or [])
        self._categories = set(categories) if categories else None
        self._tasks: list[TaskDef] = []
        self._task_paths: dict[str, Path] = {}
        self._load()

    def _load(self) -> None:
        """Discover and load all valid tasks from the directory."""
        if not self._path.is_dir():
            raise ValueError(f"Tasks directory not found: {self._path}")

        for task_dir in sorted(self._path.iterdir()):
            if not task_dir.is_dir():
                continue

            task_yaml = task_dir / "task.yaml"
            if not task_yaml.exists():
                continue

            task_id = task_dir.name

            # Apply filters
            if self._task_ids and task_id not in self._task_ids:
                continue
            if task_id in self._exclude_task_ids:
                continue

            try:
                task = load_task(task_dir)
            except Exception as e:
                logger.warning(f"Skipping invalid task {task_id}: {e}")
                continue

            if self._categories and task.category not in self._categories:
                continue

            self._tasks.append(task)
            self._task_paths[task_id] = task_dir

    @property
    def tasks(self) -> list[TaskDef]:
        return list(self._tasks)

    @property
    def task_paths(self) -> dict[str, Path]:
        return dict(self._task_paths)

    def __len__(self) -> int:
        return len(self._tasks)

    def __iter__(self):
        return iter(self._tasks)

    def get_task(self, task_id: str) -> TaskDef:
        for task in self._tasks:
            if task.task_id == task_id:
                return task
        raise KeyError(f"Task not found: {task_id}")

    def get_task_path(self, task_id: str) -> Path:
        return self._task_paths[task_id]


def load_task(task_dir: Path) -> TaskDef:
    """Load a TaskDef from a task directory."""
    task_yaml = task_dir / "task.yaml"
    with open(task_yaml) as f:
        data = yaml.safe_load(f)

    task = TaskDef(**data)
    task.task_id = task_dir.name
    task.task_path = task_dir
    return task


def validate_task_dir(task_dir: Path) -> list[str]:
    """Validate a task directory has all required files. Returns list of errors."""
    errors = []
    for filename in REQUIRED_TASK_FILES:
        if not (task_dir / filename).exists():
            errors.append(f"Missing required file: {filename}")

    task_yaml = task_dir / "task.yaml"
    if task_yaml.exists():
        try:
            with open(task_yaml) as f:
                data = yaml.safe_load(f)
            TaskDef(**data)
        except Exception as e:
            errors.append(f"Invalid task.yaml: {e}")

    return errors
