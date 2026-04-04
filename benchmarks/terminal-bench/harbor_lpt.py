#!/usr/bin/env python3
"""harbor-lpt: Harbor CLI wrapper with LPT scheduling and Docker image prefetching.

Two optimizations over the standard Harbor CLI:

1. LPT (Longest Processing Time first) scheduling — sorts trial configs by
   descending expected task runtime so the longest tasks start first. This
   minimizes total wall-clock time when running with concurrent workers.
   Harbor's TrialQueue uses asyncio.Semaphore (FIFO in CPython), so reordering
   the trial config list is sufficient to control execution order.

2. Docker image prefetching — before any trials start, sequentially pulls all
   Docker images needed by the job's tasks. This prevents concurrent pull storms
   that crash high-concurrency runs and avoids Docker API rate limits by checking
   the local cache first.

Usage: python3 harbor_lpt.py run [harbor flags...]
       (accepts all standard harbor CLI flags)
"""

import json
import subprocess
import sys
from pathlib import Path

import harbor.job as _harbor_job

# ---------------------------------------------------------------------------
# 1. LPT Scheduling
# ---------------------------------------------------------------------------

# Load per-task runtime estimates
_RUNTIMES_PATH = Path(__file__).parent / "task_runtimes.json"
_runtimes = json.loads(_RUNTIMES_PATH.read_text()) if _RUNTIMES_PATH.exists() else {}
_fallback = sorted(_runtimes.values())[len(_runtimes) // 2] if _runtimes else 0

_original_init_trial_configs = _harbor_job.Job._init_trial_configs


def _lpt_init(self):
    _original_init_trial_configs(self)

    def _task_runtime(tc):
        name = tc.task.get_task_id().get_name().split("/")[-1]
        return _runtimes.get(name, _fallback)

    self._trial_configs.sort(key=_task_runtime, reverse=True)


_harbor_job.Job._init_trial_configs = _lpt_init

# ---------------------------------------------------------------------------
# 2. Docker Image Prefetching
# ---------------------------------------------------------------------------


def _image_exists_locally(image: str) -> bool:
    """Check if a Docker image is already present in the local cache."""
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
    )
    return result.returncode == 0


def _pull_image(image: str) -> bool:
    """Pull a Docker image. Returns True on success."""
    result = subprocess.run(
        ["docker", "pull", image],
        stdout=sys.stderr,  # stream pull progress to stderr
        stderr=subprocess.STDOUT,
    )
    return result.returncode == 0


def _prefetch_docker_images(job: _harbor_job.Job) -> None:
    """Pre-pull all unique Docker images needed by the job's tasks.

    Reads each task's task.toml to find the docker_image field. Images that
    are already cached locally are skipped. Pulls happen sequentially to
    avoid concurrent pull storms and Docker API rate limits.
    """
    from harbor.models.task.task import Task

    images: dict[str, str] = {}  # image -> task_name
    seen_paths: set[Path] = set()

    for tc in job._task_configs:
        try:
            local_path = tc.get_local_path()
            if local_path in seen_paths:
                continue
            seen_paths.add(local_path)
            if not local_path.exists():
                continue

            task = Task(local_path)
            docker_image = task.config.environment.docker_image
            if docker_image and docker_image not in images:
                images[docker_image] = task.name
        except Exception:
            continue

    if not images:
        return

    print(f"\n==> Prefetching {len(images)} Docker image(s)...", file=sys.stderr)

    cached, pulled, failed = 0, 0, 0
    for image, task_name in sorted(images.items(), key=lambda kv: kv[1]):
        if _image_exists_locally(image):
            print(f"    {image} (cached)", file=sys.stderr)
            cached += 1
            continue

        print(f"    Pulling {image} (for {task_name})...", file=sys.stderr)
        if _pull_image(image):
            pulled += 1
        else:
            print(f"    WARNING: Failed to pull {image}", file=sys.stderr)
            failed += 1

    summary_parts = []
    if cached:
        summary_parts.append(f"{cached} cached")
    if pulled:
        summary_parts.append(f"{pulled} pulled")
    if failed:
        summary_parts.append(f"{failed} failed")
    print(
        f"==> Prefetch complete ({', '.join(summary_parts)})\n",
        file=sys.stderr,
    )


# Monkey-patch Job.run to prefetch images before starting trials
_original_run = _harbor_job.Job.run


async def _prefetch_and_run(self):
    _prefetch_docker_images(self)
    return await _original_run(self)


_harbor_job.Job.run = _prefetch_and_run

# ---------------------------------------------------------------------------
# 3. Run the normal Harbor CLI
# ---------------------------------------------------------------------------

from harbor.cli.main import app  # noqa: E402

app()
