"""End-to-end checks of the remaining commands through the CLI.

Which advice fits which state is covered by the planner tests, and reading the
state by the reader tests. These tests confirm the pieces are connected.
"""

from collections.abc import Callable
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

REPO_COMMANDS = ["suggest", "status", "setup", "save", "branch", "undo"]


def run(*args: str) -> str:
    """Invoke gitrdone in the current directory and return its output."""
    result = CliRunner().invoke(GitRdoneCLI().app, list(args))
    assert result.exit_code == 0, f"{args} did not succeed: {result.exception!r}"
    return result.output


def _ahead(repos: Repos) -> None:
    commit(repos.local, "local")


def _untracked(repos: Repos) -> None:
    add_new_file(repos)


def _staged(repos: Repos) -> None:
    stage_a_change(repos)


def _no_change(repos: Repos) -> None:
    pass


CONNECTED = [
    pytest.param("suggest", _ahead, "git push", id="suggest"),
    pytest.param("status", _untracked, "new_analysis.sql", id="status"),
    pytest.param("setup", _no_change, "git config --global user.name", id="setup"),
    pytest.param("save", _untracked, "git add new_analysis.sql", id="save"),
    pytest.param("branch", _no_change, "git switch -c", id="branch"),
    pytest.param("undo", _staged, "git restore --staged initial-0.txt", id="undo"),
]


@pytest.mark.parametrize(("command", "arrange", "expected"), CONNECTED)
def test_command_reads_the_repo_and_prints_its_advice(
    repos: Repos, command: str, arrange: Callable[[Repos], None], expected: str
) -> None:
    arrange(repos)

    assert expected in run(command)


def test_explain_prints_its_explanation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert "git commit" in run("explain", "commit")


@pytest.mark.parametrize("command", REPO_COMMANDS)
def test_outside_a_repository_succeeds_and_creates_nothing(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    run(command)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("command", REPO_COMMANDS)
def test_never_changes_the_repository(repos: Repos, command: str) -> None:
    teammate_pushes_and_local_fetches(repos)
    stage_a_change(repos)
    add_new_file(repos)
    local_before = repo_snapshot(repos.local)
    remote_refs_before = git(repos.remote, "for-each-ref")

    run(command)

    assert repo_snapshot(repos.local) == local_before
    assert git(repos.remote, "for-each-ref") == remote_refs_before


@pytest.mark.parametrize("command", REPO_COMMANDS)
def test_output_is_color_coded(
    repos: Repos, command: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")

    assert "\x1b[" in run(command)


def test_explain_output_is_color_coded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FORCE_COLOR", "1")

    assert "\x1b[" in run("explain", "commit")
