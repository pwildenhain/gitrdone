"""Read-only inspection of the git repository in the current directory."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

_CONFLICT_CODES = frozenset({"DD", "AU", "UD", "UA", "DU", "AA", "UU"})


@dataclass(frozen=True)
class RepoState:
    """The facts about a repository that advice is based on."""

    is_repository: bool
    has_commits: bool = False
    branch: str | None = None
    remote: str | None = None
    has_upstream: bool = False
    ahead: int = 0
    behind: int = 0
    has_staged_changes: bool = False
    has_unstaged_changes: bool = False

    @property
    def has_uncommitted_changes(self) -> bool:
        return self.has_staged_changes or self.has_unstaged_changes


LARGE_FILE_BYTES = 50 * 1024 * 1024
"""Files at or above this size are flagged, matching GitHub's warning threshold."""


@dataclass(frozen=True)
class ChangedFiles:
    """The files that differ from the last commit, relative to the repo root."""

    staged: tuple[str, ...] = ()
    unstaged: tuple[str, ...] = ()
    untracked: tuple[str, ...] = ()
    conflicted: tuple[str, ...] = ()
    large: tuple[str, ...] = ()


@dataclass(frozen=True)
class BranchState:
    """The local branches and which one work normally gets merged into."""

    current: str | None = None
    local: tuple[str, ...] = ()
    default: str | None = None


@dataclass(frozen=True)
class SetupState:
    """Which one-time setup steps have already been done."""

    has_user_name: bool = False
    has_user_email: bool = False
    has_gitignore: bool = False


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    # --no-optional-locks stops commands like status from rewriting the index.
    return subprocess.run(
        ["git", "--no-optional-locks", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _preferred_remote(remotes: list[str]) -> str | None:
    if "origin" in remotes:
        return "origin"
    return remotes[0] if remotes else None


def read_repo_state() -> RepoState:
    """Describe the repository in the current directory without changing it.

    Ahead and behind counts come from what git last heard from the remote. The
    remote itself is never contacted.
    """
    inside = _git("rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return RepoState(is_repository=False)

    status_lines = _git("status", "--porcelain").stdout.splitlines()
    # Each line starts with two columns: staged status, then unstaged status.
    has_staged = any(line[0] not in " ?" for line in status_lines)
    has_unstaged = any(line[1] != " " for line in status_lines)

    counts = _git("rev-list", "--left-right", "--count", "HEAD...@{upstream}")
    ahead, behind = 0, 0
    if counts.returncode == 0:
        ahead, behind = (int(value) for value in counts.stdout.split())

    return RepoState(
        is_repository=True,
        has_commits=_git("rev-parse", "--verify", "--quiet", "HEAD").returncode == 0,
        branch=_git("branch", "--show-current").stdout.strip() or None,
        remote=_preferred_remote(_git("remote").stdout.split()),
        has_upstream=counts.returncode == 0,
        ahead=ahead,
        behind=behind,
        has_staged_changes=has_staged,
        has_unstaged_changes=has_unstaged,
    )


def _repo_root() -> Path | None:
    toplevel = _git("rev-parse", "--show-toplevel")
    return Path(toplevel.stdout.strip()) if toplevel.returncode == 0 else None


def _is_large(path: Path) -> bool:
    return path.is_file() and path.stat().st_size >= LARGE_FILE_BYTES


def read_changed_files() -> ChangedFiles:
    """List the changed files, without changing the repository."""
    root = _repo_root()
    if root is None:
        return ChangedFiles()

    # -z gives unquoted names, separated by NUL characters.
    output = _git(
        "-C", str(root), "status", "--porcelain", "-z", "--untracked-files=all"
    ).stdout
    entries = iter(output.split("\0"))
    staged: list[str] = []
    unstaged: list[str] = []
    untracked: list[str] = []
    conflicted: list[str] = []
    for entry in entries:
        if not entry:
            continue
        code, path = entry[:2], entry[3:]
        if "R" in code or "C" in code:
            # Renames and copies are followed by the original name.
            next(entries, None)
        if code == "??":
            untracked.append(path)
        elif code in _CONFLICT_CODES:
            conflicted.append(path)
        else:
            if code[0] != " ":
                staged.append(path)
            if code[1] != " ":
                unstaged.append(path)

    changed = dict.fromkeys(staged + unstaged + untracked + conflicted)
    return ChangedFiles(
        staged=tuple(staged),
        unstaged=tuple(unstaged),
        untracked=tuple(untracked),
        conflicted=tuple(conflicted),
        large=tuple(path for path in changed if _is_large(root / path)),
    )


def read_branch_state() -> BranchState:
    """Describe the local branches, without changing the repository."""
    listed = _git("branch", "--format=%(refname:short)")
    if listed.returncode != 0:
        return BranchState()

    # While detached, git lists a "(HEAD detached at ...)" pseudo-branch.
    local = tuple(
        name for name in listed.stdout.splitlines() if not name.startswith("(")
    )
    return BranchState(
        current=_git("branch", "--show-current").stdout.strip() or None,
        local=local,
        default=_default_branch(local),
    )


def _default_branch(local: tuple[str, ...]) -> str | None:
    remote_head = _git("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if remote_head.returncode == 0:
        return remote_head.stdout.strip().removeprefix("origin/")
    return next((name for name in ("main", "master") if name in local), None)


def read_setup_state() -> SetupState:
    """Check which setup steps are done, without changing the repository."""
    root = _repo_root()
    return SetupState(
        has_user_name=_git("config", "user.name").returncode == 0,
        has_user_email=_git("config", "user.email").returncode == 0,
        has_gitignore=root is not None and (root / ".gitignore").exists(),
    )
