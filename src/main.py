#!/usr/bin/env python3
"""Main loom application."""

import sys
import os
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
import io
import contextlib
import json

# Initialize rich console
console = Console()

# Initialize Typer app
app = typer.Typer()

# Import our modules
from .core.config import ConfigManager
from .core.git import GitManager
from .core.repo_manager import RepoManager
from .utils.color_manager import ColorManager
from .utils.emojis import get_emoji_manager
from .utils.repo_status_reader import RepoStatusReader
from .views.repo_view import RepoView
from .commands.git.commands import create_git_app

# Initialize managers
config_manager = ConfigManager()
git_manager = GitManager()
repo_manager = RepoManager(config_manager, git_manager)
color_manager = ColorManager()
emoji_mgr = get_emoji_manager()

def main():
    """Main entry point."""
    # If no arguments provided, show commands (if enabled) then details by default
    if len(sys.argv) == 1:
        # Check if we should show available commands
        if config_manager.get_display_config('show_commands_on_status', False):
            console.print("\n" + "═"*50)
            console.print("[bold cyan]Available Commands:[/bold cyan]")
            console.print("═"*50)
            # Capture help text without exiting
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                try:
                    app(['--help'])
                except SystemExit:
                    pass
            help_text = buf.getvalue()
            console.print(help_text)
        
        # Show details
        show_details()
    else:
        app()


def show_status():
    """Show status of all repositories."""
    statuses = repo_manager.get_all_status()
    display_status_table(statuses)

def show_details():
    """Show detailed status of all repositories."""
    # Get all repository configurations
    repos_config = config_manager.load_repos()
    repos = repos_config.get('repos', [])
    
    if not repos:
        console.print("No repositories configured.")
        return
    
    # Get dev_root and foundry_dir for path resolution
    dev_root = config_manager.get_dev_root()
    foundry_dir = config_manager.get_foundry_dir()
    
    if not dev_root:
        console.print("Development root not configured. Please run 'loom init' first.")
        return
    
    # Build mapping of repo names to absolute paths
    repo_paths = {
        repo['name']: repo['path'].replace('$DEV_ROOT', dev_root).replace('$FOUNDRY_DIR', foundry_dir)
        for repo in repos
    }

    # Fetch summaries in parallel using RepoStatusReader helper
    repos_data = RepoStatusReader.summaries_parallel(repo_paths)

    # Display using RepoView (sequential display)
    repo_view = RepoView(console)
    repo_view.display_multiple_repos(repos_data)


def get_dev_root_interactive() -> str:
    """Get the development root directory interactively."""
    current_dev_root = repo_manager.get_dev_root()
    if current_dev_root:
        console.print(f"Current dev root: [green]{current_dev_root}[/green]")
        if Confirm.ask("Use current dev root?"):
            return current_dev_root
    
    dev_root = Prompt.ask(
        "Enter your development root directory",
        default="~/dev/jazzydog-labs"
    )
    return dev_root


def display_status_table(statuses: dict):
    """Display repository statuses in a table."""
    table = Table(title="Repository Status")
    table.add_column("Repository", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Branch", style="green")
    table.add_column("Ahead/Behind", style="yellow")
    table.add_column("Path", style="dim")
    
    for name, status in statuses.items():
        status_color = {
            "clean": "green",
            "dirty": "red",
            "missing": "red",
            "not_git": "yellow",
            "error": "red"
        }.get(status["status"], "white")
        
        ahead_behind = f"{status['ahead']}/{status['behind']}"
        
        table.add_row(
            name,
            f"[{status_color}]{status['status']}[/{status_color}]",
            status.get("branch", "N/A"),
            ahead_behind,
            status["path"]
        )
    
    console.print(table)


def display_pull_results(results: dict):
    """Display pull results."""
    table = Table(title="Pull Results")
    table.add_column("Repository", style="cyan")
    table.add_column("Status", style="magenta")
    
    for name, success in results.items():
        status = f"{emoji_mgr.get_status('success')} Success" if success else f"{emoji_mgr.get_status('error')} Failed"
        color = "green" if success else "red"
        table.add_row(name, f"[{color}]{status}[/{color}]")
    
    console.print(table)





# Create a separate app for the 'do' commands
do_app = typer.Typer(help="Run a named operation in all repositories (e.g., test, build, docs, git, etc)")


# Add the git app as a subcommand
do_app.add_typer(create_git_app(), name="git")

# Add the do app as a subcommand
app.add_typer(do_app, name="do")

@app.command()
def init(
    dev_root: Optional[str] = typer.Option(None, "--dev-root", "-d", help="Development root directory"),
    bootstrap: bool = typer.Option(True, "--bootstrap/--no-bootstrap", help="Run foundry-bootstrap after setup")
):
    """Initialize the foundry ecosystem."""
    dev_root = dev_root or get_dev_root_interactive()
    dev_root = str(Path(dev_root).expanduser())
    
    console.print("Creating directory structure...")
    success = repo_manager.create_directory_structure(dev_root)
    if not success:
        console.print(f"{emoji_mgr.get_status('error')} Failed to create directories")
        return
    
    repo_manager.set_dev_root(dev_root)
    
    console.print("Cloning repositories...")
    clone_results = repo_manager.clone_missing_repos(dev_root)
    success_count = sum(clone_results.values())
    total_count = len(clone_results)
    console.print(f"{emoji_mgr.get_status('success')} Cloned {success_count}/{total_count} repositories")
    
    console.print("Moving loom to foundry directory...")
    move_success = repo_manager.move_loom_to_foundry(dev_root)
    if move_success:
        console.print(f"{emoji_mgr.get_status('success')} Loom moved to foundry directory")
    else:
        console.print(f"{emoji_mgr.get_status('warning')} Loom already in place")
    
    if bootstrap:
        console.print("Running foundry-bootstrap...")
        bootstrap_success = repo_manager.bootstrap_foundry(dev_root)
        if bootstrap_success:
            console.print(f"{emoji_mgr.get_status('success')} Bootstrap completed")
        else:
            console.print(f"{emoji_mgr.get_status('error')} Bootstrap failed")
    
    console.print(f"\n🎉 Foundry ecosystem initialized at {dev_root}/foundry")
    console.print("All repositories have been cloned and organized.")

@app.command()
def pull_all():
    """Pull latest changes for all repositories."""
    console.print("Pulling repositories...")
    results = repo_manager.pull_all_repos()
    display_pull_results(results)

@app.command()
def details():
    """Show detailed git status for all repositories."""
    show_details()

@app.command()
def go(
    repo_name: Optional[str] = typer.Argument(None, help="Repository name to enter directly"),
    output_command: bool = typer.Option(False, "--output-command", "-o", help="Output only the cd command")
):
    """Enter a repository with context loaded."""
    from fuzzywuzzy import fuzz, process
    import subprocess
    
    # Get all repository names
    repo_names = list(repo_manager.get_repo_paths().keys())
    
    if not repo_names:
        if output_command:
            print("echo 'No repositories found'")
        else:
            print(json.dumps({
                "error": "No repositories found",
                "directory": None,
                "message": None,
                "context": None
            }))
        return
    
    selected_repo = None
    
    # If repo name provided directly, use fuzzy matching
    if repo_name:
        # First, try exact prefix matching (case-insensitive)
        prefix_matches = [name for name in repo_names if name.lower().startswith(repo_name.lower())]
        
        if len(prefix_matches) == 1:
            # Single prefix match - use it
            selected_repo = prefix_matches[0]
        elif len(prefix_matches) > 1:
            # Multiple prefix matches - use fzf for selection
            try:
                # Check if fzf is available
                subprocess.run(["fzf", "--version"], capture_output=True, check=True)
                
                # Create the fzf command with the input as initial query
                fzf_cmd = ["fzf", "--prompt", "Select repository: ", "--height", "40%", "--query", repo_name]
                
                # Run fzf with matching repository names as input
                result = subprocess.run(
                    fzf_cmd,
                    input="\n".join(prefix_matches),
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    selected_repo = result.stdout.strip()
                else:
                    # User cancelled fzf
                    return
                    
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback to fuzzy matching if fzf not available
                best_match = process.extractOne(repo_name, prefix_matches, scorer=fuzz.ratio)
                if best_match and best_match[1] >= 30:  # Lower threshold for prefix matches
                    selected_repo = best_match[0]
                else:
                    if output_command:
                        print(f"echo 'Repository {repo_name} not found'")
                    else:
                        print(json.dumps({
                            "error": f"Repository '{repo_name}' not found",
                            "directory": None,
                            "message": None,
                            "context": None
                        }))
                    return
        else:
            # No prefix matches, try fuzzy matching with lower threshold
            best_match = process.extractOne(repo_name, repo_names, scorer=fuzz.ratio)
            if best_match and best_match[1] >= 40:  # Lower threshold for fuzzy matching
                selected_repo = best_match[0]
            else:
                if output_command:
                    print(f"echo 'Repository {repo_name} not found'")
                else:
                    print(json.dumps({
                        "error": f"Repository '{repo_name}' not found",
                        "directory": None,
                        "message": None,
                        "context": None
                    }))
                return
    else:
        # Use fzf for interactive fuzzy selection
        try:
            # Check if fzf is available
            subprocess.run(["fzf", "--version"], capture_output=True, check=True)
            
            # Create the fzf command
            fzf_cmd = ["fzf", "--prompt", "Select repository: ", "--height", "40%"]
            
            # Run fzf with repository names as input
            result = subprocess.run(
                fzf_cmd,
                input="\n".join(repo_names),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                selected_repo = result.stdout.strip()
            else:
                # User cancelled fzf
                return
                
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(json.dumps({
                "error": "fzf is not installed. Please run foundry-bootstrap/bootstrap.sh to install all dependencies.",
                "directory": None,
                "message": None,
                "context": None
            }))
            return
    
    # Get repo path
    repo_paths = repo_manager.get_repo_paths()
    repo_path = repo_paths[selected_repo]
    
    # Get repository context
    context = get_repo_context(selected_repo, repo_path)
    
    if output_command:
        # Just output the cd command for sourcing
        print(f"cd {repo_path}")
        return
    else:
        # Output JSON with context
        result = {
            "directory": repo_path,
            "message": context.get("message", "Project is active and ready for development"),
            "context": context.get("context", "Repository loaded successfully")
        }
        print(json.dumps(result, indent=2))
        return


def get_repo_context(repo_name: str, repo_path: str) -> dict:
    """Get context information for a repository."""
    try:
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            return {
                "message": "Repository directory not found",
                "context": "Path does not exist"
            }
        
        # Get git status
        success, stdout, stderr = repo_manager.git.execute_command(
            repo_path_obj, 
            ["git", "status", "--porcelain", "--branch"]
        )
        
        if not success:
            return {
                "message": "Repository is not a git repository",
                "context": "Git status unavailable"
            }
        
        # Parse git status for context
        lines = stdout.strip().split('\n')
        if not lines:
            return {
                "message": "Repository is clean and ready",
                "context": "No uncommitted changes"
            }
        
        # Parse branch info
        branch_info = ""
        ahead_behind = ""
        for line in lines:
            if line.startswith('##'):
                # Extract branch and ahead/behind info
                if '...' in line:
                    parts = line[3:].split('...')
                    current_branch = parts[0].strip()
                    upstream_branch = parts[1].split()[0].strip()
                    branch_info = f"Branch: {current_branch} → {upstream_branch}"
                    
                    # Extract ahead/behind
                    if '[' in line and ']' in line:
                        start = line.find('[')
                        end = line.find(']')
                        ahead_behind = line[start+1:end]
                else:
                    current_branch = line[3:].strip()
                    branch_info = f"Branch: {current_branch}"
                break
        
        # Count changes
        staged_files = 0
        unstaged_files = 0
        untracked_files = 0
        
        for line in lines[1:]:  # Skip branch line
            if line.startswith('A ') or line.startswith('M ') or line.startswith('D '):
                staged_files += 1
            elif line.startswith(' M') or line.startswith(' D'):
                unstaged_files += 1
            elif line.startswith('??'):
                untracked_files += 1
        
        # Build context message
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
        
        # Build message
        if staged_files == 0 and unstaged_files == 0 and untracked_files == 0:
            message = "Project is clean and ready for development"
        else:
            message = f"Project has {staged_files + unstaged_files + untracked_files} pending changes"
        
        return {
            "message": message,
            "context": context
        }
        
    except Exception as e:
        return {
            "message": "Error getting repository context",
            "context": str(e)
        }

if __name__ == "__main__":
    main() 