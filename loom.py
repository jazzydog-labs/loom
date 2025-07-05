#!/usr/bin/env python3
"""Loom - The central orchestrator for the foundry ecosystem."""

import sys
import logging
from pathlib import Path
from typing import Optional, List
import io
import contextlib
import typer

# Add the loomlib directory to the path
sys.path.insert(0, str(Path(__file__).parent / "loomlib"))

from loomlib.config import ConfigManager
from loomlib.git import GitManager
from loomlib.repo_manager import RepoManager

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Fallback to basic CLI
    import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize components
config_manager = ConfigManager()
git_manager = GitManager()
repo_manager = RepoManager(config_manager, git_manager)

CFG = {
    'folder': '📁',
    'dir_sep': '❯',
    'root': '.',
    'added': '✨',
    'modified': '✏️',
    'deleted': '🗑️',
    'renamed': '🔄',
    'copied': '📋',
    'unmerged': '⚠️',
    'untracked': '❓',
    'ignored': '🚫',
    'stash': '📦',
    'clean': '✨',
    'branch': '🌿',
    'file_circle': '🖊️',
    'success': '✅',
    'warning': '⚠️',
    'error': '❌',
}

if RICH_AVAILABLE:
    app = typer.Typer(help="Loom - The central orchestrator for the foundry ecosystem")
    console = Console()
else:
    # Fallback argparse setup
    parser = argparse.ArgumentParser(description="Loom - The central orchestrator for the foundry ecosystem")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')


def get_dev_root_interactive() -> str:
    """Get the development root directory interactively."""
    if RICH_AVAILABLE:
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
    else:
        current_dev_root = repo_manager.get_dev_root()
        if current_dev_root:
            print(f"Current dev root: {current_dev_root}")
            response = input("Use current dev root? (y/n): ").lower()
            if response in ['y', 'yes']:
                return current_dev_root
        
        dev_root = input("Enter your development root directory (default: ~/dev/jazzydog-labs): ")
        return dev_root or "~/dev/jazzydog-labs"


def display_status_table(statuses: dict):
    """Display repository statuses in a table."""
    if RICH_AVAILABLE:
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
    else:
        print("\nRepository Status:")
        print("-" * 80)
        for name, status in statuses.items():
            print(f"{name:15} {status['status']:10} {status.get('branch', 'N/A'):15} "
                  f"{status['ahead']}/{status['behind']:10} {status['path']}")


def display_pull_results(results: dict):
    """Display pull results."""
    if RICH_AVAILABLE:
        table = Table(title="Pull Results")
        table.add_column("Repository", style="cyan")
        table.add_column("Status", style="magenta")
        
        for name, success in results.items():
            status = "✅ Success" if success else "❌ Failed"
            color = "green" if success else "red"
            table.add_row(name, f"[{color}]{status}[/{color}]")
        
        console.print(table)
    else:
        print("\nPull Results:")
        print("-" * 40)
        for name, success in results.items():
            status = "Success" if success else "Failed"
            print(f"{name:20} {status}")


def display_detailed_status(details: dict):
    """Display detailed git status for all repositories with color coding, aligned columns, and diff statistics."""
    import re
    
    def parse_status_line(line):
        # Returns (emoji, code, filename, color)
        if line.startswith('##'):
            return (None, "BRANCH", line, "blue")
        elif line.startswith('A '):
            return (CFG['added'], "A", line[2:].strip(), "green")
        elif line.startswith('M '):
            return (CFG['file_circle'], "M", line[2:].strip(), "yellow")  # Staged
        elif line.startswith('MM'):
            return (CFG['file_circle'], "MM", line[2:].strip(), "yellow")  # Both staged and unstaged
        elif line.startswith(' M'):
            return (CFG['modified'], " M", line[2:].strip(), "yellow")  # Unstaged only
        elif line.startswith(' D'):
            return (CFG['deleted'], "D", line[2:].strip(), "red")
        elif line.startswith('R '):
            return (CFG['renamed'], "R", line[2:].strip(), "magenta")
        elif line.startswith('C '):
            return (CFG['copied'], "C", line[2:].strip(), "cyan")
        elif line.startswith('U '):
            return (CFG['unmerged'], "U", line[2:].strip(), "red")
        elif line.startswith('??'):
            return (CFG['untracked'], "??", line[2:].strip(), "white")
        elif line.startswith('!!'):
            return (CFG['ignored'], "!!", line[2:].strip(), "dim")
        elif line.startswith('stash'):
            return (CFG['stash'], "STASH", line, "blue")
        else:
            return ("", "", line, None)
    
    def get_max_filename_length(details):
        """Calculate the maximum filename length across all repositories for alignment."""
        max_length = 0
        for repo_data in details.values():
            if isinstance(repo_data, str):
                output = repo_data
            else:
                output = repo_data.get("status", "")
            
            if output.strip():
                lines = output.strip().split('\n')
                for line in lines:
                    emoji, code, rest, color = parse_status_line(line)
                    if code and code not in ["BRANCH", "STASH"]:
                        max_length = max(max_length, len(rest))
        return max_length

    def parse_branch_info(branch_line):
        # Example: '## main...origin/main' or '## main' or '## HEAD (no branch)'
        m = re.match(r"## ([^\.\s]+)(\.\.\.(\S+))?", branch_line)
        if m:
            branch = m.group(1)
            upstream = m.group(3)
            return branch, upstream
        return branch_line.replace('## ', ''), None

    if RICH_AVAILABLE:
        repo_names = list(details.keys())
        max_filename_length = get_max_filename_length(details)
        
        for idx, (name, repo_data) in enumerate(details.items()):
            if idx > 0:
                console.print()  # Only add newline between repos, not before first
            
            # Handle both old format (string) and new format (dict)
            if isinstance(repo_data, str):
                output = repo_data
                diff_stats = {}
            else:
                output = repo_data.get("status", "")
                diff_stats = repo_data.get("diff_stats", {})
            
            if output.strip():
                lines = output.strip().split('\n')
                nonempty_lines = [l for l in lines if l.strip()]
                branch_line = None
                for l in nonempty_lines:
                    if l.startswith('##'):
                        branch_line = l
                        break
                branch, upstream = parse_branch_info(branch_line) if branch_line else (None, None)
                is_clean = len(nonempty_lines) == 1 and branch_line is not None
                # Compose header
                header = f"[bold cyan]{name}"
                if is_clean:
                    header += f" {CFG['clean']} {CFG['clean']} {CFG['clean']}"
                if branch:
                    header += f"    [green]{CFG['branch']} {branch}[/green]"
                    if upstream:
                        header += f"  -> {upstream}"
                console.print(header)
                console.print("━" * (len(name) + 24))
                if not is_clean:
                    # Group files by directory and display in new format
                    files_by_dir = {}
                    stash_info = []
                    
                    for line in lines:
                        emoji, code, rest, color = parse_status_line(line)
                        if code == "BRANCH":
                            # Skip branch line since it's shown in header
                            continue
                        elif code == "STASH":
                            stash_info.append(f"{CFG['stash']} {rest}")
                        elif code and code not in ["BRANCH", "STASH"]:
                            # Group files by directory
                            if code == "MM":
                                # File has both staged and unstaged changes - show twice
                                if "/" in rest:
                                    dir_tree_key = rest.rsplit("/", 1)[0]
                                    if dir_tree_key not in files_by_dir:
                                        files_by_dir[dir_tree_key] = []
                                    # Add staged version (pen)
                                    diff_stat = diff_stats.get(rest, "")
                                    files_by_dir[dir_tree_key].append((rest, "M", diff_stat, CFG['file_circle']))
                                    # Add unstaged version (pencil)
                                    files_by_dir[dir_tree_key].append((rest, " M", diff_stat, CFG['modified']))
                                else:
                                    if "" not in files_by_dir:
                                        files_by_dir[""] = []
                                    # Add staged version (pen)
                                    diff_stat = diff_stats.get(rest, "")
                                    files_by_dir[""].append((rest, "M", diff_stat, CFG['file_circle']))
                                    # Add unstaged version (pencil)
                                    files_by_dir[""].append((rest, " M", diff_stat, CFG['modified']))
                            else:
                                # Regular file handling
                                if "/" in rest:
                                    # Handle nested directories - use full path
                                    dir_tree_key = rest.rsplit("/", 1)[0]  # Get full directory path
                                    if dir_tree_key not in files_by_dir:
                                        files_by_dir[dir_tree_key] = []
                                    # Check if this is a new directory/file
                                    diff_stat = diff_stats.get(rest, "")
                                    if diff_stat == "NEW_DIR":
                                        # Use question mark for new untracked items
                                        files_by_dir[dir_tree_key].append((rest, "??", diff_stat, CFG['untracked']))
                                    else:
                                        files_by_dir[dir_tree_key].append((rest, code, diff_stat, emoji))
                                else:
                                    # Root level files
                                    if "" not in files_by_dir:
                                        files_by_dir[""] = []
                                    # Check if this is a new directory/file
                                    diff_stat = diff_stats.get(rest, "")
                                    if diff_stat == "NEW_DIR":
                                        # Use question mark for new untracked items
                                        files_by_dir[""].append((rest, "??", diff_stat, CFG['untracked']))
                                    else:
                                        files_by_dir[""].append((rest, code, diff_stat, emoji))
                    
                    # Display grouped files with tree-like structure
                    # First, organize files by their full directory path
                    dir_tree = {}
                    for filename, code, diff_stat, emoji in files_by_dir.get("", []):
                        # Root level files
                        if "" not in dir_tree:
                            dir_tree[""] = []
                        dir_tree[""].append((filename, code, diff_stat, emoji))
                    
                    # Handle nested directories
                    for dir_name, files in files_by_dir.items():
                        if dir_name == "":
                            continue
                        dir_tree[dir_name] = files
                    
                    # Display in tree format with proper nesting
                    for dir_path in sorted(dir_tree.keys()):
                        if dir_path == "":
                            # Root level
                            dir_prefix = f"{CFG['folder']} [cyan]{CFG['root']}[/cyan] {CFG['dir_sep']}"
                        else:
                            # Nested directories - calculate indentation
                            parts = dir_path.split('/')
                            indent_level = len(parts) - 1
                            indent = "  " * indent_level  # 2 spaces per level
                            display_name = parts[-1]  # Just the last part
                            dir_prefix = f"{indent}{CFG['folder']} [cyan]{display_name}[/cyan] {CFG['dir_sep']}"
                        
                        file_parts = []
                        for filename, code, diff_stat, emoji in dir_tree[dir_path]:
                            display_name = filename.split("/")[-1] if "/" in filename else filename
                            diff_info = ""
                            if diff_stat:
                                # Color the diff stats based on file status
                                if code == "A":
                                    # Added files - show in green
                                    diff_info = f" [green]{diff_stat}[/green]"
                                else:
                                    # Modified files - color the parts
                                    parts = diff_stat.replace("|", "").split()
                                    colored_parts = []
                                    for part in parts:
                                        if part.startswith("+"):
                                            colored_parts.append(f"[green]{part}[/green]")
                                        elif part.startswith("-"):
                                            colored_parts.append(f"[red]{part}[/red]")
                                        else:
                                            colored_parts.append(part)
                                    colored_stats = " ".join(colored_parts)
                                    diff_info = f" {colored_stats}"
                            file_parts.append(f"{emoji} {display_name}{diff_info}")
                        
                        # Compose the line, wrap if too long
                        max_width = console.width if hasattr(console, 'width') else 80
                        indent = " " * (len(dir_prefix.replace('[cyan]', '').replace('[/cyan]', '')) + 1)
                        line = dir_prefix + "  "
                        for i, part in enumerate(file_parts):
                            if i > 0:
                                line += "  "
                            if len(line) + len(part) > max_width:
                                console.print(line)
                                line = indent + part
                            else:
                                line += part
                        console.print(line)
                    
                    # Display stash info if any
                    for stash_line in stash_info:
                        console.print(stash_line)
            else:
                # No output at all, treat as clean
                header = f"[bold cyan]{name} {CFG['clean']} {CFG['clean']} {CFG['clean']}[/bold cyan]"
                console.print(header)
                console.print("━" * (len(name) + 24))
                console.print(f"[green]{CFG['clean']} {CFG['clean']} {CFG['clean']} Clean repository {CFG['clean']} {CFG['clean']} {CFG['clean']}[/green]")
    else:
        repo_names = list(details.keys())
        max_filename_length = get_max_filename_length(details)
        
        for idx, (name, repo_data) in enumerate(details.items()):
            if idx > 0:
                print()  # Only add newline between repos, not before first
            
            # Handle both old format (string) and new format (dict)
            if isinstance(repo_data, str):
                output = repo_data
                diff_stats = {}
            else:
                output = repo_data.get("status", "")
                diff_stats = repo_data.get("diff_stats", {})
            
            if output.strip():
                lines = output.strip().split('\n')
                nonempty_lines = [l for l in lines if l.strip()]
                branch_line = None
                for l in nonempty_lines:
                    if l.startswith('##'):
                        branch_line = l
                        break
                branch, upstream = parse_branch_info(branch_line) if branch_line else (None, None)
                is_clean = len(nonempty_lines) == 1 and branch_line is not None
                # Compose header
                header = f"{name}"
                if is_clean:
                    header += f" {CFG['clean']} {CFG['clean']} {CFG['clean']}"
                if branch:
                    header += f"    {CFG['branch']} {branch}"
                    if upstream:
                        header += f"  -> {upstream}"
                print(header)
                print("━" * (len(name) + 24))
                if not is_clean:
                    # Group files by directory and display in new format
                    files_by_dir = {}
                    stash_info = []
                    
                    for line in lines:
                        emoji, code, rest, color = parse_status_line(line)
                        if code == "BRANCH":
                            # Skip branch line since it's shown in header
                            continue
                        elif code == "STASH":
                            stash_info.append(f"{CFG['stash']} {rest}")
                        elif code and code not in ["BRANCH", "STASH"]:
                            # Group files by directory
                            if code == "MM":
                                # File has both staged and unstaged changes - show twice
                                if "/" in rest:
                                    dir_tree_key = rest.rsplit("/", 1)[0]
                                    if dir_tree_key not in files_by_dir:
                                        files_by_dir[dir_tree_key] = []
                                    # Add staged version (pen)
                                    diff_stat = diff_stats.get(rest, "")
                                    files_by_dir[dir_tree_key].append((rest, "M", diff_stat, CFG['file_circle']))
                                    # Add unstaged version (pencil)
                                    files_by_dir[dir_tree_key].append((rest, " M", diff_stat, CFG['modified']))
                                else:
                                    if "" not in files_by_dir:
                                        files_by_dir[""] = []
                                    # Add staged version (pen)
                                    diff_stat = diff_stats.get(rest, "")
                                    files_by_dir[""].append((rest, "M", diff_stat, CFG['file_circle']))
                                    # Add unstaged version (pencil)
                                    files_by_dir[""].append((rest, " M", diff_stat, CFG['modified']))
                            else:
                                # Regular file handling
                                if "/" in rest:
                                    # Handle nested directories - use full path
                                    dir_tree_key = rest.rsplit("/", 1)[0]  # Get full directory path
                                    if dir_tree_key not in files_by_dir:
                                        files_by_dir[dir_tree_key] = []
                                    # Check if this is a new directory/file
                                    diff_stat = diff_stats.get(rest, "")
                                    if diff_stat == "NEW_DIR":
                                        # Use question mark for new untracked items
                                        files_by_dir[dir_tree_key].append((rest, "??", diff_stat, CFG['untracked']))
                                    else:
                                        files_by_dir[dir_tree_key].append((rest, code, diff_stat, emoji))
                                else:
                                    # Root level files
                                    if "" not in files_by_dir:
                                        files_by_dir[""] = []
                                    # Check if this is a new directory/file
                                    diff_stat = diff_stats.get(rest, "")
                                    if diff_stat == "NEW_DIR":
                                        # Use question mark for new untracked items
                                        files_by_dir[""].append((rest, "??", diff_stat, CFG['untracked']))
                                    else:
                                        files_by_dir[""].append((rest, code, diff_stat, emoji))
                    
                    # Display grouped files with tree-like structure
                    # First, organize files by their full directory path
                    dir_tree = {}
                    for filename, code, diff_stat, emoji in files_by_dir.get("", []):
                        # Root level files
                        if "" not in dir_tree:
                            dir_tree[""] = []
                        dir_tree[""].append((filename, code, diff_stat, emoji))
                    
                    # Handle nested directories
                    for dir_name, files in files_by_dir.items():
                        if dir_name == "":
                            continue
                        dir_tree[dir_name] = files
                    
                    # Display in tree format with proper nesting
                    for dir_path in sorted(dir_tree.keys()):
                        if dir_path == "":
                            # Root level
                            dir_prefix = f"{CFG['folder']} {dir_name} {CFG['dir_sep']}"
                        else:
                            # Nested directories - calculate indentation
                            parts = dir_path.split('/')
                            indent_level = len(parts) - 1
                            indent = "  " * indent_level  # 2 spaces per level
                            display_name = parts[-1]  # Just the last part
                            dir_prefix = f"{indent}{CFG['folder']} {display_name} {CFG['dir_sep']}"
                        
                        file_parts = []
                        for filename, code, diff_stat, emoji in dir_tree[dir_path]:
                            display_name = filename.split("/")[-1] if "/" in filename else filename
                            diff_info = ""
                            if diff_stat:
                                # Color the diff stats based on file status
                                if code == "A":
                                    # Added files - show in green
                                    diff_info = f" [green]{diff_stat}[/green]"
                                else:
                                    # Modified files - color the parts
                                    parts = diff_stat.replace("|", "").split()
                                    colored_parts = []
                                    for part in parts:
                                        if part.startswith("+"):
                                            colored_parts.append(f"[green]{part}[/green]")
                                        elif part.startswith("-"):
                                            colored_parts.append(f"[red]{part}[/red]")
                                        else:
                                            colored_parts.append(part)
                                    colored_stats = " ".join(colored_parts)
                                    diff_info = f" {colored_stats}"
                            file_parts.append(f"{emoji} {display_name}{diff_info}")
                        
                        # Compose the line, wrap if too long
                        max_width = 80
                        indent = " " * (len(dir_prefix) + 2)
                        line = dir_prefix + "  "
                        for i, part in enumerate(file_parts):
                            if i > 0:
                                line += "  "
                            if len(line) + len(part) > max_width:
                                print(line)
                                line = indent + part
                            else:
                                line += part
                        print(line)
                    
                    # Display stash info if any
                    for stash_line in stash_info:
                        print(stash_line)
            else:
                header = f"{name} {CFG['clean']} {CFG['clean']} {CFG['clean']}"
                print(header)
                print("━" * (len(name) + 24))
                print(f"{CFG['clean']} {CFG['clean']} {CFG['clean']} Clean repository {CFG['clean']} {CFG['clean']} {CFG['clean']}")


if RICH_AVAILABLE:
    @app.command()
    def init(
        dev_root: Optional[str] = typer.Option(None, "--dev-root", "-d", help="Development root directory"),
        bootstrap: bool = typer.Option(True, "--bootstrap/--no-bootstrap", help="Run foundry-bootstrap after setup")
    ):
        """Initialize the foundry ecosystem."""
        if not dev_root:
            dev_root = get_dev_root_interactive()
        
        # Expand user path
        dev_root = str(Path(dev_root).expanduser())
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Create directory structure
            task = progress.add_task("Creating directory structure...", total=None)
            success = repo_manager.create_directory_structure(dev_root)
            progress.update(task, description="✅ Directory structure created" if success else "❌ Failed to create directories")
            
            # Set dev root
            repo_manager.set_dev_root(dev_root)
            
            # Clone missing repos
            task = progress.add_task("Cloning repositories...", total=None)
            clone_results = repo_manager.clone_missing_repos(dev_root)
            success_count = sum(clone_results.values())
            total_count = len(clone_results)
            progress.update(task, description=f"✅ Cloned {success_count}/{total_count} repositories")
            
            # Move loom to foundry
            task = progress.add_task("Moving loom to foundry directory...", total=None)
            move_success = repo_manager.move_loom_to_foundry(dev_root)
            progress.update(task, description="✅ Loom moved to foundry directory" if move_success else "⚠️  Loom already in place")
            
            # Run bootstrap if requested
            if bootstrap:
                task = progress.add_task("Running foundry-bootstrap...", total=None)
                bootstrap_success = repo_manager.bootstrap_foundry(dev_root)
                progress.update(task, description="✅ Bootstrap completed" if bootstrap_success else "❌ Bootstrap failed")
        
        console.print(Panel(
            f"[green]Foundry ecosystem initialized at {dev_root}/foundry[/green]\n"
            "All repositories have been cloned and organized.",
            title="🎉 Initialization Complete"
        ))

    @app.command()
    def pull():
        """Pull latest changes for all repositories."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Pulling repositories...", total=None)
            results = repo_manager.pull_all_repos()
            progress.update(task, description="✅ Pull completed")
        
        display_pull_results(results)

    @app.command()
    def status():
        """Show status of all repositories."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Checking repository status...", total=None)
            statuses = repo_manager.get_all_status()
            progress.update(task, description="✅ Status check completed")
        
        display_status_table(statuses)

    @app.command()
    def details():
        """Show detailed git status for all repositories."""
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Getting detailed status...", total=None)
                
                # Get all repository names
                repo_names = list(repo_manager.get_repo_paths().keys())
                details = {}
                
                for name in repo_names:
                    details[name] = repo_manager.get_detailed_status(name)
                
                progress.update(task, description="✅ Detailed status completed")
        else:
            # Get all repository names
            repo_names = list(repo_manager.get_repo_paths().keys())
            details = {}
            
            for name in repo_names:
                details[name] = repo_manager.get_detailed_status(name)
        
        display_detailed_status(details)

    @app.command()
    def exec(
        command: str = typer.Argument(..., help="Command to execute in all repositories")
    ):
        """Execute a command in all repositories."""
        # Split the command string into a list
        command_parts = command.split()
        console.print(f"Executing: {' '.join(command_parts)}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Executing command...", total=None)
            results = repo_manager.execute_in_all_repos(command_parts)
            progress.update(task, description="✅ Command execution completed")
        
        # Display results
        table = Table(title="Command Execution Results")
        table.add_column("Repository", style="cyan")
        table.add_column("Success", style="magenta")
        table.add_column("Output", style="green")
        table.add_column("Error", style="red")
        
        for name, (success, stdout, stderr) in results.items():
            success_text = "✅" if success else "❌"
            color = "green" if success else "red"
            table.add_row(
                name,
                f"[{color}]{success_text}[/{color}]",
                stdout[:100] + "..." if len(stdout) > 100 else stdout,
                stderr[:100] + "..." if len(stderr) > 100 else stderr
            )
        
        console.print(table)

else:
    # Fallback argparse implementation
    def init_command(args):
        dev_root = args.dev_root or get_dev_root_interactive()
        dev_root = str(Path(dev_root).expanduser())
        
        print("Creating directory structure...")
        success = repo_manager.create_directory_structure(dev_root)
        if not success:
            print("❌ Failed to create directories")
            return
        
        repo_manager.set_dev_root(dev_root)
        
        print("Cloning repositories...")
        clone_results = repo_manager.clone_missing_repos(dev_root)
        success_count = sum(clone_results.values())
        total_count = len(clone_results)
        print(f"✅ Cloned {success_count}/{total_count} repositories")
        
        print("Moving loom to foundry directory...")
        move_success = repo_manager.move_loom_to_foundry(dev_root)
        if move_success:
            print("✅ Loom moved to foundry directory")
        else:
            print("⚠️  Loom already in place")
        
        if args.bootstrap:
            print("Running foundry-bootstrap...")
            bootstrap_success = repo_manager.bootstrap_foundry(dev_root)
            if bootstrap_success:
                print("✅ Bootstrap completed")
            else:
                print("❌ Bootstrap failed")
        
        print(f"\n🎉 Foundry ecosystem initialized at {dev_root}/foundry")
        print("All repositories have been cloned and organized.")

    def pull_command(args):
        print("Pulling repositories...")
        results = repo_manager.pull_all_repos()
        display_pull_results(results)

    def status_command(args):
        print("Checking repository status...")
        statuses = repo_manager.get_all_status()
        display_status_table(statuses)

    def details_command(args):
        # Get all repository names
        repo_names = list(repo_manager.get_repo_paths().keys())
        details = {}
        
        for name in repo_names:
            details[name] = repo_manager.get_detailed_status(name)
        
        display_detailed_status(details)

    def exec_command(args):
        print(f"Executing: {' '.join(args.command)}")
        results = repo_manager.execute_in_all_repos(args.command)
        
        print("\nCommand Execution Results:")
        print("-" * 80)
        for name, (success, stdout, stderr) in results.items():
            success_text = "✅" if success else "❌"
            print(f"{name:15} {success_text}")
            if stdout:
                print(f"  Output: {stdout[:100]}{'...' if len(stdout) > 100 else ''}")
            if stderr:
                print(f"  Error: {stderr[:100]}{'...' if len(stderr) > 100 else ''}")

    # Set up subparsers
    init_parser = subparsers.add_parser('init', help='Initialize the foundry ecosystem')
    init_parser.add_argument('--dev-root', '-d', help='Development root directory')
    init_parser.add_argument('--bootstrap', action='store_true', default=True, help='Run foundry-bootstrap after setup')
    init_parser.add_argument('--no-bootstrap', dest='bootstrap', action='store_false', help='Skip foundry-bootstrap')
    init_parser.set_defaults(func=init_command)
    
    subparsers.add_parser('pull', help='Pull latest changes for all repositories').set_defaults(func=pull_command)
    subparsers.add_parser('status', help='Show status of all repositories').set_defaults(func=status_command)
    subparsers.add_parser('details', help='Show detailed git status for all repositories').set_defaults(func=details_command)
    
    exec_parser = subparsers.add_parser('exec', help='Execute a command in all repositories')
    exec_parser.add_argument('command', nargs='+', help='Command to execute')
    exec_parser.set_defaults(func=exec_command)


def main():
    """Main entry point."""
    if RICH_AVAILABLE:
        # If no arguments provided, show commands (if enabled) then status by default
        if len(sys.argv) == 1:
            # Check if we should show available commands
            if config_manager.get_display_config('show_commands_on_status', False):
                console.print("\n" + "="*50)
                console.print("[bold cyan]Available Commands:[/bold cyan]")
                console.print("="*50)
                # Capture help text without exiting
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    try:
                        app(['--help'])
                    except SystemExit:
                        pass
                help_text = buf.getvalue()
                console.print(help_text)
            status()
        else:
            app()
    else:
        args = parser.parse_args()
        if hasattr(args, 'func'):
            args.func(args)
        else:
            # Show commands (if enabled) then status by default when no command provided
            if config_manager.get_display_config('show_commands_on_status', False):
                print("\n" + "="*50)
                print("Available Commands:")
                print("="*50)
                parser.print_help()
            status_command(args)


if __name__ == "__main__":
    main() 