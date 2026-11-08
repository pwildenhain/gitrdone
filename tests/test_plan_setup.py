"""Expected advice from ``plan_setup``: only the steps still missing."""

import pytest

from gitrdone.advice import plan_setup
from gitrdone.repo_state import ChangedFiles, RepoState, SetupState
from plan_states import (
    ADD_REMOTE,
    CLEAN,
    CLONE,
    INIT,
    NO_REMOTE,
    OUTSIDE,
    SYNCED,
    commands_of,
    notices_of,
    suggestions_of,
    text_of,
)

SET_NAME = 'git config --global user.name "Your Name"'
SET_EMAIL = 'git config --global user.email "you@example.com"'

COMPLETE = SetupState(has_user_name=True, has_user_email=True, has_gitignore=True)
NOTHING_DONE = SetupState()
NO_NAME = SetupState(has_user_email=True, has_gitignore=True)
NO_EMAIL = SetupState(has_user_name=True, has_gitignore=True)
NO_GITIGNORE = SetupState(has_user_name=True, has_user_email=True)

PLANS = [
    pytest.param(OUTSIDE, NO_GITIGNORE, [INIT, CLONE], id="outside_a_repo"),
    pytest.param(
        OUTSIDE,
        NOTHING_DONE,
        [INIT, CLONE, SET_NAME, SET_EMAIL],
        id="outside_a_repo_without_identity",
    ),
    pytest.param(SYNCED, COMPLETE, [], id="fully_set_up"),
    pytest.param(SYNCED, NO_NAME, [SET_NAME], id="missing_name"),
    pytest.param(SYNCED, NO_EMAIL, [SET_EMAIL], id="missing_email"),
    pytest.param(SYNCED, NOTHING_DONE, [SET_NAME, SET_EMAIL], id="missing_identity"),
    pytest.param(NO_REMOTE, COMPLETE, [ADD_REMOTE], id="missing_remote"),
    pytest.param(
        NO_REMOTE,
        NOTHING_DONE,
        [SET_NAME, SET_EMAIL, ADD_REMOTE],
        id="missing_identity_and_remote",
    ),
]


@pytest.mark.parametrize(("state", "setup", "expected"), PLANS)
def test_suggests_only_the_missing_steps(
    state: RepoState, setup: SetupState, expected: list[str]
) -> None:
    assert commands_of(plan_setup(state, setup, CLEAN)) == expected


@pytest.mark.parametrize(("state", "setup", "expected"), PLANS)
def test_every_suggestion_explains_itself_in_words(
    state: RepoState, setup: SetupState, expected: list[str]
) -> None:
    for suggestion in suggestions_of(plan_setup(state, setup, CLEAN)):
        assert len(suggestion.reason.split()) >= 8, suggestion.command


def test_fully_set_up_says_so() -> None:
    assert "set up" in text_of(notices_of(plan_setup(SYNCED, COMPLETE, CLEAN)))


def test_missing_gitignore_needs_attention() -> None:
    notices = notices_of(plan_setup(SYNCED, NO_GITIGNORE, CLEAN))

    assert any(
        ".gitignore" in notice.text and notice.level == "attention"
        for notice in notices
    )


def test_existing_gitignore_is_not_mentioned() -> None:
    assert ".gitignore" not in text_of(plan_setup(SYNCED, COMPLETE, CLEAN))


def test_gitignore_is_not_raised_until_there_is_a_repository() -> None:
    assert ".gitignore" not in text_of(plan_setup(OUTSIDE, NO_GITIGNORE, CLEAN))


@pytest.mark.parametrize(
    "files",
    [
        pytest.param(ChangedFiles(untracked=(".env",)), id="credentials"),
        pytest.param(
            ChangedFiles(untracked=(".ipynb_checkpoints/a-checkpoint.ipynb",)),
            id="notebook_checkpoint",
        ),
        pytest.param(
            ChangedFiles(untracked=("huge.csv",), large=("huge.csv",)), id="large_file"
        ),
    ],
)
def test_warns_about_files_to_keep_out_of_version_control(files: ChangedFiles) -> None:
    notices = notices_of(plan_setup(SYNCED, COMPLETE, files))

    assert any(
        files.untracked[0] in notice.text and notice.level == "attention"
        for notice in notices
    )


def test_ordinary_files_get_no_warning() -> None:
    files = ChangedFiles(untracked=("analysis.sql",))

    assert all(
        notice.level != "attention"
        for notice in notices_of(plan_setup(SYNCED, COMPLETE, files))
    )
