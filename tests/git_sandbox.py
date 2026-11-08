"""Helpers for arranging real git repositories in tests.

Each sandbox is wired up the same way a team's would be: a bare repository
stands in for the hosted remote, and a second clone stands in for a teammate
pushing their own work.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Repos:
    """The repositories involved in a scenario."""

    local: Path
    remote: Path
    teammate: Path


def git(cwd: Path, *args: str) -> str:
    """Run a git command to arrange a scenario and return its output."""
    completed = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def write_file(repo: Path, name: str, content: str = "data\n") -> None:
    (repo / name).write_text(content)


def commit(repo: Path, label: str, count: int = 1) -> None:
    """Create ``count`` commits, each adding a new file."""
    for number in range(count):
        write_file(repo, f"{label}-{number}.txt")
        git(repo, "add", ".")
        git(repo, "commit", "-m", f"{label} {number}")


def teammate_pushes(repos: Repos, count: int = 1) -> None:
    """Publish new commits to the remote without the local repo knowing."""
    commit(repos.teammate, "teammate", count)
    git(repos.teammate, "push")


def teammate_pushes_and_local_fetches(repos: Repos, count: int = 1) -> None:
    teammate_pushes(repos, count)
    git(repos.local, "fetch")


def stage_a_change(repos: Repos) -> None:
    write_file(repos.local, "initial-0.txt", "edited\n")
    git(repos.local, "add", "initial-0.txt")


def edit_without_staging(repos: Repos) -> None:
    write_file(repos.local, "initial-0.txt", "edited\n")


def add_new_file(repos: Repos) -> None:
    write_file(repos.local, "new_analysis.sql")


def start_merge_conflict(repos: Repos) -> None:
    """Leave the local repo mid-merge with ``initial-0.txt`` in conflict."""
    for repo, content in ((repos.teammate, "theirs\n"), (repos.local, "ours\n")):
        write_file(repo, "initial-0.txt", content)
        git(repo, "add", "initial-0.txt")
        git(repo, "commit", "-m", "conflicting edit")
    git(repos.teammate, "push")
    git(repos.local, "fetch")
    merge = subprocess.run(
        ["git", "merge", "origin/main"],
        cwd=repos.local,
        capture_output=True,
        text=True,
    )
    assert merge.returncode != 0, "the merge was expected to conflict"


def init_repo_without_commits(root: Path) -> Path:
    """Create a repo with a remote and an untracked file but no commits."""
    remote = root / "remote.git"
    local = root / "local"
    remote.mkdir()
    local.mkdir()
    git(remote, "init", "--bare", "-b", "main")
    git(local, "init", "-b", "main")
    git(local, "remote", "add", "origin", str(remote))
    write_file(local, "analysis.sql")
    return local


def repo_snapshot(repo: Path) -> dict[str, str]:
    """Capture everything a well-behaved read-only command must leave alone."""
    return {
        "refs": git(repo, "for-each-ref"),
        "head": git(repo, "symbolic-ref", "HEAD"),
        "status": git(repo, "status", "--porcelain"),
        "staged": git(repo, "diff", "--cached"),
        "unstaged": git(repo, "diff"),
        "stash": git(repo, "stash", "list"),
        "config": git(repo, "config", "--local", "--list"),
    }
