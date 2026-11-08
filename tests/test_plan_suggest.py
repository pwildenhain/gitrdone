"""Expected advice from ``plan_suggest``: one situation at a time, by priority."""

import pytest

from gitrdone.advice import plan_suggest
from gitrdone.repo_state import ChangedFiles, RepoState
from plan_states import (
    ABORT_MERGE,
    ADD,
    ADD_REMOTE,
    AHEAD,
    BEHIND,
    CLEAN,
    CLONE,
    COMMIT,
    CONFLICT,
    DETACHED,
    DIVERGED,
    INIT,
    MERGE_PULL,
    NO_COMMITS,
    NO_REMOTE,
    NO_UPSTREAM,
    OUTSIDE,
    PULL,
    PUSH,
    SWITCH,
    SYNCED,
    commands_of,
    notices_of,
    staged,
    suggestions_of,
    text_of,
    unstaged,
)

EDITED = ChangedFiles(unstaged=("report.sql",))
STAGED = ChangedFiles(staged=("report.sql",))

PLANS = [
    pytest.param(OUTSIDE, CLEAN, [INIT, CLONE], id="outside_a_repo"),
    pytest.param(
        staged(unstaged(DIVERGED)),
        CONFLICT,
        [ADD, COMMIT, ABORT_MERGE],
        id="merge_conflict_comes_first",
    ),
    pytest.param(DETACHED, CLEAN, [SWITCH], id="detached"),
    pytest.param(unstaged(SYNCED), EDITED, [ADD, COMMIT], id="unstaged_changes"),
    pytest.param(staged(SYNCED), STAGED, [COMMIT], id="only_staged_changes"),
    pytest.param(
        unstaged(BEHIND), EDITED, [ADD, COMMIT], id="uncommitted_comes_before_pull"
    ),
    pytest.param(
        unstaged(AHEAD), EDITED, [ADD, COMMIT], id="uncommitted_comes_before_push"
    ),
    pytest.param(NO_COMMITS, CLEAN, [ADD, COMMIT], id="no_commits"),
    pytest.param(NO_REMOTE, CLEAN, [ADD_REMOTE], id="no_remote"),
    pytest.param(
        NO_UPSTREAM, CLEAN, ["git push -u origin analysis"], id="no_upstream"
    ),
    pytest.param(BEHIND, CLEAN, [PULL], id="behind"),
    pytest.param(DIVERGED, CLEAN, [MERGE_PULL], id="pull_comes_before_push"),
    pytest.param(AHEAD, CLEAN, [PUSH], id="ahead"),
    pytest.param(SYNCED, CLEAN, [], id="nothing_to_do"),
]


@pytest.mark.parametrize(("state", "files", "expected"), PLANS)
def test_suggests_these_commands_in_this_order(
    state: RepoState, files: ChangedFiles, expected: list[str]
) -> None:
    assert commands_of(plan_suggest(state, files)) == expected


@pytest.mark.parametrize(("state", "files", "expected"), PLANS)
def test_every_suggestion_explains_itself_in_words(
    state: RepoState, files: ChangedFiles, expected: list[str]
) -> None:
    for suggestion in suggestions_of(plan_suggest(state, files)):
        assert len(suggestion.reason.split()) >= 8, suggestion.command


def test_nothing_to_do_confirms_everything_is_up_to_date() -> None:
    assert "up to date" in text_of(notices_of(plan_suggest(SYNCED, CLEAN)))


def test_merge_conflict_names_the_conflicted_files() -> None:
    assert "report.sql" in text_of(plan_suggest(staged(unstaged(SYNCED)), CONFLICT))


def test_aborting_a_merge_carries_a_warning() -> None:
    abort = next(
        item
        for item in suggestions_of(plan_suggest(staged(unstaged(SYNCED)), CONFLICT))
        if item.command == ABORT_MERGE
    )

    assert abort.warning is not None
