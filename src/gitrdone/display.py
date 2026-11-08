"""Color-coded terminal output for gitrdone."""

from collections.abc import Sequence

from rich.console import Console
from rich.padding import Padding
from rich.text import Text

from gitrdone.advice import Notice, Step, Suggestion

_NOTICE_STYLES = {"info": "", "ok": "green", "attention": "bold yellow"}


def _print_notice(console: Console, notice: Notice) -> None:
    text = Text(notice.text, style=_NOTICE_STYLES[notice.level])
    console.print(Padding(text, (0, 0, 1, 0)))


def _print_suggestion(console: Console, number: int, suggestion: Suggestion) -> None:
    heading = Text.assemble(
        (f"{number}. ", "bold"), (suggestion.command, "bold green")
    )
    # Soft wrapping keeps a command on one line so it can be copied intact.
    console.print(heading, soft_wrap=True)
    console.print(Padding(Text(suggestion.reason, style="cyan"), (0, 0, 0, 3)))
    if suggestion.warning:
        console.print(
            Padding(Text(f"Warning: {suggestion.warning}", style="bold red"), (0, 0, 0, 3))
        )
    console.print()


def print_suggestions(steps: Sequence[Step]) -> None:
    """Print notices as they come and number the suggested commands in order."""
    console = Console()
    number = 0
    for step in steps:
        if isinstance(step, Notice):
            _print_notice(console, step)
        else:
            number += 1
            _print_suggestion(console, number, step)
