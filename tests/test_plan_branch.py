"""Expected advice from ``plan_branch``."""

import pytest

from gitrdone.advice import plan_branch
from gitrdone.repo_state import BranchState, RepoState
from plan_states import (
    ABORT_MERGE,
    ADD,
    CLEAN,
    CLONE,
    COMMIT,
    CONFLICT,
    DETACHED,
    INIT,
    NO_COMMITS,
    NO_UPSTREAM,
    OUTSIDE,
    SYNCED,
    commands_of,
    notices_of,
    suggestions_of,
    text_of,
    unstaged,
)

NEW_BRANCH = "git switch -c <new-branch>"

ONLY_MAIN = BranchState(current="main", local=("main",), default="main")
ON_MAIN_WITH_OTHER = BranchState(
    current="main", local=("analysis", "main"), default="main"
)
ON_FEATURE = BranchState(current="analysis", local=("analysis", "main"), default="main")
ON_FEATURE_NO_DEFAULT = BranchState(
    current="analysis", local=("analysis", "draft"), default=None
)
DETACHED_BRANCHES = BranchState(current=None, local=("main",), default="main")

PLANS = [
    pytest.param(SYNCED, ONLY_MAIN, [NEW_BRANCH], id="on_default_branch"),
    pytest.param(
        SYNCED,
        ON_MAIN_WITH_OTHER,
        [NEW_BRANCH, "git switch analysis"],
        id="on_default_branch_with_others",
    ),
    pytest.param(
        NO_UPSTREAM,
        ON_FEATURE,
        ["git switch main", "git merge analysis"],
        id="on_feature_branch",
    ),
    pytest.param(
        NO_UPSTREAM,
        ON_FEATURE_NO_DEFAULT,
        ["git switch draft"],
        id="default_branch_unknown_has_no_merge",
    ),
    pytest.param(DETACHED, DETACHED_BRANCHES, ["git switch main"], id="detached"),
    pytest.param(NO_COMMITS, ONLY_MAIN, [ADD, COMMIT], id="no_commits_yet"),
    pytest.param(OUTSIDE, BranchState(), [INIT, CLONE], id="outside_a_repo"),
]


@pytest.mark.parametrize(("state", "branches", "expected"), PLANS)
def test_suggests_these_commands_in_this_order(
    state: RepoState, branches: BranchState, expected: list[str]
) -> None:
    assert commands_of(plan_branch(state, branches, CLEAN)) == expected


@pytest.mark.parametrize(("state", "branches", "expected"), PLANS)
def test_every_suggestion_explains_itself_in_words(
    state: RepoState, branches: BranchState, expected: list[str]
) -> None:
    for suggestion in suggestions_of(plan_branch(state, branches, CLEAN)):
        assert len(suggestion.reason.split()) >= 8, suggestion.command


def test_shows_the_current_branch_and_the_local_branches() -> None:
    text = text_of(notices_of(plan_branch(SYNCED, ON_MAIN_WITH_OTHER, CLEAN)))

    assert "main" in text
    assert "analysis" in text


def test_merge_conflict_comes_before_branch_advice() -> None:
    steps = plan_branch(unstaged(SYNCED), ON_FEATURE, CONFLICT)

    assert commands_of(steps) == [ADD, COMMIT, ABORT_MERGE]
    assert "report.sql" in text_of(steps)


def test_merge_conflict_explains_how_to_finish_or_abort() -> None:
    steps = suggestions_of(plan_branch(unstaged(SYNCED), ON_FEATURE, CONFLICT))
    abort = next(item for item in steps if item.command == ABORT_MERGE)

    assert abort.warning is not None
