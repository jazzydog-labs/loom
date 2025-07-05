"""Git commands for loom do operations."""

import sys
from pathlib import Path
from typing import Optional

# Add the loomlib directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "loomlib"))

from loomlib.config import ConfigManager
from loomlib.git import GitManager
from loomlib.repo_manager import RepoManager

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    import typer
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Initialize components
config_manager = ConfigManager()
git_manager = GitManager()
repo_manager = RepoManager(config_manager, git_manager)

if RICH_AVAILABLE:
    console = Console()


def create_git_app():
    """Create and return the git commands Typer app."""
    app = typer.Typer(help="Git operations for all repositories")
    
    @app.command()
    def add():
        """Run the 'add' operation in all repositories. (Example: add files, dependencies, etc)"""
        console.print("Running 'add' operation in all repositories...")
        # This is a placeholder for a generic add operation. In a real implementation, this could add files, dependencies, etc.
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running add...", total=None)
            results = repo_manager.add_all_files()  # This currently adds all files via git, but could be extended.
            progress.update(task, description="✅ Add operation completed")
        
        # Display results
        table = Table(title="Add Operation Results")
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

    @app.command()
    def commit(
        message: str = typer.Argument(..., help="Commit message")
    ):
        """Run the 'commit' operation in all repositories. (Example: commit changes, checkpoint, etc)"""
        console.print(f"Running 'commit' operation in all repositories with message: {message}")
        # This is a placeholder for a generic commit operation. In a real implementation, this could commit changes, checkpoint, etc.
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running commit...", total=None)
            results = repo_manager.commit_all(message)  # This currently commits via git, but could be extended.
            progress.update(task, description="✅ Commit operation completed")
        
        # Display results
        table = Table(title="Commit Operation Results")
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

    @app.command()
    def push():
        """Run the 'push' operation in all repositories. (Example: push changes, publish, etc)"""
        console.print("Running 'push' operation in all repositories...")
        # This is a placeholder for a generic push operation. In a real implementation, this could push changes, publish, etc.
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running push...", total=None)
            results = repo_manager.push_all()  # This currently pushes via git, but could be extended.
            progress.update(task, description="✅ Push operation completed")
        
        # Display results
        table = Table(title="Push Operation Results")
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

    @app.command()
    def pull():
        """Run the 'pull' operation in all repositories. (Example: pull changes, sync, etc)"""
        console.print("Running 'pull' operation in all repositories...")
        # This is a placeholder for a generic pull operation. In a real implementation, this could pull changes, sync, etc.
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running pull...", total=None)
            results = repo_manager.pull_all()  # This currently pulls via git, but could be extended.
            progress.update(task, description="✅ Pull operation completed")
        
        # Display results
        table = Table(title="Pull Operation Results")
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

    @app.command()
    def status():
        """Run the 'status' operation in all repositories. (Example: check status, health, etc)"""
        console.print("Running 'status' operation in all repositories...")
        # This is a placeholder for a generic status operation. In a real implementation, this could check status, health, etc.
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running status...", total=None)
            results = repo_manager.status_all()  # This currently checks git status, but could be extended.
            progress.update(task, description="✅ Status operation completed")
        
        # Display results
        table = Table(title="Status Operation Results")
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

    return app 