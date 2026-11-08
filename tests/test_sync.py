"""End-to-end checks of ``gitrdone sync`` through the CLI.

Which advice fits which state is covered in ``test_advice.py``, and reading the
state is covered in ``test_repo_state.py``. These tests confirm the pieces are
connected.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from git_sandbox import (
    Repos,
    add_new_file,
    commit,
    git,
    repo_snapshot,
    stage_a_change,
    teammate_pushes_and_local_fetches,
)
from gitrdone.cli import GitRdoneCLI


def run_sync() -> str:
    """Invoke ``gitrdone sync`` in the current directory and return its output.

    The app is built per invocation so that a console created along with it
    picks up the environment set by the test.
    """
    result = CliRunner().invoke(GitRdoneCLI().app, ["sync"])
    assert result.exit_code == 0, f"sync did not succeed: {result.exception!r}"
    return result.output


def test_diverged_repository_gets_pull_then_push(repos: Repos) -> None:
    commit(repos.local, "local")
    teammate_pushes_and_local_fetches(repos)

    output = run_sync()

    assert output.index("git pull --no-rebase") < output.index("git push")


def test_outside_a_repository_succeeds_and_creates_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert "git init" in run_sync()
    assert list(tmp_path.iterdir()) == []


def test_never_changes_the_repository(repos: Repos) -> None:
    teammate_pushes_and_local_fetches(repos)
    stage_a_change(repos)
    add_new_file(repos)
    local_before = repo_snapshot(repos.local)
    remote_refs_before = git(repos.remote, "for-each-ref")

    run_sync()

    assert repo_snapshot(repos.local) == local_before
    assert git(repos.remote, "for-each-ref") == remote_refs_before


def test_output_is_color_coded(
    repos: Repos, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")

    assert "\x1b[" in run_sync()
