"""Terminal output from ``print_suggestions``."""

import pytest

from gitrdone.advice import Notice, Suggestion
from gitrdone.display import print_suggestions

SUGGESTIONS = [
    Suggestion("git pull", "Downloads the work your teammates shared."),
    Suggestion("git push", "Uploads your own work."),
]


def test_prints_each_command_with_its_reason_in_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    print_suggestions(SUGGESTIONS)

    output = capsys.readouterr().out
    positions = [
        output.index(text)
        for text in (
            "1. git pull",
            "Downloads the work",
            "2. git push",
            "Uploads your own work",
        )
    ]
    assert positions == sorted(positions)


def test_output_is_color_coded(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")

    print_suggestions(SUGGESTIONS)

    assert "\x1b[" in capsys.readouterr().out


def test_long_commands_stay_on_one_line(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLUMNS", "30")
    command = "git push -u origin a-very-long-branch-name-for-an-analysis"

    print_suggestions([Suggestion(command, "Shares the branch.")])

    assert command in capsys.readouterr().out


def test_square_brackets_are_printed_literally(
    capsys: pytest.CaptureFixture[str],
) -> None:
    print_suggestions([Suggestion("git push -u origin [bold]x", "Shares the branch.")])

    assert "git push -u origin [bold]x" in capsys.readouterr().out


def test_prints_a_warning_after_the_reason(
    capsys: pytest.CaptureFixture[str],
) -> None:
    print_suggestions(
        [Suggestion("git restore a.sql", "Discards edits.", warning="This is permanent.")]
    )

    output = capsys.readouterr().out
    assert output.index("Discards edits.") < output.index("This is permanent.")


def test_prints_a_notice(capsys: pytest.CaptureFixture[str]) -> None:
    print_suggestions([Notice("Everything is up to date.", "ok")])

    assert "Everything is up to date." in capsys.readouterr().out


def test_notice_brackets_are_printed_literally(
    capsys: pytest.CaptureFixture[str],
) -> None:
    print_suggestions([Notice("data[bold]/a.sql")])

    assert "data[bold]/a.sql" in capsys.readouterr().out


def test_notices_are_not_numbered_and_do_not_affect_command_numbers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    print_suggestions(
        [
            Notice("Your changed files."),
            Suggestion("git push", "Uploads your own work."),
        ]
    )

    output = capsys.readouterr().out
    assert "1. git push" in output
    assert "1. Your changed files." not in output
    assert "2. git push" not in output


def test_ok_and_attention_notices_look_different(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")

    print_suggestions([Notice("Same words.", "ok")])
    ok_output = capsys.readouterr().out
    print_suggestions([Notice("Same words.", "attention")])
    attention_output = capsys.readouterr().out

    assert "\x1b[" in ok_output
    assert "\x1b[" in attention_output
    assert ok_output != attention_output
