"""Controller implementing loom operations."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, cast
import contextlib
import io
import json
import subprocess

from rich.console import Console, Group
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..core.config import ConfigManager
from ..core.git import GitManager
from ..core.repo_manager import RepoManager
from ..utils.emojis import get_emoji_manager
from ..views.repo_view import RepoView
from ..utils.worker_pool import map_parallel
from ..infra.todo_manager import TodoManager


class LoomController:
    """Coordinate CLI commands with the underlying managers."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()
        self.config = ConfigManager()
        self.git = GitManager()
        self.repos = RepoManager(self.config, self.git)
        self.emoji = get_emoji_manager()

    # ------------------------------------------------------------------
    # High level helpers
    # ------------------------------------------------------------------
    def start(self, app) -> None:
        """Show commands and repo details when called without arguments."""
        if self.config.get_display_config("show_commands_on_status", False):
            self.console.print("\n" + "═" * 50)
            self.console.print("[bold cyan]Available Commands:[/bold cyan]")
            self.console.print("═" * 50)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                try:
                    app(["--help"])
                except SystemExit:
                    pass
            self.console.print(buf.getvalue())
        self.show_details()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------
    def show_details(self) -> None:
        repos_config = self.config.load_repos()
        repos = repos_config.get("repos", [])
        if not repos:
            self.console.print("No repositories configured.")
            return

        dev_root = self.config.get_dev_root()
        foundry_dir = self.config.get_foundry_dir()
        if not dev_root:
            self.console.print(
                "Development root not configured. Please run 'loom init' first."
            )
            return

        repo_paths = {
            repo["name"]: repo["path"].replace("$DEV_ROOT", dev_root).replace(
                "$FOUNDRY_DIR", foundry_dir
            )
            for repo in repos
        }

        # Now handled by the overridden method in src/app/loom_controller.py
        # which uses RepoStatusService instead of RepoStatusReader
        raise NotImplementedError("This method should be overridden by the new LoomController")

    def init(self, dev_root: Optional[str], bootstrap: bool = True) -> None:
        dev_root = dev_root or self.get_dev_root_interactive()
        dev_root = str(Path(dev_root).expanduser())

        self.console.print("Creating directory structure...")
        if not self.repos.create_directory_structure(dev_root):
            self.console.print(
                f"{self.emoji.get_status('error')} Failed to create directories"
            )
            return

        self.repos.set_dev_root(dev_root)

        self.console.print("Cloning repositories...")
        clone_results = self.repos.clone_missing_repos(dev_root)
        self.console.print(
            f"{self.emoji.get_status('success')} Cloned {sum(clone_results.values())}/{len(clone_results)} repositories"
        )

        self.console.print("Moving loom to foundry directory...")
        if self.repos.move_loom_to_foundry(dev_root):
            self.console.print(
                f"{self.emoji.get_status('success')} Loom moved to foundry directory"
            )
        else:
            self.console.print(
                f"{self.emoji.get_status('warning')} Loom already in place"
            )

        if bootstrap:
            self.console.print("Running foundry-bootstrap...")
            bootstrap_success = self.repos.bootstrap_foundry(dev_root)  # type: ignore[attr-defined]
            if bootstrap_success:
                self.console.print(
                    f"{self.emoji.get_status('success')} Bootstrap completed"
                )
            else:
                self.console.print(
                    f"{self.emoji.get_status('error')} Bootstrap failed"
                )

        self.console.print(
            f"\n🎉 Foundry ecosystem initialized at {dev_root}/foundry"
        )
        self.console.print("All repositories have been cloned and organized.")

    def _get_single_fuzzy_match(self, query: str, candidates: list, min_score: int = 60) -> Optional[str]:
        """Check if there's exactly one good fuzzy match above the threshold, or one clearly best match."""
        from fuzzywuzzy import fuzz, process
        
        # Use partial_ratio for better substring matching (e.g., "ali" in "just-aliases")
        matches = process.extract(query, candidates, scorer=fuzz.partial_ratio, limit=len(candidates))
        good_matches = [match for match in matches if match[1] >= min_score]
        
        if len(good_matches) == 1:
            return good_matches[0][0]
        elif len(good_matches) > 1:
            # Check if there's one clearly best match (at least 20 points better than the second best)
            best_match = good_matches[0]
            second_best = good_matches[1]
            if best_match[1] - second_best[1] >= 20:
                return best_match[0]
        
        return None

    def _run_fzf_selection(self, candidates: list, query: str = "") -> Optional[str]:
        """Run fzf to select from candidates, return selected item or None."""
        try:
            subprocess.run(["fzf", "--version"], capture_output=True, check=True)
            fzf_cmd = ["fzf", "--prompt", "Select repository: ", "--height", "40%"]
            if query:
                fzf_cmd.extend(["--query", query])
            
            result = subprocess.run(
                fzf_cmd, input="\n".join(candidates), capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return None

    def go(self, repo_name: Optional[str], output_command: bool = False) -> None:
        from fuzzywuzzy import fuzz, process

        repo_names = list(self.repos.get_repo_paths().keys())
        if not repo_names:
            if output_command:
                print("echo 'No repositories found'")
            else:
                print(
                    json.dumps(
                        {
                            "error": "No repositories found",
                            "directory": None,
                            "message": None,
                            "context": None,
                        }
                    )
                )
            return

        selected_repo: Optional[str] = None
        if repo_name:
            prefix_matches = [n for n in repo_names if n.lower().startswith(repo_name.lower())]
            if len(prefix_matches) == 1:
                selected_repo = prefix_matches[0]
            elif len(prefix_matches) > 1:
                # Check if there's only one good fuzzy match among prefix matches
                single_match = self._get_single_fuzzy_match(repo_name, prefix_matches)
                if single_match:
                    selected_repo = single_match
                else:
                    # Multiple good matches, use fzf
                    selected_repo = self._run_fzf_selection(prefix_matches, repo_name)
                    if not selected_repo:
                        # Fallback to best fuzzy match
                        best_match = process.extractOne(repo_name, prefix_matches, scorer=fuzz.ratio)
                        if best_match and best_match[1] >= 30:
                            selected_repo = best_match[0]
                        else:
                            if output_command:
                                print(f"echo 'Repository {repo_name} not found'")
                            else:
                                print(
                                    json.dumps(
                                        {
                                            "error": f"Repository '{repo_name}' not found",
                                            "directory": None,
                                            "message": None,
                                            "context": None,
                                        }
                                    )
                                )
                            return
            else:
                # No prefix matches. Check if there's only one good fuzzy match across all repos
                single_match = self._get_single_fuzzy_match(repo_name, repo_names)
                if single_match:
                    selected_repo = single_match
                else:
                    # Multiple good matches or no good matches, try fzf
                    selected_repo = self._run_fzf_selection(repo_names, repo_name)
                    if not selected_repo:
                        # Fallback to best fuzzy match
                        best_match = process.extractOne(repo_name, repo_names, scorer=fuzz.ratio)
                        if best_match and best_match[1] >= 40:
                            selected_repo = best_match[0]
                        else:
                            if output_command:
                                print(f"echo 'Repository {repo_name} not found'")
                            else:
                                print(
                                    json.dumps(
                                        {
                                            "error": f"Repository '{repo_name}' not found",
                                            "directory": None,
                                            "message": None,
                                            "context": None,
                                        }
                                    )
                                )
                            return
        else:
            # No repo name provided, check if there's only one repo total
            if len(repo_names) == 1:
                selected_repo = repo_names[0]
            else:
                # Multiple repos, use fzf
                selected_repo = self._run_fzf_selection(repo_names)
                if not selected_repo:
                    if output_command:
                        print("echo 'No repository selected'")
                    else:
                        print(
                            json.dumps(
                                {
                                    "error": "fzf is not installed. Please run foundry-bootstrap/bootstrap.sh to install all dependencies.",
                                    "directory": None,
                                    "message": None,
                                    "context": None,
                                }
                            )
                        )
                    return

        repo_paths = self.repos.get_repo_paths()
        if selected_repo is None:
            self.console.print("No repository selected.")
            return

        repo_path = repo_paths[selected_repo]
        context = self._get_repo_context(selected_repo, repo_path)
        if output_command:
            print(f"cd {repo_path}")
        else:
            result = {
                "directory": repo_path,
                "message": context.get("message", "Project is active and ready for development"),
                "context": context.get("context", "Repository loaded successfully"),
            }
            print(json.dumps(result, indent=2))

    # ------------------------------------------------------------------
    # Repository sync operation
    # ------------------------------------------------------------------
    def sync(self, push: bool = False) -> None:
        """Pull latest changes for all clean repositories in parallel with real-time progress.

        A repository is considered safe to sync if:
        1. It has no uncommitted changes (status == "clean"), and
        2. For pull-only: It is not ahead of its upstream (local commits to push == 0).
        3. For push mode: It can be ahead (will push those commits).

        Dirty repositories are skipped and reported.
        
        Args:
            push: If True, also push local commits after pulling (when safe).
        """

        repo_paths = self.repos.get_repo_paths()
        if not repo_paths:
            self.console.print("No repositories configured – run 'loom init' first.")
            return

        # Initialize progress tracking
        repo_status = {}
        for name in repo_paths.keys():
            repo_status[name] = {"status": "pending", "message": "", "spinner": Spinner("dots")}

        def _sync_repo(item):
            name, path = item
            from pathlib import Path

            path_obj = Path(path)
            status = self.git.get_repo_status(path_obj)

            # Skip if repo has local modifications
            if status.get("status") != "clean":
                return (name, "skipped", "dirty working tree")

            ahead = status.get("ahead", "0")
            behind = status.get("behind", "0")

            # For pull-only mode, skip if ahead (as before)
            if not push and ahead != "0":
                return (name, "skipped", f"{ahead} commit(s) ahead")

            # For push mode, check if we've diverged (both ahead and behind)
            if push and ahead != "0" and behind != "0":
                return (name, "skipped", f"diverged: {ahead} ahead, {behind} behind")

            # Perform git pull
            pull_success, pull_had_changes, commits_pulled = self.git.pull_repo(path_obj)
            if not pull_success:
                return (name, "failed", "git pull error")

            # If we're in push mode and have commits to push, push them
            if push and ahead != "0":
                push_success, push_had_changes = self.git.push_repo(path_obj)
                if not push_success:
                    return (name, "failed", "git push error")
                
                # Format commit count messages
                push_commit_count = int(ahead)
                push_commit_word = "commit" if push_commit_count == 1 else "commits"
                
                if pull_had_changes and push_had_changes:
                    # Format pull commit count message
                    pull_commit_word = "commit" if commits_pulled == 1 else "commits"
                    return (name, "pulled_pushed", f"pulled {commits_pulled} {pull_commit_word} and pushed {push_commit_count} {push_commit_word}")
                elif pull_had_changes:
                    pull_commit_word = "commit" if commits_pulled == 1 else "commits"
                    return (name, "pulled_pushed", f"pulled {commits_pulled} {pull_commit_word}, no {push_commit_word} to push")
                elif push_had_changes:
                    return (name, "pulled_pushed", f"pushed {push_commit_count} {push_commit_word}")
                else:
                    return (name, "up_to_date", "already up to date")
            else:
                # Regular pull-only result
                if pull_had_changes:
                    pull_commit_word = "commit" if commits_pulled == 1 else "commits"
                    return (name, "pulled", f"pulled {commits_pulled} {pull_commit_word} from upstream")
                else:
                    return (name, "up_to_date", "already up to date")

        def _create_status_display():
            """Create the live status display."""
            # Calculate live summary counts
            synced_count = sum(1 for info in repo_status.values() if info["status"] in ["pulled", "pulled_pushed"])
            up_to_date_count = sum(1 for info in repo_status.values() if info["status"] == "up_to_date")
            skipped_count = sum(1 for info in repo_status.values() if info["status"] == "skipped")
            failed_count = sum(1 for info in repo_status.values() if info["status"] == "failed")
            
            # Create summary line
            summary_text = Text.from_markup(f"[bold]Sync summary:[/bold] Synced: {synced_count} | Up to date: {up_to_date_count} | Skipped: {skipped_count} | Failed: {failed_count}")
            
            # Build renderables list
            renderables = []
            renderables.append(summary_text)
            renderables.append(Text("[dim]Press ↵ to continue…[/]"))
            
            for name, info in repo_status.items():
                if info["status"] == "pending":
                    # Use Columns to properly combine spinner with text
                    spinner_text = Columns([info['spinner'], Text(f"{name}: syncing...")])
                    renderables.append(spinner_text)
                elif info["status"] == "pulled":
                    renderables.append(Text.from_markup(f"{self.emoji.get_status('success')} Synced  [bold]{name}[/bold]: {info['message']}"))
                elif info["status"] == "pulled_pushed":
                    renderables.append(Text.from_markup(f"{self.emoji.get_status('success')} Synced  [bold]{name}[/bold]: {info['message']}"))
                elif info["status"] == "up_to_date":
                    renderables.append(Text.from_markup(f"{self.emoji.get_status('info')}  {name}: {info['message']}"))
                elif info["status"] == "skipped":
                    renderables.append(Text.from_markup(f"{self.emoji.get_status('warning')}  Skipped {name}: {info['message']}"))
                elif info["status"] == "failed":
                    renderables.append(Text.from_markup(f"{self.emoji.get_status('error')}  Failed to sync {name}: {info['message']}"))
            
            # Create a proper renderable with line breaks
            return Group(*renderables)

        # Execute sync operations with live progress
        with Live(_create_status_display(), console=self.console, refresh_per_second=4) as live:
            with ThreadPoolExecutor(max_workers=4) as executor:
                # Submit all tasks
                future_to_repo = {
                    executor.submit(_sync_repo, item): item[0]
                    for item in repo_paths.items()
                }
                # Process results as they complete
                for future in as_completed(future_to_repo):
                    repo_name = future_to_repo[future]
                    try:
                        name, outcome, reason = future.result()
                        repo_status[name]["status"] = outcome
                        repo_status[name]["message"] = reason
                        # Update the live display
                        live.update(_create_status_display())
                    except Exception as e: 
                        repo_status[repo_name]["status"] = "failed"
                        repo_status[repo_name]["message"] = f"error: {str(e)}"
                        live.update(_create_status_display())
            # after finishing, wait for user input using live.console.line()
            self.console.input()

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def get_dev_root_interactive(self) -> str:
        current_dev_root = self.repos.get_dev_root()
        if current_dev_root:
            self.console.print(f"Current dev root: [green]{current_dev_root}[/green]")
            if Confirm.ask("Use current dev root?"):
                return current_dev_root
        return Prompt.ask(
            "Enter your development root directory", default="~/dev/jazzydog-labs"
        )

    def _get_repo_context(self, repo_name: str, repo_path: str) -> dict:
        try:
            repo_path_obj = Path(repo_path)
            if not repo_path_obj.exists():
                return {"message": "Repository directory not found", "context": "Path does not exist"}
            success, stdout, _ = self.repos.git.execute_command(
                repo_path_obj, ["git", "status", "--porcelain", "--branch"]
            )
            if not success:
                return {
                    "message": "Repository is not a git repository",
                    "context": "Git status unavailable",
                }
            lines = stdout.strip().split("\n")
            if not lines:
                return {
                    "message": "Repository is clean and ready",
                    "context": "No uncommitted changes",
                }
            branch_info = ""
            ahead_behind = ""
            for line in lines:
                if line.startswith("##"):
                    if "..." in line:
                        parts = line[3:].split("...")
                        current_branch = parts[0].strip()
                        upstream_branch = parts[1].split()[0].strip()
                        branch_info = f"Branch: {current_branch} → {upstream_branch}"
                        if "[" in line and "]" in line:
                            start = line.find("[")
                            end = line.find("]")
                            ahead_behind = line[start + 1 : end]
                    else:
                        current_branch = line[3:].strip()
                        branch_info = f"Branch: {current_branch}"
                    break
            staged_files = 0
            unstaged_files = 0
            untracked_files = 0
            for line in lines[1:]:
                if line.startswith("A ") or line.startswith("M ") or line.startswith("D "):
                    staged_files += 1
                elif line.startswith(" M") or line.startswith(" D"):
                    unstaged_files += 1
                elif line.startswith("??"):
                    untracked_files += 1
            context_parts = []
            if branch_info:
                context_parts.append(branch_info)
            if ahead_behind:
                context_parts.append(ahead_behind)
            change_summary = []
            if staged_files > 0:
                change_summary.append(f"{staged_files} staged")
            if unstaged_files > 0:
                change_summary.append(f"{unstaged_files} modified")
            if untracked_files > 0:
                change_summary.append(f"{untracked_files} untracked")
            if change_summary:
                context_parts.append(f"Changes: {', '.join(change_summary)}")
            context = " | ".join(context_parts) if context_parts else "Repository loaded successfully"
            if staged_files == 0 and unstaged_files == 0 and untracked_files == 0:
                message = "Project is clean and ready for development"
            else:
                message = f"Project has {staged_files + unstaged_files + untracked_files} pending changes"
            return {"message": message, "context": context}
        except Exception as e:  # pragma: no cover - defensive
            return {"message": "Error getting repository context", "context": str(e)}

    def todos(self, root: Optional[str] = None) -> None:
        """Collect and display TODO items grouped by file and parent tasks.

        Args:
            root: Optional path to scan. Defaults to the configured dev_root or current working directory.
        """
        # Resolve root directory -------------------------------------------------
        root_path = Path(root).expanduser().resolve() if root else Path.cwd()

        # Collect todos via JSON interface --------------------------------------
        manager = TodoManager(root_path)
        try:
            todos_raw_json = cast(str, manager.collect(as_json=True))
            todos = json.loads(todos_raw_json)
        except Exception as exc:  # pragma: no cover – defensive
            self.console.print(f"[red]Error collecting TODOs:[/red] {exc}")
            return

        # Filter to pending tasks ----------------------------------------------
        pending_todos = [t for t in todos if t.get("status") != "done"]
        if not pending_todos:
            self.console.print("[green]No pending TODOs found! 🎉[/green]")
            return

        # Group by file ---------------------------------------------------------
        from collections import defaultdict
        file_groups: defaultdict[str, list[dict]] = defaultdict(list)
        for task in pending_todos:
            file_groups[task["path"]].append(task)

        # Build rich tree -------------------------------------------------------
        from rich.tree import Tree
        from rich.text import Text

        root_tree = Tree(Text("Pending TODOs", style="bold magenta"))

        def _ensure_child(parent: Tree, label: str) -> Tree:
            """Return existing child with *label* or create a new one."""
            for child in parent.children:
                # child.label may be Text or str
                if str(child.label) == label:
                    return child
            return parent.add(label)

        for path in sorted(file_groups.keys()):
            file_node = root_tree.add(Text(path, style="bold cyan"))
            # Sort tasks by line number for determinism
            for task in sorted(file_groups[path], key=lambda t: t.get("line", 0)):
                parents: list[str] = task.get("parent_task", [])  # type: ignore[arg-type]
                current_node = file_node
                for parent_desc in parents:
                    current_node = _ensure_child(current_node, parent_desc)
                # Final leaf: actual task description
                desc = task["description"]
                line_no = task.get("line")
                note = f"{desc} (L{line_no})" if line_no else desc
                current_node.add(note)

        self.console.print(root_tree)

__all__ = ["LoomController"]
