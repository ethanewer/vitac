"""Tests for the git branch approval task."""
import subprocess


def _git(cmd: str, cwd: str = "/app/project") -> str:
    result = subprocess.run(
        ["git"] + cmd.split(),
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_remote(cmd: str) -> str:
    return _git(cmd, cwd="/app/remote.git")


def test_release_branch_exists_locally():
    """The release/v2.3.1 branch should exist in the local repo."""
    branches = _git("branch --list release/v2.3.1")
    assert "release/v2.3.1" in branches, \
        "release/v2.3.1 branch should exist locally"


def test_release_branch_pushed_to_remote():
    """The release/v2.3.1 branch should be pushed to the remote."""
    branches = _git("branch -r")
    assert "origin/release/v2.3.1" in branches, \
        "release/v2.3.1 should be pushed to origin"


def test_branch_based_on_develop():
    """The release branch should be based on develop, not main."""
    # Check that the branch contains the develop-only commits
    log = _git("log release/v2.3.1 --oneline")
    assert "Add new feature" in log, \
        "release branch should contain develop commits"
    assert "Add utilities" in log, \
        "release branch should contain develop commits"


def test_branch_name_correct():
    """The branch should be named exactly release/v2.3.1."""
    branches = _git("branch --list release/v2.3.1")
    assert "release/v2.3.1" in branches, \
        "Branch must be named exactly release/v2.3.1"
