"""Git commands for loom."""

import sys
from pathlib import Path
from typing import Optional

# Add the loomlib directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "loomlib"))

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
    app = typer.Typer(help="Git operations for all repositories")
    console = Console()


@app.command()
def add():
    """Add all files in all repositories."""
    console.print("Adding all files in all repositories...")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Adding files...", total=None)
        results = repo_manager.add_all_files()
        progress.update(task, description="✅ Add completed")
    
    # Display results
    table = Table(title="Add Results")
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
    """Commit all changes in all repositories."""
    console.print(f"Committing with message: {message}")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Committing...", total=None)
        results = repo_manager.commit_all(message)
        progress.update(task, description="✅ Commit completed")
    
    # Display results
    table = Table(title="Commit Results")
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
    """Push all repositories."""
    console.print("Pushing all repositories...")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Pushing...", total=None)
        results = repo_manager.push_all()
        progress.update(task, description="✅ Push completed")
    
    # Display results
    table = Table(title="Push Results")
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
    """Pull all repositories."""
    console.print("Pulling all repositories...")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Pulling...", total=None)
        results = repo_manager.pull_all()
        progress.update(task, description="✅ Pull completed")
    
    # Display results
    table = Table(title="Pull Results")
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
    """Get status of all repositories."""
    console.print("Getting status of all repositories...")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Getting status...", total=None)
        results = repo_manager.status_all()
        progress.update(task, description="✅ Status completed")
    
    # Display results
    table = Table(title="Status Results")
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


if __name__ == "__main__":
    app() 