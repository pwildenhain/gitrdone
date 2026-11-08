"""Expected explanations from ``explain_command``."""

import pytest

from gitrdone.advice import explain_command
from plan_states import commands_of, notices_of, suggestions_of, text_of

BASIC_COMMANDS = [
    "init",
    "clone",
    "config",
    "status",
    "add",
    "commit",
    "fetch",
    "pull",
    "push",
    "remote",
    "branch",
    "switch",
    "merge",
    "restore",
    "revert",
    "log",
    "diff",
]

OUT_OF_SCOPE = ["rebase", "cherry-pick", "submodule", "bisect", "not-a-command"]


@pytest.mark.parametrize("name", BASIC_COMMANDS)
def test_describes_the_command_and_when_to_use_it(name: str) -> None:
    notices = notices_of(explain_command(name))

    assert notices
    assert len(text_of(notices).split()) >= 8


@pytest.mark.parametrize("name", BASIC_COMMANDS)
def test_gives_a_typical_example_with_a_reason(name: str) -> None:
    examples = suggestions_of(explain_command(name))

    assert examples
    assert examples[0].command.startswith(f"git {name}")
    assert len(examples[0].reason.split()) >= 8


@pytest.mark.parametrize("name", BASIC_COMMANDS)
def test_accepts_the_leading_git(name: str) -> None:
    assert explain_command(f"git {name}") == explain_command(name)


def test_ignores_surrounding_whitespace() -> None:
    assert explain_command("  commit ") == explain_command("commit")


@pytest.mark.parametrize("name", OUT_OF_SCOPE)
def test_outside_the_basics_says_so_and_points_to_the_docs(name: str) -> None:
    steps = explain_command(name)

    assert commands_of(steps) == []
    assert "out of scope" in text_of(steps).lower()
    assert "git-scm.com/docs" in text_of(steps)


def test_out_of_scope_accepts_the_leading_git() -> None:
    assert explain_command("git rebase") == explain_command("rebase")
