# gitrdone

> **This package was built with [Claude Code](https://claude.com/claude-code), Anthropic's AI coding tool.** Claude Code wrote the code and its tests, and the maintainer directed what the tool should do and how it should be designed.
>
> **Does it use AI when I run it?** No. The advice comes from fixed rules written into the program, so the same situation always gets the same advice. You don't need an AI service or an account.
>
> **Does it send my code or data anywhere?** No. It makes no network connections of its own. It asks the git on your computer about your project, and it looks at file names and sizes, not what's inside your files.
>
> **Could it damage my project?** It only reads the state of your project and never runs a git command that changes anything. Automated tests check this against real git repositories.
>
> **Can I trust the advice?** The expected advice for each situation is written down as automated tests, and every suggestion comes with its reason. It can still be wrong, so read the explanation before you run a command, and take any warning seriously. If something looks off, please [open an issue](https://github.com/pwildenhain/gitrdone/issues).

Plain-language advice on which git command to run next, written for data analysts who are new to version control.

Run `gitrdone` inside a project and it looks at where your work stands, then tells you which git commands fit and why. For example, `gitrdone save` in a project with a new SQL query and a file of passwords gives you this:

```text
Changed files: .env, monthly_revenue.sql

.env looks like it holds passwords or other credentials, so it usually
shouldn't be committed. Listing it in a .gitignore file tells git to leave it
out.

1. git add monthly_revenue.sql
   Staging marks these files as ready to go in your next commit, so you choose
   exactly what gets saved.

2. git commit -m "Describe your change"
   Saves your staged work as a commit, a permanent snapshot in your local
   history. Do this first so syncing can't disturb your work.
```

## What it does and doesn't do

**gitrdone only gives advice. It never runs a git command that changes anything.** You read the suggestion, decide whether it makes sense, and run it yourself, so you can't break your project by trying a gitrdone command.

It covers the everyday git an analyst needs:

- Starting a project, or copying an existing one
- Saving your work in commits
- Sharing work with your team and getting theirs
- Working on branches and merging them
- Fixing merge conflicts
- Undoing mistakes safely

It deliberately leaves out advanced topics such as rebasing, cherry-picking, and submodules. If you ask about one of those, it points you to the [official git documentation](https://git-scm.com/docs).

Two limits are worth knowing:

- **It doesn't contact your team's server.** It only knows what git last heard from the remote, so it may suggest `git fetch` to check for new work.
- **Its file warnings are a safety net, not a guarantee.** It flags files by name (such as `.env` or `*.pem`) and by size (50 MB or more). A password inside `query.sql` won't be caught, so look over what you're committing.

## Install

You need two things first:

1. **Git.** Run `git --version` in a terminal to check. If you get an error, [download git](https://git-scm.com/downloads).
2. **uv**, a tool that installs Python programs. It sets up the right version of Python for you, so you don't need to install Python yourself.

   On Windows, in PowerShell:

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   On macOS or Linux:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

Then close your terminal, open a new one, and install gitrdone:

```bash
uv tool install git+https://github.com/pwildenhain/gitrdone
```

Check that it worked:

```bash
gitrdone --help
```

If your terminal says the command isn't found, run `uv tool update-shell`, then open a new terminal.

To remove it later, run `uv tool uninstall gitrdone`.

## Getting started

Open a terminal in your project folder and run:

```bash
gitrdone suggest
```

That's the only command you need to remember. It finds the most pressing thing to deal with and tells you what to do about it. Follow its advice, run it again, and repeat until it says everything is up to date.

## Commands

Run these from anywhere inside your project folder.

| Command | Use it when you want to... |
|---|---|
| `gitrdone suggest` | Know what to do next |
| `gitrdone status` | Understand where your work stands |
| `gitrdone setup` | Get a project ready for git |
| `gitrdone save` | Save your work in a commit |
| `gitrdone sync` | Share your work and get your team's |
| `gitrdone branch` | Create, switch, or merge branches |
| `gitrdone undo` | Take something back |
| `gitrdone explain <command>` | Learn what a git command does |

### `gitrdone suggest`

Recommends the single most useful next step. It deals with one situation at a time, most urgent first: not being in a git project, a merge conflict, unsaved work, new work to download, then work to upload. If there's nothing to do, it tells you everything is up to date.

### `gitrdone status`

Describes your project in plain language: which branch you're on, which files have changed, and how your work compares with the shared copy. Green means all is well and yellow means something needs your attention. It only reports and doesn't recommend commands.

### `gitrdone setup`

Checks each one-time setup step and lists only the ones you haven't done:

- Starting a git project in this folder, or copying an existing one
- Setting the name and email attached to your commits
- Connecting to a shared copy on your team's server
- Adding a `.gitignore` file, which tells git which files to leave out

It also warns you about files that usually don't belong in git: large data files, credentials, and notebook checkpoints.

### `gitrdone save`

Lists your changed files and gives you the commands to commit them. Files that look risky are left out of the suggested command and flagged, so you can decide what to do with them. If there's nothing to save, it says so.

### `gitrdone sync`

Compares your branch with the shared copy and tells you whether to download, upload, or do both, in the right order. If something would get in the way, such as unsaved work or no connection to a shared copy yet, it tells you how to fix that first.

### `gitrdone branch`

Shows your branches and what you can do from where you are. On your main branch, it suggests starting a new branch for your work. On any other branch, it shows how to bring finished work back. If a merge has stopped because of a conflict, it explains how to finish or cancel it.

### `gitrdone undo`

Lists what can be undone right now, safest options first:

- Taking a file back out of your next commit
- Fixing your last commit, if you haven't shared it yet
- Reversing your last commit, if you already have
- Throwing away edits to a file

The last one can't be reversed, so it always comes with a warning.

### `gitrdone explain <command>`

Tells you what a git command does, when you'd use it, and gives an example. You can write the name with or without `git`.

```text
$ gitrdone explain push

Uploads your commits to the remote so others can see them. Use it when you have
finished work you want to share.

1. git push
   Sends the commits on your current branch up to the shared copy.
```

It covers `init`, `clone`, `config`, `status`, `add`, `commit`, `fetch`, `pull`, `push`, `remote`, `branch`, `switch`, `merge`, `restore`, `revert`, `log`, and `diff`.

## A typical day

| What you're doing | What to run |
|---|---|
| Sitting down to start work | `gitrdone sync` |
| Starting something new | `gitrdone branch` |
| Reaching a good stopping point | `gitrdone save` |
| Ready to share your work | `gitrdone sync` |
| Something went wrong | `gitrdone undo` |
| Not sure what's going on | `gitrdone suggest` |

## Words you'll see

| Term | What it means |
|---|---|
| **Repository** (or repo) | A project that git is tracking |
| **Commit** | A saved snapshot of your work, with a note about what changed |
| **Staging** | Choosing which files go in your next commit |
| **Remote** | The shared copy of the project, usually on a service like GitHub |
| **Push** | Upload your commits to the remote |
| **Pull** | Download new commits from the remote and combine them with yours |
| **Fetch** | Check the remote for new work without changing your files |
| **Branch** | A separate line of work, so you can make changes without affecting the main version |
| **Merge** | Bring the work from one branch into another |
| **Merge conflict** | Two people changed the same lines, and git needs you to choose what to keep |
| **`.gitignore`** | A file listing what git should leave out |

## Contributing

The project uses [uv](https://docs.astral.sh/uv/). After cloning it:

```bash
uv sync
uv run pytest
uv run mypy --strict src tests
```
