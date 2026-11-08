"""Expected advice from ``plan_save``."""

import pytest

from gitrdone.advice import plan_save
from gitrdone.repo_state import ChangedFiles
from plan_states import (
    ABORT_MERGE,
    ADD,
    CLEAN,
    CLONE,
    COMMIT,
    CONFLICT,
    INIT,
    OUTSIDE,
    SYNCED,
    commands_of,
    notices_of,
    suggestions_of,
    text_of,
)

PLANS = [
    pytest.param(
        ChangedFiles(unstaged=("a.sql",)), ["git add a.sql", COMMIT], id="edited"
    ),
    pytest.param(
        ChangedFiles(untracked=("a.sql",)), ["git add a.sql", COMMIT], id="new_file"
    ),
    pytest.param(
        ChangedFiles(unstaged=("a.sql",), untracked=("b.sql",)),
        ["git add a.sql b.sql", COMMIT],
        id="edited_and_new",
    ),
    pytest.param(ChangedFiles(staged=("a.sql",)), [COMMIT], id="already_staged"),
    pytest.param(
        ChangedFiles(staged=("a.sql",), unstaged=("b.sql",)),
        ["git add b.sql", COMMIT],
        id="partly_staged",
    ),
    pytest.param(
        ChangedFiles(staged=("a.sql",), unstaged=("a.sql",)),
        ["git add a.sql", COMMIT],
        id="staged_then_edited_again",
    ),
    pytest.param(
        ChangedFiles(untracked=("my report.sql",)),
        ['git add "my report.sql"', COMMIT],
        id="name_with_spaces",
    ),
    pytest.param(CLEAN, [], id="nothing_to_commit"),
    pytest.param(CONFLICT, [ADD, COMMIT, ABORT_MERGE], id="merge_conflict"),
]


@pytest.mark.parametrize(("files", "expected"), PLANS)
def test_suggests_these_commands_in_this_order(
    files: ChangedFiles, expected: list[str]
) -> None:
    assert commands_of(plan_save(SYNCED, files)) == expected


@pytest.mark.parametrize(("files", "expected"), PLANS)
def test_every_suggestion_explains_itself_in_words(
    files: ChangedFiles, expected: list[str]
) -> None:
    for suggestion in suggestions_of(plan_save(SYNCED, files)):
        assert len(suggestion.reason.split()) >= 8, suggestion.command


def test_outside_a_repository_points_to_creating_one() -> None:
    assert commands_of(plan_save(OUTSIDE, CLEAN)) == [INIT, CLONE]


def test_nothing_to_commit_says_so() -> None:
    assert "nothing to commit" in text_of(notices_of(plan_save(SYNCED, CLEAN))).lower()


@pytest.mark.parametrize("name", ["staged.sql", "edited.sql", "new.sql"])
def test_lists_every_changed_file(name: str) -> None:
    files = ChangedFiles(
        staged=("staged.sql",), unstaged=("edited.sql",), untracked=("new.sql",)
    )

    assert name in text_of(notices_of(plan_save(SYNCED, files)))


def test_explains_the_difference_between_staging_and_committing() -> None:
    add, commit = suggestions_of(plan_save(SYNCED, ChangedFiles(unstaged=("a.sql",))))

    assert "stag" in add.reason.lower()
    assert "snapshot" in commit.reason.lower()


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        "config/.env",
        "credentials.json",
        "id_rsa",
        "server.pem",
        "api.key",
        ".ipynb_checkpoints/report-checkpoint.ipynb",
        "notebooks/.ipynb_checkpoints/report-checkpoint.ipynb",
    ],
)
def test_risky_files_are_left_out_of_git_add_and_warned_about(path: str) -> None:
    steps = plan_save(SYNCED, ChangedFiles(untracked=(path, "analysis.sql")))

    assert commands_of(steps) == ["git add analysis.sql", COMMIT]
    assert any(
        path in notice.text and notice.level == "attention"
        for notice in notices_of(steps)
    )


@pytest.mark.parametrize(
    "path", ["analysis.sql", "report.ipynb", "keys.py", "environment.yml", "data.csv"]
)
def test_ordinary_files_are_not_flagged(path: str) -> None:
    steps = plan_save(SYNCED, ChangedFiles(untracked=(path,)))

    assert commands_of(steps) == [f"git add {path}", COMMIT]
    assert all(notice.level != "attention" for notice in notices_of(steps))


def test_large_files_are_left_out_of_git_add_and_warned_about() -> None:
    steps = plan_save(
        SYNCED, ChangedFiles(untracked=("huge.csv", "a.sql"), large=("huge.csv",))
    )

    assert commands_of(steps) == ["git add a.sql", COMMIT]
    assert any(
        "huge.csv" in notice.text and notice.level == "attention"
        for notice in notices_of(steps)
    )


def test_only_risky_files_means_nothing_to_add_or_commit() -> None:
    steps = plan_save(SYNCED, ChangedFiles(untracked=(".env",)))

    assert commands_of(steps) == []
    assert any(notice.level == "attention" for notice in notices_of(steps))


def test_staged_risky_file_is_unstaged_before_committing() -> None:
    steps = plan_save(SYNCED, ChangedFiles(staged=(".env", "a.sql")))

    assert commands_of(steps) == ["git restore --staged .env", COMMIT]
    assert any(".env" in notice.text for notice in notices_of(steps))


def test_only_a_staged_risky_file_has_nothing_left_to_commit() -> None:
    steps = plan_save(SYNCED, ChangedFiles(staged=(".env",)))

    assert commands_of(steps) == ["git restore --staged .env"]
