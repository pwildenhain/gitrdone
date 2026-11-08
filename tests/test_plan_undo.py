"""Expected advice from ``plan_undo``: safest options first."""

import pytest

from gitrdone.advice import plan_undo
from gitrdone.repo_state import ChangedFiles, RepoState
from plan_states import (
    ABORT_MERGE,
    AHEAD,
    CLEAN,
    CONFLICT,
    NO_COMMITS,
    NO_REMOTE,
    NO_UPSTREAM,
    OUTSIDE,
    SYNCED,
    commands_of,
    notices_of,
    staged,
    suggestions_of,
    text_of,
    unstaged,
)

AMEND = "git commit --amend"
REVERT = "git revert HEAD"

PLANS = [
    pytest.param(SYNCED, CLEAN, [REVERT], id="pushed_commit"),
    pytest.param(AHEAD, CLEAN, [AMEND], id="unpushed_commit"),
    pytest.param(NO_UPSTREAM, CLEAN, [AMEND], id="branch_not_shared"),
    pytest.param(NO_REMOTE, CLEAN, [AMEND], id="no_remote"),
    pytest.param(
        staged(SYNCED),
        ChangedFiles(staged=("a.sql",)),
        ["git restore --staged a.sql", REVERT],
        id="staged_file",
    ),
    pytest.param(
        unstaged(SYNCED),
        ChangedFiles(unstaged=("a.sql",)),
        [REVERT, "git restore a.sql"],
        id="discarding_edits_comes_last",
    ),
    pytest.param(
        staged(unstaged(AHEAD)),
        ChangedFiles(staged=("a.sql",), unstaged=("b.sql",)),
        ["git restore --staged a.sql", AMEND, "git restore b.sql"],
        id="safest_options_first",
    ),
    pytest.param(
        unstaged(SYNCED),
        ChangedFiles(unstaged=("a.sql", "b.sql")),
        [REVERT, "git restore a.sql b.sql"],
        id="several_files",
    ),
    pytest.param(
        staged(SYNCED),
        ChangedFiles(staged=("my report.sql",)),
        ['git restore --staged "my report.sql"', REVERT],
        id="name_with_spaces",
    ),
    pytest.param(
        unstaged(SYNCED),
        ChangedFiles(untracked=("a.sql",)),
        [REVERT],
        id="untracked_files_are_left_alone",
    ),
    pytest.param(NO_COMMITS, CLEAN, [], id="nothing_to_undo"),
    pytest.param(
        staged(NO_COMMITS),
        ChangedFiles(staged=("a.sql",)),
        ["git rm --cached a.sql"],
        id="restore_needs_a_commit_so_unstage_differently",
    ),
    pytest.param(
        unstaged(NO_COMMITS),
        ChangedFiles(untracked=("a.sql",)),
        [],
        id="only_untracked_files_without_commits",
    ),
    pytest.param(
        staged(unstaged(SYNCED)), CONFLICT, [ABORT_MERGE], id="merge_conflict"
    ),
    pytest.param(OUTSIDE, CLEAN, [], id="outside_a_repo"),
]


@pytest.mark.parametrize(("state", "files", "expected"), PLANS)
def test_suggests_these_commands_in_this_order(
    state: RepoState, files: ChangedFiles, expected: list[str]
) -> None:
    assert commands_of(plan_undo(state, files)) == expected


@pytest.mark.parametrize(("state", "files", "expected"), PLANS)
def test_every_suggestion_explains_itself_in_words(
    state: RepoState, files: ChangedFiles, expected: list[str]
) -> None:
    for suggestion in suggestions_of(plan_undo(state, files)):
        assert len(suggestion.reason.split()) >= 8, suggestion.command


def test_discarding_edits_warns_that_it_is_permanent() -> None:
    steps = suggestions_of(plan_undo(unstaged(SYNCED), ChangedFiles(unstaged=("a.sql",))))
    discard = next(item for item in steps if item.command == "git restore a.sql")

    assert discard.warning is not None
    assert "permanent" in discard.warning.lower()


@pytest.mark.parametrize(
    ("state", "files"),
    [
        pytest.param(staged(SYNCED), ChangedFiles(staged=("a.sql",)), id="revert"),
        pytest.param(staged(AHEAD), ChangedFiles(staged=("a.sql",)), id="amend"),
    ],
)
def test_options_that_keep_work_carry_no_warning(
    state: RepoState, files: ChangedFiles
) -> None:
    assert all(item.warning is None for item in suggestions_of(plan_undo(state, files)))


def test_aborting_a_merge_carries_a_warning() -> None:
    abort = suggestions_of(plan_undo(staged(unstaged(SYNCED)), CONFLICT))[0]

    assert abort.warning is not None


def test_outside_a_repository_says_so() -> None:
    assert "repository" in text_of(notices_of(plan_undo(OUTSIDE, CLEAN)))


def test_nothing_to_undo_says_so() -> None:
    assert "nothing to undo" in text_of(notices_of(plan_undo(NO_COMMITS, CLEAN))).lower()
