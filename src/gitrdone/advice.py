"""Decide which git commands to suggest for a given repository state."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, NamedTuple

from gitrdone.repo_state import BranchState, ChangedFiles, RepoState, SetupState

_CREDENTIAL_NAMES = frozenset({".env", "credentials.json", "id_rsa"})
_CREDENTIAL_SUFFIXES = (".pem", ".key")
_CHECKPOINT_FOLDER = ".ipynb_checkpoints/"
_GIT_DOCS_URL = "https://git-scm.com/docs"


@dataclass(frozen=True)
class Suggestion:
    """A git command for the user to run and the reason it fits."""

    command: str
    reason: str
    warning: str | None = None


@dataclass(frozen=True)
class Notice:
    """Something to tell the user that isn't a command to run."""

    text: str
    level: Literal["info", "ok", "attention"] = "info"


Step = Suggestion | Notice


def _commits(count: int) -> str:
    return f"{count} commit" if count == 1 else f"{count} commits"


def _command_paths(paths: Iterable[str]) -> str:
    """Format file names for a command line, quoting any with spaces."""
    return " ".join(f'"{path}"' if " " in path else path for path in paths)


def _listed(paths: Iterable[str]) -> str:
    return ", ".join(paths)


def _all_changed(files: ChangedFiles) -> list[str]:
    combined = files.staged + files.unstaged + files.untracked
    return list(dict.fromkeys(combined))


def _risk(path: str, files: ChangedFiles) -> str | None:
    """Describe why a file shouldn't be committed, or None if it looks fine."""
    name = path.rsplit("/", 1)[-1]
    if path in files.large:
        return "is a very large file"
    if name in _CREDENTIAL_NAMES or name.endswith(_CREDENTIAL_SUFFIXES):
        return "looks like it holds passwords or other credentials"
    if _CHECKPOINT_FOLDER in path:
        return "is a notebook checkpoint that Jupyter creates automatically"
    return None


def _risk_notices(paths: Iterable[str], files: ChangedFiles) -> list[Notice]:
    return [
        Notice(
            f"{path} {why}, so it usually shouldn't be committed. Listing it in "
            "a .gitignore file tells git to leave it out.",
            "attention",
        )
        for path in paths
        if (why := _risk(path, files)) is not None
    ]


def _outside_repository() -> list[Suggestion]:
    return [
        Suggestion(
            "git init",
            "This folder isn't a git repository yet. Run this to start "
            "tracking the project in this folder.",
        ),
        Suggestion(
            "git clone <url>",
            "Or, if the project already exists somewhere else, run this "
            "instead to download your own copy of it.",
        ),
    ]


def _switch_to_a_branch() -> Suggestion:
    return Suggestion(
        "git switch <branch>",
        "You aren't on a branch right now, so there is nothing to "
        "sync. Switch to the branch you want to work on first.",
    )


def _add_remote() -> Suggestion:
    return Suggestion(
        "git remote add origin <url>",
        "This project isn't connected to a shared copy, called a "
        "remote, so there is nowhere to sync with. Use the address of "
        "the repository your team hosts.",
    )


def _publish_branch(remote: str, branch: str) -> Suggestion:
    return Suggestion(
        f"git push -u {remote} {branch}",
        f"The branch {branch} hasn't been shared yet. This "
        "uploads it and links it to the remote so future syncs know "
        "where to go.",
    )


def _commit() -> Suggestion:
    return Suggestion(
        'git commit -m "Describe your change"',
        "Saves your staged work as a commit, a permanent snapshot in your "
        "local history. Do this first so syncing can't disturb your work.",
    )


def _commit_steps(state: RepoState) -> list[Suggestion]:
    steps: list[Suggestion] = []
    if state.has_unstaged_changes or not state.has_staged_changes:
        steps.append(
            Suggestion(
                "git add <file>",
                "Marks each file you want to keep as ready to save, which is "
                "called staging. Repeat it for every file that belongs in the "
                "commit, and leave out data files and credentials.",
            )
        )
    steps.append(_commit())
    return steps


def _abort_merge() -> Suggestion:
    return Suggestion(
        "git merge --abort",
        "Or, to back out instead, this cancels the merge and puts your files "
        "back the way they were before it started.",
        warning="Any conflicts you have already fixed in this merge will be lost.",
    )


def _conflict_steps(files: ChangedFiles) -> list[Step]:
    return [
        Notice(
            f"A merge is stuck on conflicts in: {_listed(files.conflicted)}. Open "
            "each file and edit it to keep the content you want, removing the "
            "<<<<<<<, =======, and >>>>>>> marker lines.",
            "attention",
        ),
        Suggestion(
            "git add <file>",
            "After you have fixed a conflicted file, this tells git it is "
            "resolved. Repeat it for each conflicted file.",
        ),
        Suggestion(
            'git commit -m "Describe your change"',
            "Once every conflict is resolved, this saves the result and "
            "finishes the merge.",
        ),
        _abort_merge(),
    ]


def _pull(state: RepoState, has_local_work: bool) -> Suggestion:
    if not has_local_work:
        return Suggestion(
            "git pull",
            f"The remote, the shared copy of this project, has "
            f"{_commits(state.behind)} you don't have yet. This downloads them.",
        )
    summary = f"The remote has {_commits(state.behind)} you don't have yet"
    if state.ahead:
        summary += f", and you have {_commits(state.ahead)} it doesn't"
    return Suggestion(
        "git pull --no-rebase",
        f"{summary}. This downloads the remote's work and merges it with "
        "yours. If you both changed the same lines, git will ask you to "
        "choose what to keep.",
    )


def _push(state: RepoState) -> Suggestion:
    if state.ahead:
        reason = (
            f"You have {_commits(state.ahead)} that the remote doesn't have "
            "yet. This uploads your work so others can see it."
        )
    else:
        reason = "Once your work is committed, this uploads it so others can see it."
    return Suggestion("git push", reason)


def _fetch(has_local_work: bool) -> Suggestion:
    if has_local_work:
        reason = (
            "gitrdone only knows what git last heard from the remote. This "
            "checks for new work from others without changing your files. If "
            "any turns up, run gitrdone sync again."
        )
    else:
        reason = (
            "Your branch is up to date as of the last time git checked the "
            "remote. gitrdone doesn't contact the remote itself, so this "
            "checks for new work from others without changing your files."
        )
    return Suggestion("git fetch", reason)


def plan_sync(state: RepoState) -> list[Suggestion]:
    """Return the commands that sync the repository, in the order to run them."""
    if not state.is_repository:
        return _outside_repository()

    if state.branch is None:
        return [_switch_to_a_branch()]

    plan: list[Suggestion] = []
    if state.has_uncommitted_changes or not state.has_commits:
        plan.extend(_commit_steps(state))

    if state.remote is None:
        plan.append(_add_remote())
        return plan

    if not state.has_commits:
        return plan

    if not state.has_upstream:
        plan.append(_publish_branch(state.remote, state.branch))
        return plan

    has_local_work = state.ahead > 0 or state.has_uncommitted_changes
    if state.behind:
        plan.append(_pull(state, has_local_work))
    else:
        plan.append(_fetch(has_local_work))
    if has_local_work:
        plan.append(_push(state))
    return plan


def plan_suggest(state: RepoState, files: ChangedFiles) -> list[Step]:
    """Return the steps for the single most pressing situation."""
    if not state.is_repository:
        return [*_outside_repository()]
    if files.conflicted:
        return _conflict_steps(files)
    if state.branch is None:
        return [_switch_to_a_branch()]
    if state.has_uncommitted_changes or not state.has_commits:
        return [*_commit_steps(state)]
    if state.remote is None:
        return [_add_remote()]
    if not state.has_upstream:
        return [_publish_branch(state.remote, state.branch)]
    if state.behind:
        return [_pull(state, has_local_work=state.ahead > 0)]
    if state.ahead:
        return [_push(state)]
    return [
        Notice(
            "Everything is up to date as of the last time git checked the remote.",
            "ok",
        )
    ]


def _describe_remote(state: RepoState) -> list[Notice]:
    if not state.has_commits:
        return [Notice("This project has no commits yet.", "attention")]
    if state.remote is None:
        return [
            Notice(
                "This project isn't connected to a remote, a shared copy that "
                "others can reach.",
                "attention",
            )
        ]
    if state.branch is None:
        return []
    if not state.has_upstream:
        return [
            Notice(
                f"The branch {state.branch} hasn't been shared with the remote yet.",
                "attention",
            )
        ]
    if not state.ahead and not state.behind:
        return [
            Notice(
                "Your branch is up to date as of the last time git checked the "
                "remote, the shared copy of this project.",
                "ok",
            )
        ]
    notices: list[Notice] = []
    if state.ahead:
        notices.append(
            Notice(
                f"You have {_commits(state.ahead)} that the remote doesn't have yet.",
                "attention",
            )
        )
    if state.behind:
        notices.append(
            Notice(
                f"The remote has {_commits(state.behind)} you don't have yet.",
                "attention",
            )
        )
    return notices


def describe_status(state: RepoState, files: ChangedFiles) -> list[Notice]:
    """Describe the repository in plain language, recommending nothing."""
    if not state.is_repository:
        return [Notice("This folder isn't a git repository.", "attention")]

    notices = [
        Notice(f"You are on the branch {state.branch}.", "ok")
        if state.branch
        else Notice("You are not on a branch right now.", "attention")
    ]
    if files.conflicted:
        notices.append(
            Notice(
                f"Files with merge conflicts: {_listed(files.conflicted)}", "attention"
            )
        )
    if files.staged:
        notices.append(
            Notice(
                "Staged files, which are ready to be saved in your next commit: "
                f"{_listed(files.staged)}",
                "ok",
            )
        )
    if files.unstaged:
        notices.append(
            Notice(
                "Edited files that aren't staged for your next commit yet: "
                f"{_listed(files.unstaged)}",
                "attention",
            )
        )
    if files.untracked:
        notices.append(
            Notice(
                f"New files that git isn't tracking yet: {_listed(files.untracked)}",
                "attention",
            )
        )
    notices.extend(_describe_remote(state))
    return notices


def plan_setup(
    state: RepoState, setup: SetupState, files: ChangedFiles
) -> list[Step]:
    """Return only the setup steps that are still missing."""
    steps: list[Step] = []
    if not state.is_repository:
        steps.extend(_outside_repository())
    if not setup.has_user_name:
        steps.append(
            Suggestion(
                'git config --global user.name "Your Name"',
                "Sets the name attached to every commit you make, so others "
                "can see who made each change.",
            )
        )
    if not setup.has_user_email:
        steps.append(
            Suggestion(
                'git config --global user.email "you@example.com"',
                "Sets the email attached to every commit you make. Use the "
                "address from your team's git hosting account.",
            )
        )
    if state.is_repository:
        if state.remote is None:
            steps.append(_add_remote())
        if not setup.has_gitignore:
            steps.append(
                Notice(
                    "There is no .gitignore file yet. Create a file with that "
                    "name and list what git should leave out, such as data "
                    "extracts, credentials, and .ipynb_checkpoints/.",
                    "attention",
                )
            )
    steps.extend(_risk_notices(_all_changed(files), files))
    return steps or [Notice("This project is set up.", "ok")]


def plan_save(state: RepoState, files: ChangedFiles) -> list[Step]:
    """Return the steps that commit the current work."""
    if not state.is_repository:
        return [*_outside_repository()]
    if files.conflicted:
        return _conflict_steps(files)

    changed = _all_changed(files)
    if not changed:
        return [Notice("Nothing to commit. All your work is already saved.", "ok")]

    steps: list[Step] = [Notice(f"Changed files: {_listed(changed)}")]
    steps.extend(_risk_notices(changed, files))

    risky_staged = [path for path in files.staged if _risk(path, files)]
    safe_staged = [path for path in files.staged if not _risk(path, files)]
    to_add = [
        path
        for path in dict.fromkeys(files.unstaged + files.untracked)
        if not _risk(path, files)
    ]

    if risky_staged:
        steps.append(
            Suggestion(
                f"git restore --staged {_command_paths(risky_staged)}",
                "Takes these files back out of your next commit without "
                "changing the files themselves.",
            )
        )
    if to_add:
        steps.append(
            Suggestion(
                f"git add {_command_paths(to_add)}",
                "Staging marks these files as ready to go in your next commit, "
                "so you choose exactly what gets saved.",
            )
        )
    if to_add or safe_staged:
        steps.append(_commit())
    return steps


def _branch_summary(branches: BranchState) -> Notice:
    where = (
        f"You are on the branch {branches.current}."
        if branches.current
        else "You are not on a branch right now."
    )
    return Notice(f"{where} Local branches: {_listed(branches.local)}")


def _switch_to(branch: str) -> Suggestion:
    return Suggestion(
        f"git switch {branch}",
        f"Moves you to the branch {branch} and updates your files to match it.",
    )


def plan_branch(
    state: RepoState, branches: BranchState, files: ChangedFiles
) -> list[Step]:
    """Return the branch actions that fit the current branch."""
    if not state.is_repository:
        return [*_outside_repository()]
    if files.conflicted:
        return _conflict_steps(files)
    if not state.has_commits:
        return [*_commit_steps(state)]

    current, default = branches.current, branches.default
    others = [name for name in branches.local if name not in (current, default)]
    steps: list[Step] = [_branch_summary(branches)]

    if current is None:
        steps.append(_switch_to(default) if default else _switch_to_a_branch())
    elif current == default:
        steps.append(
            Suggestion(
                "git switch -c <new-branch>",
                "You are on the main branch of this project. Creating a new "
                "branch keeps your work separate until it is finished.",
            )
        )
        steps.extend(_switch_to(name) for name in others)
    else:
        steps.extend(_switch_to(name) for name in others)
        if default:
            steps.append(_switch_to(default))
            steps.append(
                Suggestion(
                    f"git merge {current}",
                    f"When your work is finished, run this from {default} to "
                    f"bring the changes from {current} into it.",
                )
            )
    return steps


def _undo_last_commit(state: RepoState) -> Suggestion:
    if state.has_upstream and state.ahead == 0:
        return Suggestion(
            "git revert HEAD",
            "Your last commit has already been shared, so this adds a new "
            "commit that reverses it and keeps the history intact.",
        )
    return Suggestion(
        "git commit --amend",
        "Your last commit hasn't been shared yet, so this lets you replace it "
        "to fix its message or add something you forgot.",
    )


def plan_undo(state: RepoState, files: ChangedFiles) -> list[Step]:
    """Return what can be undone, safest options first."""
    if not state.is_repository:
        return [Notice("This folder isn't a git repository.", "attention")]
    if files.conflicted:
        return [_abort_merge()]

    if not state.has_commits:
        if not files.staged:
            return [Notice("Nothing to undo yet.", "ok")]
        return [
            Suggestion(
                f"git rm --cached {_command_paths(files.staged)}",
                "Takes these files back out of your first commit without "
                "changing the files themselves.",
            )
        ]

    steps: list[Step] = []
    if files.staged:
        steps.append(
            Suggestion(
                f"git restore --staged {_command_paths(files.staged)}",
                "Takes these files back out of your next commit and keeps "
                "your edits in place.",
            )
        )
    steps.append(_undo_last_commit(state))
    if files.unstaged:
        steps.append(
            Suggestion(
                f"git restore {_command_paths(files.unstaged)}",
                "Throws away your edits and puts these files back to how they "
                "were at the last commit.",
                warning="This permanently discards those edits. They can't be recovered.",
            )
        )
    return steps


class _Basic(NamedTuple):
    description: str
    example: str
    example_reason: str


_BASICS: dict[str, _Basic] = {
    "init": _Basic(
        "Starts tracking a folder with git. Use it once, when a project isn't "
        "under version control yet.",
        "git init",
        "Run this inside the project folder to turn it into a git repository.",
    ),
    "clone": _Basic(
        "Downloads your own copy of an existing project. Use it when joining "
        "a project that already lives on a shared server.",
        "git clone <url>",
        "Creates a new folder holding the project and its full history.",
    ),
    "config": _Basic(
        "Reads or changes git's settings. Use it when setting up git for the "
        "first time, mainly for your name and email.",
        'git config --global user.name "Your Name"',
        "Sets the name attached to every commit you make on this computer.",
    ),
    "status": _Basic(
        "Shows which files have changed and which are ready to commit. Use it "
        "whenever you aren't sure what state your work is in.",
        "git status",
        "Lists your changes without altering anything, so it is always safe.",
    ),
    "add": _Basic(
        "Stages a file, marking it as ready to go in your next commit. Use it "
        "to choose exactly what gets saved.",
        "git add analysis.sql",
        "Includes the current version of this file in your next commit.",
    ),
    "commit": _Basic(
        "Saves your staged files as a permanent snapshot in your local "
        "history. Use it each time you finish a meaningful piece of work.",
        'git commit -m "Add monthly revenue query"',
        "Records the snapshot along with a message describing what changed.",
    ),
    "fetch": _Basic(
        "Checks the remote, the shared copy of the project, for new work. Use "
        "it to see what others have done without changing your files.",
        "git fetch",
        "Updates what git knows about the remote and leaves your files alone.",
    ),
    "pull": _Basic(
        "Downloads new work from the remote and combines it with yours. Use "
        "it before starting work so you begin from the latest version.",
        "git pull",
        "Brings the commits others have shared into your current branch.",
    ),
    "push": _Basic(
        "Uploads your commits to the remote so others can see them. Use it "
        "when you have finished work you want to share.",
        "git push",
        "Sends the commits on your current branch up to the shared copy.",
    ),
    "remote": _Basic(
        "Manages the shared copies this project is connected to. Use it to "
        "connect a project to a hosted repository.",
        "git remote add origin <url>",
        "Connects this project to a hosted repository under the name origin.",
    ),
    "branch": _Basic(
        "Lists your branches, which are separate lines of work. Use it to see "
        "what branches exist and which one you are on.",
        "git branch",
        "Prints your local branches and marks the one you are currently on.",
    ),
    "switch": _Basic(
        "Moves you to a different branch. Use it to change what you are "
        "working on or to start a new line of work.",
        "git switch -c monthly-report",
        "Creates a new branch called monthly-report and moves you onto it.",
    ),
    "merge": _Basic(
        "Brings the work from another branch into your current one. Use it "
        "when work on a separate branch is finished.",
        "git merge monthly-report",
        "Combines the monthly-report branch into the branch you are on now.",
    ),
    "restore": _Basic(
        "Puts files back to an earlier state. Use it to unstage a file or to "
        "throw away edits you no longer want.",
        "git restore --staged analysis.sql",
        "Takes the file out of your next commit and keeps your edits in place.",
    ),
    "revert": _Basic(
        "Reverses an earlier commit by adding a new one. Use it to undo work "
        "that has already been shared with others.",
        "git revert HEAD",
        "Adds a new commit that cancels out your most recent commit.",
    ),
    "log": _Basic(
        "Shows the history of commits. Use it to see who changed what, and "
        "when they changed it.",
        "git log --oneline",
        "Lists each commit on a single line, with the newest commit first.",
    ),
    "diff": _Basic(
        "Shows exactly which lines have changed. Use it to review your edits "
        "before you stage or commit them.",
        "git diff",
        "Prints the edits you have made that aren't staged for a commit yet.",
    ),
}


def explain_command(name: str) -> list[Step]:
    """Explain a basic git command, with or without the leading ``git``."""
    command = name.strip().removeprefix("git ").strip()
    basic = _BASICS.get(command)
    if basic is None:
        return [
            Notice(
                f"{command} is out of scope for gitrdone, which covers the basics "
                f"an analyst needs. See the official documentation: {_GIT_DOCS_URL}",
                "attention",
            )
        ]
    return [Notice(basic.description), Suggestion(basic.example, basic.example_reason)]
