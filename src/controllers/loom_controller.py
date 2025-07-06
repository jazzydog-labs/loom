"""Controller implementing loom operations."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import contextlib
import io
import json
import subprocess

from rich.console import Console
from rich.prompt import Prompt, Confirm

from ..core.config import ConfigManager
from ..core.git import GitManager
from ..core.repo_manager import RepoManager
from ..utils.emojis import get_emoji_manager
from ..utils.repo_status_reader import RepoStatusReader
from ..views.repo_view import RepoView


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

        repos_data = RepoStatusReader.summaries_parallel(repo_paths)
        RepoView(self.console).display_multiple_repos(repos_data)

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
                try:
                    subprocess.run(["fzf", "--version"], capture_output=True, check=True)
                    fzf_cmd = ["fzf", "--prompt", "Select repository: ", "--height", "40%", "--query", repo_name]
                    result = subprocess.run(
                        fzf_cmd, input="\n".join(prefix_matches), capture_output=True, text=True
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        selected_repo = result.stdout.strip()
                    else:
                        return
                except (subprocess.CalledProcessError, FileNotFoundError):
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
            try:
                subprocess.run(["fzf", "--version"], capture_output=True, check=True)
                fzf_cmd = ["fzf", "--prompt", "Select repository: ", "--height", "40%"]
                result = subprocess.run(
                    fzf_cmd, input="\n".join(repo_names), capture_output=True, text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    selected_repo = result.stdout.strip()
                else:
                    return
            except (subprocess.CalledProcessError, FileNotFoundError):
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

__all__ = ["LoomController"]
