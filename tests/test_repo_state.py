"""``read_repo_state`` against real git repositories."""

from dataclasses import replace
from pathlib import Path

import pytest

from git_sandbox import (
    Repos,
    add_new_file,
    commit,
    edit_without_staging,
    git,
    init_repo_without_commits,
    repo_snapshot,
    stage_a_change,
    teammate_pushes,
    teammate_pushes_and_local_fetches,
    write_file,
)
from gitrdone.repo_state import RepoState, read_repo_state

SYNCED = RepoState(
    is_repository=True,
    has_commits=True,
    branch="main",
    remote="origin",
    has_upstream=True,
)


def test_outside_a_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert read_repo_state() == RepoState(is_repository=False)


def test_repository_without_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(init_repo_without_commits(tmp_path))

    assert read_repo_state() == RepoState(
        is_repository=True,
        branch="main",
        remote="origin",
        has_unstaged_changes=True,
    )


def test_no_remote(repos: Repos) -> None:
    git(repos.local, "remote", "remove", "origin")

    assert read_repo_state() == replace(SYNCED, remote=None, has_upstream=False)


def test_remote_with_another_name(repos: Repos) -> None:
    git(repos.local, "remote", "rename", "origin", "team")

    assert read_repo_state() == replace(SYNCED, remote="team")


def test_origin_is_preferred_among_several_remotes(repos: Repos) -> None:
    git(repos.local, "remote", "add", "archive", "../elsewhere.git")

    assert read_repo_state() == SYNCED


def test_no_upstream(repos: Repos) -> None:
    git(repos.local, "switch", "-c", "analysis")

    assert read_repo_state() == replace(
        SYNCED, branch="analysis", has_upstream=False
    )


def test_detached_head(repos: Repos) -> None:
    git(repos.local, "switch", "--detach")

    assert read_repo_state() == replace(SYNCED, branch=None, has_upstream=False)


def test_up_to_date(repos: Repos) -> None:
    assert read_repo_state() == SYNCED


def test_ahead(repos: Repos) -> None:
    commit(repos.local, "local")

    assert read_repo_state() == replace(SYNCED, ahead=1)


def test_behind(repos: Repos) -> None:
    teammate_pushes_and_local_fetches(repos)

    assert read_repo_state() == replace(SYNCED, behind=1)


def test_diverged(repos: Repos) -> None:
    commit(repos.local, "local")
    teammate_pushes_and_local_fetches(repos, count=2)

    assert read_repo_state() == replace(SYNCED, ahead=1, behind=2)


def test_staged_change(repos: Repos) -> None:
    stage_a_change(repos)

    assert read_repo_state() == replace(SYNCED, has_staged_changes=True)


def test_unstaged_change(repos: Repos) -> None:
    edit_without_staging(repos)

    assert read_repo_state() == replace(SYNCED, has_unstaged_changes=True)


def test_untracked_file_counts_as_unstaged(repos: Repos) -> None:
    add_new_file(repos)

    assert read_repo_state() == replace(SYNCED, has_unstaged_changes=True)


def test_staged_and_unstaged_changes_together(repos: Repos) -> None:
    stage_a_change(repos)
    add_new_file(repos)

    assert read_repo_state() == replace(
        SYNCED, has_staged_changes=True, has_unstaged_changes=True
    )


def test_ignored_files_are_not_uncommitted_changes(repos: Repos) -> None:
    write_file(repos.local, ".gitignore", "*.csv\n")
    commit(repos.local, "ignore-rules")
    write_file(repos.local, "extract.csv")

    assert read_repo_state() == replace(SYNCED, ahead=1)


def test_unfetched_remote_work_is_not_seen(repos: Repos) -> None:
    teammate_pushes(repos)

    assert read_repo_state() == SYNCED


def test_works_when_the_remote_cannot_be_reached(repos: Repos) -> None:
    commit(repos.local, "local")
    git(repos.local, "remote", "set-url", "origin", "../gone.git")

    assert read_repo_state() == replace(SYNCED, ahead=1)


def test_does_not_change_the_repository(repos: Repos) -> None:
    teammate_pushes(repos)
    stage_a_change(repos)
    add_new_file(repos)
    local_before = repo_snapshot(repos.local)
    remote_refs_before = git(repos.remote, "for-each-ref")

    read_repo_state()

    assert repo_snapshot(repos.local) == local_before
    assert git(repos.remote, "for-each-ref") == remote_refs_before


def test_does_not_create_a_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    read_repo_state()

    assert list(tmp_path.iterdir()) == []
