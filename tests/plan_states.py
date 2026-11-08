"""Hand-built repository states and expected commands for the advice tests."""

from collections.abc import Sequence
from dataclasses import replace

from gitrdone.advice import Notice, Step, Suggestion
from gitrdone.repo_state import ChangedFiles, RepoState

INIT = "git init"
CLONE = "git clone <url>"
ADD = "git add <file>"
COMMIT = 'git commit -m "Describe your change"'
FETCH = "git fetch"
PULL = "git pull"
MERGE_PULL = "git pull --no-rebase"
PUSH = "git push"
ADD_REMOTE = "git remote add origin <url>"
SWITCH = "git switch <branch>"
ABORT_MERGE = "git merge --abort"

OUTSIDE = RepoState(is_repository=False)
SYNCED = RepoState(
    is_repository=True,
    has_commits=True,
    branch="main",
    remote="origin",
    has_upstream=True,
)
NO_COMMITS = replace(SYNCED, has_commits=False, has_upstream=False)
NO_REMOTE = replace(SYNCED, remote=None, has_upstream=False)
NO_UPSTREAM = replace(SYNCED, branch="analysis", has_upstream=False)
DETACHED = replace(SYNCED, branch=None, has_upstream=False)
AHEAD = replace(SYNCED, ahead=2)
BEHIND = replace(SYNCED, behind=3)
DIVERGED = replace(SYNCED, ahead=2, behind=3)

CLEAN = ChangedFiles()
CONFLICT = ChangedFiles(conflicted=("report.sql",))


def unstaged(state: RepoState) -> RepoState:
    return replace(state, has_unstaged_changes=True)


def staged(state: RepoState) -> RepoState:
    return replace(state, has_staged_changes=True)


def commands_of(steps: Sequence[Step]) -> list[str]:
    return [step.command for step in steps if isinstance(step, Suggestion)]


def suggestions_of(steps: Sequence[Step]) -> list[Suggestion]:
    return [step for step in steps if isinstance(step, Suggestion)]


def notices_of(steps: Sequence[Step]) -> list[Notice]:
    return [step for step in steps if isinstance(step, Notice)]


def text_of(steps: Sequence[Step]) -> str:
    """Join everything the user would read, for checking what gets mentioned."""
    parts: list[str] = []
    for step in steps:
        if isinstance(step, Notice):
            parts.append(step.text)
        else:
            parts.extend([step.command, step.reason, step.warning or ""])
    return " ".join(parts)
