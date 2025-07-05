#!/usr/bin/env python3
"""Loom - The central orchestrator for the foundry ecosystem."""

import sys
import logging
from pathlib import Path
from typing import Optional
import io
import contextlib
import typer.main

# Add the loomlib directory to the path
sys.path.insert(0, str(Path(__file__).parent / "loomlib"))

from loomlib.config import ConfigManager
from loomlib.git import GitManager
from loomlib.repo_manager import RepoManager

try:
    import typer
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
    """Display detailed git status for all repositories with color coding and aligned columns."""
    def parse_status_line(line):
        # Returns (emoji, code, filename, color)
        if line.startswith('##'):
            return ("🌿", "BRANCH", line, "blue")
        elif line.startswith('A '):
            return ("✓", "A", line[2:].strip(), "green")
        elif line.startswith('M '):
            return ("●", "M", line[2:].strip(), "yellow")
        elif line.startswith(' D'):
            return ("✗", "D", line[2:].strip(), "red")
        elif line.startswith('R '):
            return ("↔", "R", line[2:].strip(), "magenta")
        elif line.startswith('C '):
            return ("📋", "C", line[2:].strip(), "cyan")
        elif line.startswith('U '):
            return ("⚠", "U", line[2:].strip(), "red")
        elif line.startswith(' M'):
            return ("○", "M", line[2:].strip(), "yellow")
        elif line.startswith(' D'):
            return ("○", "D", line[2:].strip(), "red")
        elif line.startswith('??'):
            return ("?", "??", line[2:].strip(), "white")
        elif line.startswith('!!'):
            return ("!", "!!", line[2:].strip(), "dim")
        elif line.startswith('stash'):
            return ("📦", "STASH", line, "blue")
        else:
            return ("", "", line, None)

    if RICH_AVAILABLE:
        repo_names = list(details.keys())
        for idx, (name, output) in enumerate(details.items()):
            if idx > 0:
                console.print()  # Only add newline between repos, not before first
            console.print(f"[bold cyan]{name}[/bold cyan]")
            console.print("=" * (len(name) + 2))
            if output.strip():
                lines = output.strip().split('\n')
                for line in lines:
                    emoji, code, rest, color = parse_status_line(line)
                    if code == "BRANCH":
                        console.print(f"[blue]{rest}[/blue]")
                    elif code == "STASH":
                        console.print(f"[blue]{emoji} {rest}[/blue]")
                    elif code:
                        # Align columns: emoji, code, filename
                        console.print(f"[{color}]{emoji:<2} {code:<3} {rest}[/]")
                    else:
                        console.print(rest)
            else:
                console.print("[dim]✨ No changes[/dim]")
    else:
        repo_names = list(details.keys())
        for idx, (name, output) in enumerate(details.items()):
            if idx > 0:
                print()  # Only add newline between repos, not before first
            print(f"{name}")
            print("=" * (len(name) + 2))
            if output.strip():
                lines = output.strip().split('\n')
                for line in lines:
                    emoji, code, rest, color = parse_status_line(line)
                    if code == "BRANCH":
                        print(f"🌿 {rest}")
                    elif code == "STASH":
                        print(f"📦 {rest}")
                    elif code:
                        print(f"{emoji:<2} {code:<3} {rest}")
                    else:
                        print(rest)
            else:
                print("✨ No changes")


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
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Getting detailed status...", total=None)
            details = repo_manager.get_detailed_status()
            progress.update(task, description="✅ Detailed status completed")
        
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
        print("Getting detailed repository status...")
        details = repo_manager.get_detailed_status()
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