"""Fixtures shared across the gitrdone test suite."""

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from git_sandbox import Repos, commit, git


@pytest.fixture(scope="session", autouse=True)
def isolated_git(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Keep the user's git config and terminal settings out of the tests."""
    empty_config = tmp_path_factory.mktemp("git-config") / "empty.gitconfig"
    empty_config.touch()
    with pytest.MonkeyPatch.context() as env:
        env.setenv("GIT_CONFIG_GLOBAL", str(empty_config))
        env.setenv("GIT_CONFIG_NOSYSTEM", "1")
        env.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path_factory.getbasetemp()))
        env.setenv("GIT_AUTHOR_NAME", "Test Analyst")
        env.setenv("GIT_AUTHOR_EMAIL", "analyst@example.com")
        env.setenv("GIT_COMMITTER_NAME", "Test Analyst")
        env.setenv("GIT_COMMITTER_EMAIL", "analyst@example.com")
        env.delenv("GIT_DIR", raising=False)
        env.delenv("GIT_WORK_TREE", raising=False)
        # A wide console keeps rich from wrapping a command across two lines.
        env.setenv("COLUMNS", "200")
        env.delenv("FORCE_COLOR", raising=False)
        env.delenv("NO_COLOR", raising=False)
        yield


@pytest.fixture(scope="session")
def repos_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the remote and both clones once, for every test to copy."""
    root = tmp_path_factory.mktemp("repos-template")
    remote = root / "remote.git"
    local = root / "local"
    teammate = root / "teammate"
    remote.mkdir()
    local.mkdir()
    git(remote, "init", "--bare", "-b", "main")
    git(local, "init", "-b", "main")
    commit(local, "initial")
    git(local, "remote", "add", "origin", str(remote))
    git(local, "push", "-u", "origin", "main")
    git(root, "clone", str(remote), str(teammate))
    # Relative URLs make each copy talk to its own remote, not the template's.
    git(local, "remote", "set-url", "origin", "../remote.git")
    git(teammate, "remote", "set-url", "origin", "../remote.git")
    return root


@pytest.fixture
def repos(
    repos_template: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Repos:
    """A private copy of a local repo on ``main`` that matches its remote."""
    shutil.copytree(repos_template, tmp_path, dirs_exist_ok=True)
    monkeypatch.chdir(tmp_path / "local")
    return Repos(
        local=tmp_path / "local",
        remote=tmp_path / "remote.git",
        teammate=tmp_path / "teammate",
    )
