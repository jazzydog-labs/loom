# Loom Workflows

This page collects the core workflows expected when using Loom to manage a
collection of repositories. Each command is shown with a short description so
you can skim and copy as needed.

## 1. Initialising a new environment

```bash
python3 loom.py init --dev-root ~/dev    # clones repos and runs bootstrap
```

This sets up the directory structure under `~/dev/foundry/` and optionally
executes the bootstrap script for system dependencies.

## 2. Checking repository status

```bash
python3 loom.py status
```

Displays a condensed table showing each repository's current branch and whether
it is ahead, behind, or has local changes.

## 3. Synchronising repositories

```bash
python3 loom.py sync
```

Runs `git pull` in parallel across all clean repositories. Add `--push` to also
push commits that are already ahead of the upstream remote when it is safe to do
so.

## 4. Navigating into a repository

```bash
python3 loom.py go <repo>
```

Prints the path to `<repo>` and additional context such as the current branch or
any outstanding changes. When used in a shell function it can also `cd` you into
the directory directly.

## 5. Listing TODO items

```bash
python3 loom.py todos
```

Aggregates TODOs from `todo.md` files and from `#todo:` comments inside the
source code. Results are grouped by file for quick triage.

---

These workflows cover the most common day‑to‑day actions. For full command
options run `python3 loom.py --help`.
