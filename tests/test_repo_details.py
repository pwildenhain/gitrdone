"""The file, branch, and setup readers against real git repositories."""

from collections.abc import Callable
from pathlib import Path

import pytest

from git_sandbox import (
    Repos,
    add_new_file,
    commit,
    edit_without_staging,
    git,
    repo_snapshot,
    stage_a_change,
    start_merge_conflict,
    write_file,
)
from gitrdone.repo_state import (
    LARGE_FILE_BYTES,
    BranchState,
    ChangedFiles,
    SetupState,
    read_branch_state,
    read_changed_files,
    read_setup_state,
)

TRACKED = "initial-0.txt"
UNTRACKED = "new_analysis.sql"


def make_file_of_size(path: Path, size: int) -> None:
    with path.open("wb") as file:
        file.truncate(size)


# --- read_changed_files ------------------------------------------------------


def test_clean_repository_has_no_changed_files(repos: Repos) -> None:
    assert read_changed_files() == ChangedFiles()


def test_changed_files_outside_a_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert read_changed_files() == ChangedFiles()


def test_staged_file(repos: Repos) -> None:
    stage_a_change(repos)

    assert read_changed_files() == ChangedFiles(staged=(TRACKED,))


def test_unstaged_file(repos: Repos) -> None:
    edit_without_staging(repos)

    assert read_changed_files() == ChangedFiles(unstaged=(TRACKED,))


def test_untracked_file(repos: Repos) -> None:
    add_new_file(repos)

    assert read_changed_files() == ChangedFiles(untracked=(UNTRACKED,))


def test_file_staged_and_then_edited_again_is_in_both_lists(repos: Repos) -> None:
    stage_a_change(repos)
    write_file(repos.local, TRACKED, "edited again\n")

    assert read_changed_files() == ChangedFiles(staged=(TRACKED,), unstaged=(TRACKED,))


def test_files_inside_new_folders_are_listed_individually(repos: Repos) -> None:
    (repos.local / "queries").mkdir()
    write_file(repos.local / "queries", "a.sql")

    assert read_changed_files() == ChangedFiles(untracked=("queries/a.sql",))


def test_file_names_with_spaces_are_not_quoted(repos: Repos) -> None:
    write_file(repos.local, "my report.sql")

    assert read_changed_files() == ChangedFiles(untracked=("my report.sql",))


def test_renamed_file_is_listed_once_under_its_new_name(repos: Repos) -> None:
    git(repos.local, "mv", TRACKED, "renamed.txt")
    add_new_file(repos)

    assert read_changed_files() == ChangedFiles(
        staged=("renamed.txt",), untracked=(UNTRACKED,)
    )


def test_paths_are_relative_to_the_repo_root_from_a_subfolder(
    repos: Repos, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repos.local / "queries").mkdir()
    write_file(repos.local / "queries", "a.sql")
    monkeypatch.chdir(repos.local / "queries")

    assert read_changed_files() == ChangedFiles(untracked=("queries/a.sql",))


def test_merge_conflict_is_listed_separately(repos: Repos) -> None:
    start_merge_conflict(repos)

    assert read_changed_files() == ChangedFiles(conflicted=(TRACKED,))


def test_ignored_files_are_not_listed(repos: Repos) -> None:
    write_file(repos.local, ".gitignore", "*.csv\n")
    commit(repos.local, "ignore-rules")
    write_file(repos.local, "extract.csv")

    assert read_changed_files() == ChangedFiles()


def test_large_file_is_flagged(repos: Repos) -> None:
    make_file_of_size(repos.local / "huge.csv", LARGE_FILE_BYTES)

    assert read_changed_files() == ChangedFiles(
        untracked=("huge.csv",), large=("huge.csv",)
    )


def test_file_just_under_the_limit_is_not_flagged(repos: Repos) -> None:
    make_file_of_size(repos.local / "big.csv", LARGE_FILE_BYTES - 1)

    assert read_changed_files() == ChangedFiles(untracked=("big.csv",))


def test_large_file_is_found_from_a_subfolder(
    repos: Repos, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repos.local / "queries").mkdir()
    make_file_of_size(repos.local / "huge.csv", LARGE_FILE_BYTES)
    monkeypatch.chdir(repos.local / "queries")

    assert read_changed_files().large == ("huge.csv",)


# --- read_branch_state -------------------------------------------------------


def test_single_branch(repos: Repos) -> None:
    assert read_branch_state() == BranchState(
        current="main", local=("main",), default="main"
    )


def test_branch_state_outside_a_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert read_branch_state() == BranchState()


def test_several_branches(repos: Repos) -> None:
    git(repos.local, "switch", "-c", "analysis")

    assert read_branch_state() == BranchState(
        current="analysis", local=("analysis", "main"), default="main"
    )


def test_detached_head_is_not_listed_as_a_branch(repos: Repos) -> None:
    git(repos.local, "switch", "--detach")

    assert read_branch_state() == BranchState(
        current=None, local=("main",), default="main"
    )


def test_default_branch_comes_from_the_remote_when_known(repos: Repos) -> None:
    git(repos.local, "switch", "-c", "trunk")
    git(repos.local, "push", "-u", "origin", "trunk")
    git(repos.local, "remote", "set-head", "origin", "trunk")

    assert read_branch_state().default == "trunk"


def test_master_is_recognized_as_the_default_branch(repos: Repos) -> None:
    git(repos.local, "branch", "-m", "main", "master")

    assert read_branch_state().default == "master"


def test_default_branch_is_unknown_without_a_conventional_name(repos: Repos) -> None:
    git(repos.local, "branch", "-m", "main", "analysis")

    assert read_branch_state().default is None


# --- read_setup_state --------------------------------------------------------


def test_nothing_set_up(repos: Repos) -> None:
    assert read_setup_state() == SetupState()


def test_setup_outside_a_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert read_setup_state() == SetupState()


def test_identity_is_read_from_the_repository_config(repos: Repos) -> None:
    git(repos.local, "config", "user.name", "Test Analyst")
    git(repos.local, "config", "user.email", "analyst@example.com")

    assert read_setup_state() == SetupState(has_user_name=True, has_user_email=True)


def test_identity_is_read_from_global_config_outside_a_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "global.gitconfig"
    config.write_text("[user]\n\tname = Test Analyst\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    folder = tmp_path / "folder"
    folder.mkdir()
    monkeypatch.chdir(folder)

    assert read_setup_state() == SetupState(has_user_name=True)


def test_gitignore_is_found(repos: Repos) -> None:
    write_file(repos.local, ".gitignore", "*.csv\n")

    assert read_setup_state() == SetupState(has_gitignore=True)


def test_gitignore_is_found_from_a_subfolder(
    repos: Repos, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_file(repos.local, ".gitignore", "*.csv\n")
    (repos.local / "queries").mkdir()
    monkeypatch.chdir(repos.local / "queries")

    assert read_setup_state() == SetupState(has_gitignore=True)


# --- Read-only contract ------------------------------------------------------


READERS: dict[str, Callable[[], object]] = {
    "changed_files": read_changed_files,
    "branch_state": read_branch_state,
    "setup_state": read_setup_state,
}


@pytest.mark.parametrize("reader", READERS.values(), ids=READERS)
def test_readers_do_not_change_the_repository(
    repos: Repos, reader: Callable[[], object]
) -> None:
    stage_a_change(repos)
    add_new_file(repos)
    before = repo_snapshot(repos.local)

    reader()

    assert repo_snapshot(repos.local) == before
