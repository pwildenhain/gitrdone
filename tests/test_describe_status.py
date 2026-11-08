"""Expected plain-language report from ``describe_status``."""

import re

import pytest

from gitrdone.advice import describe_status
from gitrdone.repo_state import ChangedFiles, RepoState
from plan_states import (
    AHEAD,
    BEHIND,
    CLEAN,
    CONFLICT,
    DETACHED,
    DIVERGED,
    NO_COMMITS,
    NO_REMOTE,
    NO_UPSTREAM,
    OUTSIDE,
    SYNCED,
    staged,
    text_of,
    unstaged,
)

GIT_COMMAND = (
    r"\bgit (init|clone|config|status|add|commit|fetch|pull|push|remote|branch"
    r"|switch|merge|restore|revert|log|diff)\b"
)

ALL_KINDS_OF_CHANGE = ChangedFiles(
    staged=("staged.sql",), unstaged=("edited.sql",), untracked=("new.sql",)
)

SITUATIONS = [
    pytest.param(OUTSIDE, CLEAN, id="outside_a_repo"),
    pytest.param(SYNCED, CLEAN, id="clean"),
    pytest.param(staged(unstaged(SYNCED)), ALL_KINDS_OF_CHANGE, id="changes"),
    pytest.param(staged(unstaged(SYNCED)), CONFLICT, id="merge_conflict"),
    pytest.param(DETACHED, CLEAN, id="detached"),
    pytest.param(NO_COMMITS, CLEAN, id="no_commits"),
    pytest.param(NO_REMOTE, CLEAN, id="no_remote"),
    pytest.param(NO_UPSTREAM, CLEAN, id="no_upstream"),
    pytest.param(AHEAD, CLEAN, id="ahead"),
    pytest.param(BEHIND, CLEAN, id="behind"),
    pytest.param(DIVERGED, CLEAN, id="diverged"),
]


@pytest.mark.parametrize(("state", "files"), SITUATIONS)
def test_reports_without_recommending_commands(
    state: RepoState, files: ChangedFiles
) -> None:
    text = text_of(describe_status(state, files))

    assert not re.search(GIT_COMMAND, text)


@pytest.mark.parametrize(("state", "files"), SITUATIONS)
def test_avoids_git_jargon(state: RepoState, files: ChangedFiles) -> None:
    text = text_of(describe_status(state, files))

    assert not re.search(r"\b(HEAD|upstream|porcelain|detached)\b", text)


def test_outside_a_repository_says_so() -> None:
    notices = describe_status(OUTSIDE, CLEAN)

    assert "repository" in text_of(notices)
    assert {notice.level for notice in notices} == {"attention"}


def test_names_the_current_branch() -> None:
    assert "main" in text_of(describe_status(SYNCED, CLEAN))


def test_detached_head_says_there_is_no_current_branch() -> None:
    assert "not on a branch" in text_of(describe_status(DETACHED, CLEAN))


def test_clean_and_up_to_date_needs_no_attention() -> None:
    assert {notice.level for notice in describe_status(SYNCED, CLEAN)} == {"ok"}


@pytest.mark.parametrize("name", ["staged.sql", "edited.sql", "new.sql"])
def test_lists_every_changed_file(name: str) -> None:
    state = staged(unstaged(SYNCED))

    assert name in text_of(describe_status(state, ALL_KINDS_OF_CHANGE))


def test_defines_staging_where_it_appears() -> None:
    text = text_of(describe_status(staged(SYNCED), ChangedFiles(staged=("a.sql",))))

    assert re.search(r"ready to (save|commit|be saved|be committed)", text, re.I)


@pytest.mark.parametrize(
    ("state", "files"),
    [
        pytest.param(unstaged(SYNCED), ChangedFiles(unstaged=("a.sql",)), id="edited"),
        pytest.param(unstaged(SYNCED), ChangedFiles(untracked=("a.sql",)), id="new"),
        pytest.param(staged(unstaged(SYNCED)), CONFLICT, id="conflict"),
        pytest.param(BEHIND, CLEAN, id="behind"),
        pytest.param(DIVERGED, CLEAN, id="diverged"),
        pytest.param(AHEAD, CLEAN, id="ahead"),
        pytest.param(NO_REMOTE, CLEAN, id="no_remote"),
    ],
)
def test_flags_what_needs_attention(state: RepoState, files: ChangedFiles) -> None:
    levels = {notice.level for notice in describe_status(state, files)}

    assert "attention" in levels


def test_conflicted_files_are_named() -> None:
    assert "report.sql" in text_of(describe_status(staged(unstaged(SYNCED)), CONFLICT))


def test_reports_commits_not_yet_shared() -> None:
    assert "2 commits" in text_of(describe_status(AHEAD, CLEAN))


def test_reports_commits_not_yet_downloaded() -> None:
    assert "3 commits" in text_of(describe_status(BEHIND, CLEAN))


def test_reports_both_counts_when_diverged() -> None:
    text = text_of(describe_status(DIVERGED, CLEAN))

    assert "2 commits" in text
    assert "3 commits" in text
