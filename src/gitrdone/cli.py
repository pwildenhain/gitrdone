"""Command-line controller for gitrdone."""

from typing import Annotated

import typer

from gitrdone.advice import (
    describe_status,
    explain_command,
    plan_branch,
    plan_save,
    plan_setup,
    plan_suggest,
    plan_sync,
    plan_undo,
)
from gitrdone.display import print_suggestions
from gitrdone.repo_state import (
    read_branch_state,
    read_changed_files,
    read_repo_state,
    read_setup_state,
)


class GitRdoneCLI:
    """Registers and handles the gitrdone commands.

    Every command follows the same contract:

    - It only reads the state of the repository. It never runs a git command
      that changes anything; the user stays in control of what gets executed.
    - It prints suggested git commands, each with a short explanation of why
      that command fits the current state of the repository.
    - It stays within the basic git usage an analyst needs. Advanced workflows
      such as rebasing, cherry-picking, or submodules are out of scope.
    - Its terminal output is color coded with rich.

    Each command reads the repository, passes those facts to a pure planning
    function, and prints the result.
    """

    def __init__(self) -> None:
        self.app = typer.Typer(
            name="gitrdone",
            help="Get plain-language advice on which git commands to run next.",
            no_args_is_help=True,
        )
        self.app.command(help="Recommend what to do next in this repository.")(
            self.suggest
        )
        self.app.command(help="Explain the current repository state in plain language.")(
            self.status
        )
        self.app.command(help="Suggest how to get a new project set up with git.")(
            self.setup
        )
        self.app.command(help="Suggest how to save your work in a commit.")(self.save)
        self.app.command(help="Suggest how to sync with the remote repository.")(
            self.sync
        )
        self.app.command(help="Suggest how to create, switch, or merge branches.")(
            self.branch
        )
        self.app.command(help="Suggest the safest way to undo a change.")(self.undo)
        self.app.command(help="Explain what a basic git command does.")(self.explain)

    def suggest(self) -> None:
        """Recommend the single most useful next step for this repository.

        This is the main entry point for users who don't know where to start.
        Addresses the most pressing situation, in priority order: not a git
        repository, merge conflict in progress, uncommitted changes, commits to
        pull, commits to push, nothing to do.
        """
        print_suggestions(plan_suggest(read_repo_state(), read_changed_files()))

    def status(self) -> None:
        """Describe the current state of the repository in plain language.

        Summarizes the current branch, staged changes, unstaged changes,
        untracked files, and how far the branch is ahead of or behind its
        remote. Uses color to separate what is safe from what needs attention,
        and reports the state only, without recommending commands.
        """
        print_suggestions(describe_status(read_repo_state(), read_changed_files()))

    def setup(self) -> None:
        """Suggest the steps for getting a project set up with git.

        Suggests only the steps still missing: initializing or cloning the
        repository, setting ``user.name`` and ``user.email``, adding a
        ``.gitignore``, and connecting a remote. Warns about files that
        analysts should usually keep out of version control, such as large
        data files, credentials, and notebook checkpoints.
        """
        print_suggestions(
            plan_setup(read_repo_state(), read_setup_state(), read_changed_files())
        )

    def save(self) -> None:
        """Suggest how to save the current work in a commit.

        Lists the changed files and suggests the ``git add`` and ``git commit``
        commands needed to commit them, explaining the difference between
        staging and committing. Leaves out and warns about files that look like
        they shouldn't be committed. If there is nothing to commit, says so.
        """
        print_suggestions(plan_save(read_repo_state(), read_changed_files()))

    def sync(self) -> None:
        """Suggest how to bring the local and remote repositories in line.

        Compares the current branch with its remote and suggests ``git pull``,
        ``git push``, or a pull followed by a push when the two have diverged.
        Covers the common blockers: no remote configured, no upstream branch
        set, and uncommitted changes that should be committed first. Suggests
        ``git fetch`` when the remote information may be stale, since this tool
        does not contact the remote itself.
        """
        print_suggestions(plan_sync(read_repo_state()))

    def branch(self) -> None:
        """Suggest how to work with branches given the current branch state.

        Shows the current branch and the local branches. Suggests creating and
        switching to a new branch when the user is working directly on the
        default branch, ``git switch`` for moving between existing branches,
        and ``git merge`` for bringing finished work back. If a merge conflict
        is in progress, explains how to resolve it and finish or abort the
        merge.
        """
        print_suggestions(
            plan_branch(read_repo_state(), read_branch_state(), read_changed_files())
        )

    def undo(self) -> None:
        """Suggest the safest way to undo changes in the current state.

        Offers options based on what can be undone: unstaging a file
        (``git restore --staged``), discarding edits to a file
        (``git restore``), amending a commit that hasn't been pushed
        (``git commit --amend``), and reversing a commit that has been pushed
        (``git revert``). Lists options that don't lose work first, and clearly
        warns when a suggested command permanently discards changes.
        """
        print_suggestions(plan_undo(read_repo_state(), read_changed_files()))

    def explain(
        self,
        command: Annotated[
            str,
            typer.Argument(help="The git command to explain, for example 'commit'."),
        ],
    ) -> None:
        """Explain what a basic git command does and when to use it.

        Prints a short description of the command, when an analyst would use
        it, and a typical example. Accepts the name with or without the leading
        ``git``. If the command is outside the supported basics, says that it
        is out of scope and points to the official git documentation.

        Args:
            command: The name of the git command to explain.
        """
        print_suggestions(explain_command(command))


app = GitRdoneCLI().app

if __name__ == "__main__":
    app()
