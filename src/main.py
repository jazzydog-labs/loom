#!/usr/bin/env python3
"""Main loom application."""

import sys
import logging
from pathlib import Path
from typing import Optional, List
import io
import contextlib

# Add the loomlib directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "loomlib"))

from loomlib.config import ConfigManager
from loomlib.git import GitManager
from loomlib.repo_manager import RepoManager

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    import typer
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

if RICH_AVAILABLE:
    app = typer.Typer(help="Loom - The central orchestrator for the foundry ecosystem")
    console = Console()
else:
    # Fallback argparse setup
    parser = argparse.ArgumentParser(description="Loom - The central orchestrator for the foundry ecosystem")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')


def main():
    """Main entry point."""
    if RICH_AVAILABLE:
        # If no arguments provided, show commands (if enabled) then status then details by default
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
            
            # Show status
            console.print("\n" + "═"*50)
            console.print("[bold cyan]Repository Status:[/bold cyan]")
            console.print("═"*50)
            show_status()
            
            # Show details
            console.print("\n" + "═"*50)
            console.print("[bold cyan]Detailed Status:[/bold cyan]")
            console.print("═"*50)
            show_details()
        else:
            app()
    else:
        args = parser.parse_args()
        if hasattr(args, 'func'):
            args.func(args)
        else:
            # Show commands (if enabled) then status then details by default when no command provided
            if config_manager.get_display_config('show_commands_on_status', False):
                print("\n" + "═"*50)
                print("Available Commands:")
                print("═"*50)
                parser.print_help()
            
            # Show status
            print("\n" + "═"*50)
            print("Repository Status:")
            print("═"*50)
            show_status()
            
            # Show details
            print("\n" + "═"*50)
            print("Detailed Status:")
            print("═"*50)
            show_details()


def show_status():
    """Show status of all repositories."""
    statuses = repo_manager.get_all_status()
    display_status_table(statuses)


def show_details():
    """Show detailed status of all repositories."""
    # Get all repository names
    repo_names = list(repo_manager.get_repo_paths().keys())
    details = {}
    
    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Getting detailed status...", total=None)
            
            for name in repo_names:
                details[name] = repo_manager.get_detailed_status(name)
            
            progress.update(task, description="✅ Detailed status completed")
    else:
        for name in repo_names:
            details[name] = repo_manager.get_detailed_status(name)
    
    display_detailed_status(details)


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
                    if line.startswith('##'):
                        continue
                    # Extract filename from status line
                    parts = line.split()
                    if len(parts) >= 2:
                        filename = parts[-1]  # Last part is usually the filename
                        max_length = max(max_length, len(filename))
        return max_length
    
    def parse_branch_info(branch_line):
        # Example: '## main...origin/main' or '## main' or '## HEAD (no branch)'
        if '...' in branch_line:
            current, upstream = branch_line[3:].split('...')
            return current.strip(), upstream.strip()
        else:
            current = branch_line[3:].strip()
            return current, None
    
    def parse_diff_stats(diff_output):
        """Parse git diff --stat output to extract line counts."""
        if not diff_output:
            return {}
        
        stats = {}
        lines = diff_output.strip().split('\n')
        
        for line in lines:
            # Look for lines like " 1 file changed, 1 insertion(+), 1 deletion(-)"
            if 'file changed' in line:
                continue
            
            # Look for lines like " src/main.py | 10 +++++-----"
            if '|' in line:
                parts = line.split('|')
                if len(parts) == 2:
                    filename = parts[0].strip()
                    stat_part = parts[1].strip()
                    
                    # Extract numbers from stat part
                    # Example: " 10 +++++-----" -> +10, -5
                    additions = stat_part.count('+')
                    deletions = stat_part.count('-')
                    
                    if additions > 0 or deletions > 0:
                        stats[filename] = f"+{additions} -{deletions}"
        
        return stats
    
    # Configuration for emojis
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
    
    max_filename_length = get_max_filename_length(details)
    
    if RICH_AVAILABLE:
        for repo_name, repo_data in details.items():
            if isinstance(repo_data, str):
                output = repo_data
            else:
                output = repo_data.get("status", "")
            
            if not output.strip():
                continue
            
            lines = output.strip().split('\n')
            if not lines:
                continue
            
            # Parse branch info from first line
            branch_line = lines[0]
            if branch_line.startswith('##'):
                current_branch, upstream_branch = parse_branch_info(branch_line)
                
                # Create header with branch info
                if upstream_branch:
                    header = f"{repo_name} {CFG['branch']} {current_branch}...{upstream_branch}"
                else:
                    header = f"{repo_name} {CFG['branch']} {current_branch}"
                
                console.print(f"\n[bold cyan]{header}[/bold cyan]")
                
                # Check if repo is clean
                if len(lines) == 1:
                    console.print(f"  {CFG['clean']} Clean repository")
                    continue
                
                # Group files by directory
                files_by_dir = {}
                current_dir = ""
                
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    
                    emoji, code, filename, color = parse_status_line(line)
                    if not emoji:
                        continue
                    
                    # Extract directory and filename
                    if '/' in filename:
                        dir_part, file_part = filename.rsplit('/', 1)
                        if dir_part not in files_by_dir:
                            files_by_dir[dir_part] = []
                        files_by_dir[dir_part].append((emoji, file_part, color))
                    else:
                        if "" not in files_by_dir:
                            files_by_dir[""] = []
                        files_by_dir[""].append((emoji, filename, color))
                
                # Display files grouped by directory
                for directory, files in files_by_dir.items():
                    if directory:
                        console.print(f"  {CFG['folder']} {directory} {CFG['dir_sep']}")
                        indent = "    "
                    else:
                        indent = "  "
                    
                    # Group files on the same line
                    file_line = []
                    for emoji, filename, color in files:
                        file_line.append(f"{emoji} {filename}")
                    
                    # Join files with spaces
                    console.print(f"{indent}{' '.join(file_line)}")
                
                console.print("")  # Empty line between repos
            else:
                console.print(f"\n[bold cyan]{repo_name}[/bold cyan]")
                console.print(f"  {CFG['error']} Error getting status")
                console.print("")
    else:
        # Plain text version
        for repo_name, repo_data in details.items():
            if isinstance(repo_data, str):
                output = repo_data
            else:
                output = repo_data.get("status", "")
            
            if not output.strip():
                continue
            
            lines = output.strip().split('\n')
            if not lines:
                continue
            
            # Parse branch info from first line
            branch_line = lines[0]
            if branch_line.startswith('##'):
                current_branch, upstream_branch = parse_branch_info(branch_line)
                
                # Create header with branch info
                if upstream_branch:
                    header = f"{repo_name} {current_branch}...{upstream_branch}"
                else:
                    header = f"{repo_name} {current_branch}"
                
                print(f"\n{header}")
                print("═" * len(header))
                
                # Check if repo is clean
                if len(lines) == 1:
                    print("  ✨ Clean repository")
                    continue
                
                # Group files by directory
                files_by_dir = {}
                
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    
                    emoji, code, filename, color = parse_status_line(line)
                    if not emoji:
                        continue
                    
                    # Extract directory and filename
                    if '/' in filename:
                        dir_part, file_part = filename.rsplit('/', 1)
                        if dir_part not in files_by_dir:
                            files_by_dir[dir_part] = []
                        files_by_dir[dir_part].append((emoji, file_part))
                    else:
                        if "" not in files_by_dir:
                            files_by_dir[""] = []
                        files_by_dir[""].append((emoji, filename))
                
                # Display files grouped by directory
                for directory, files in files_by_dir.items():
                    if directory:
                        print(f"  📁 {directory} ❯")
                        indent = "    "
                    else:
                        indent = "  "
                    
                    # Group files on the same line
                    file_line = []
                    for emoji, filename in files:
                        file_line.append(f"{emoji} {filename}")
                    
                    # Join files with spaces
                    print(f"{indent}{' '.join(file_line)}")
                
                print("")  # Empty line between repos
            else:
                print(f"\n{repo_name}")
                print("  ❌ Error getting status")
                print("")


# Create a separate app for the 'do' commands
if RICH_AVAILABLE:
    do_app = typer.Typer(help="Run a named operation in all repositories (e.g., test, build, docs, git, etc)")
    
    # Import git commands from the new location
    from commands.git.commands import create_git_app
    
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
            console.print("❌ Failed to create directories")
            return
        
        repo_manager.set_dev_root(dev_root)
        
        console.print("Cloning repositories...")
        clone_results = repo_manager.clone_missing_repos(dev_root)
        success_count = sum(clone_results.values())
        total_count = len(clone_results)
        console.print(f"✅ Cloned {success_count}/{total_count} repositories")
        
        console.print("Moving loom to foundry directory...")
        move_success = repo_manager.move_loom_to_foundry(dev_root)
        if move_success:
            console.print("✅ Loom moved to foundry directory")
        else:
            console.print("⚠️  Loom already in place")
        
        if bootstrap:
            console.print("Running foundry-bootstrap...")
            bootstrap_success = repo_manager.bootstrap_foundry(dev_root)
            if bootstrap_success:
                console.print("✅ Bootstrap completed")
            else:
                console.print("❌ Bootstrap failed")
        
        console.print(f"\n🎉 Foundry ecosystem initialized at {dev_root}/foundry")
        console.print("All repositories have been cloned and organized.")

    @app.command()
    def pull_all():
        """Pull latest changes for all repositories."""
        console.print("Pulling repositories...")
        results = repo_manager.pull_all_repos()
        display_pull_results(results)

    @app.command()
    def status_all():
        """Show status of all repositories."""
        show_status()

    @app.command()
    def details():
        """Show detailed git status for all repositories."""
        show_details()

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
        show_status()

    def details_command(args):
        show_details()

    # Set up subparsers
    init_parser = subparsers.add_parser('init', help='Initialize the foundry ecosystem')
    init_parser.add_argument('--dev-root', '-d', help='Development root directory')
    init_parser.add_argument('--bootstrap', action='store_true', default=True, help='Run foundry-bootstrap after setup')
    init_parser.add_argument('--no-bootstrap', dest='bootstrap', action='store_false', help='Skip foundry-bootstrap')
    init_parser.set_defaults(func=init_command)
    
    subparsers.add_parser('pull', help='Pull latest changes for all repositories').set_defaults(func=pull_command)
    subparsers.add_parser('status', help='Show status of all repositories').set_defaults(func=status_command)
    subparsers.add_parser('details', help='Show detailed git status for all repositories').set_defaults(func=details_command)


if __name__ == "__main__":
    main() 