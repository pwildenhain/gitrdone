"""Expected advice from ``plan_sync`` for each repository state.

These tests use hand-built states, so they involve no git and no terminal.
"""

from dataclasses import replace

import pytest

from gitrdone.advice import Suggestion, plan_sync
from gitrdone.repo_state import RepoState
from plan_states import (
    ADD,
    ADD_REMOTE,
    AHEAD,
    BEHIND,
    COMMIT,
    DETACHED,
    DIVERGED,
    FETCH,
    MERGE_PULL,
    NO_COMMITS,
    NO_REMOTE,
    NO_UPSTREAM,
    OUTSIDE,
    PULL,
    PUSH,
    SWITCH,
    SYNCED,
    staged,
    unstaged,
)


def commands(state: RepoState) -> list[str]:
    return [suggestion.command for suggestion in plan_sync(state)]


def suggestion_for(state: RepoState, command: str) -> Suggestion:
    return next(item for item in plan_sync(state) if item.command == command)


PLANS = [
    pytest.param(OUTSIDE, ["git init", "git clone <url>"], id="outside_a_repo"),
    pytest.param(DETACHED, [SWITCH], id="detached"),
    pytest.param(unstaged(DETACHED), [SWITCH], id="detached_with_changes"),
    pytest.param(NO_REMOTE, [ADD_REMOTE], id="no_remote"),
    pytest.param(
        unstaged(NO_REMOTE), [ADD, COMMIT, ADD_REMOTE], id="no_remote_with_changes"
    ),
    pytest.param(NO_COMMITS, [ADD, COMMIT], id="no_commits_and_no_files"),
    pytest.param(unstaged(NO_COMMITS), [ADD, COMMIT], id="no_commits_with_new_files"),
    pytest.param(staged(NO_COMMITS), [COMMIT], id="no_commits_with_staged_files"),
    pytest.param(
        NO_UPSTREAM, ["git push -u origin analysis"], id="no_upstream"
    ),
    pytest.param(
        replace(NO_UPSTREAM, remote="team"),
        ["git push -u team analysis"],
        id="no_upstream_uses_the_configured_remote",
    ),
    pytest.param(
        unstaged(NO_UPSTREAM),
        [ADD, COMMIT, "git push -u origin analysis"],
        id="no_upstream_with_changes",
    ),
    pytest.param(SYNCED, [FETCH], id="up_to_date"),
    pytest.param(AHEAD, [FETCH, PUSH], id="ahead"),
    pytest.param(BEHIND, [PULL], id="behind"),
    pytest.param(DIVERGED, [MERGE_PULL, PUSH], id="diverged"),
    pytest.param(staged(SYNCED), [COMMIT, FETCH, PUSH], id="up_to_date_staged"),
    pytest.param(
        unstaged(SYNCED), [ADD, COMMIT, FETCH, PUSH], id="up_to_date_unstaged"
    ),
    pytest.param(
        staged(unstaged(SYNCED)),
        [ADD, COMMIT, FETCH, PUSH],
        id="up_to_date_staged_and_unstaged",
    ),
    pytest.param(staged(AHEAD), [COMMIT, FETCH, PUSH], id="ahead_staged"),
    pytest.param(unstaged(AHEAD), [ADD, COMMIT, FETCH, PUSH], id="ahead_unstaged"),
    pytest.param(staged(BEHIND), [COMMIT, MERGE_PULL, PUSH], id="behind_staged"),
    pytest.param(
        unstaged(BEHIND), [ADD, COMMIT, MERGE_PULL, PUSH], id="behind_unstaged"
    ),
    pytest.param(
        unstaged(DIVERGED), [ADD, COMMIT, MERGE_PULL, PUSH], id="diverged_unstaged"
    ),
]


@pytest.mark.parametrize(("state", "expected"), PLANS)
def test_suggests_these_commands_in_this_order(
    state: RepoState, expected: list[str]
) -> None:
    assert commands(state) == expected


@pytest.mark.parametrize(("state", "expected"), PLANS)
def test_every_suggestion_explains_itself_in_words(
    state: RepoState, expected: list[str]
) -> None:
    for suggestion in plan_sync(state):
        assert len(suggestion.reason.split()) >= 8, suggestion.command


def test_up_to_date_says_so() -> None:
    assert "up to date" in suggestion_for(SYNCED, FETCH).reason


def test_ahead_reports_how_many_commits_will_be_pushed() -> None:
    assert "2 commits" in suggestion_for(AHEAD, PUSH).reason


def test_behind_reports_how_many_commits_will_be_pulled() -> None:
    assert "3 commits" in suggestion_for(BEHIND, PULL).reason


def test_diverged_reports_both_commit_counts() -> None:
    reason = suggestion_for(DIVERGED, MERGE_PULL).reason

    assert "3 commits" in reason
    assert "2 commits" in reason


def test_single_commit_is_not_pluralized() -> None:
    reason = suggestion_for(replace(SYNCED, ahead=1), PUSH).reason

    assert "1 commit " in reason


def test_unpublished_branch_is_named_in_the_reason() -> None:
    assert "analysis" in suggestion_for(NO_UPSTREAM, "git push -u origin analysis").reason
