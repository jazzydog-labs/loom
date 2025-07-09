"""Typer CLI mapping commands to the LoomController."""

from typing import Optional
import typer
from rich.console import Console

from ..app.loom_controller import LoomController

app = typer.Typer()
console = Console()
controller = LoomController(console=console)


@app.command()
def status() -> None:
    """Show aggregated repository status."""
    typer.echo(controller.status())


@app.command()
def init(
    dev_root: Optional[str] = typer.Option(
        None, "--dev-root", "-d", help="Development root directory"
    ),
    bootstrap: bool = typer.Option(
        True,
        "--bootstrap/--no-bootstrap",
        help="Run foundry-bootstrap after setup",
    ),
) -> None:
    """Initialize the foundry ecosystem."""
    controller.init(dev_root, bootstrap)


@app.command()
def details() -> None:
    """Show detailed git status for all repositories."""
    controller.show_details()


@app.command()
def go(
    repo_name: Optional[str] = typer.Argument(
        None, help="Repository name to enter directly"
    ),
    output_command: bool = typer.Option(
        False,
        "--output-command",
        "-o",
        help="Output only the cd command",
    ),
) -> None:
    """Enter a repository with context loaded."""
    controller.go(repo_name, output_command)


@app.command()
def sync(
    push: bool = typer.Option(
        False,
        "--push",
        help="Also push local commits after pulling (when safe)"
    )
) -> None:
    """Sync clean repositories (git pull) in parallel."""
    controller.sync(push=push)


@app.command()
def todos(
    root: Optional[str] = typer.Option(
        None, "--root", "-r", help="Root directory to scan for TODOs"
    ),
) -> None:
    """Display pending TODOs grouped by file and hierarchy."""
    controller.todos(root)


@app.command()
def exec(
    command: str = typer.Argument(..., help="Command to execute in each repository"),
    repos: Optional[str] = typer.Option(
        None, "--repos", "-r", help="Comma-separated list of specific repos to target"
    ),
    max_workers: int = typer.Option(
        8, "--workers", "-w", help="Maximum number of parallel workers"
    ),
    summary: bool = typer.Option(
        True, "--summary/--no-summary", help="Show execution summary"
    ),
) -> None:
    """Execute a command across multiple repositories in parallel."""
    repo_list = repos.split(",") if repos else None
    controller.bulk_exec(command, repo_list, max_workers, summary)


@app.command()
def do(
    task: str = typer.Argument(..., help="Task to run (e.g., 'test' runs 'just test')"),
    repos: Optional[str] = typer.Option(
        None, "--repos", "-r", help="Comma-separated list of specific repos to target"
    ),
    max_workers: int = typer.Option(
        8, "--workers", "-w", help="Maximum number of parallel workers"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show all output, not just errors"
    ),
) -> None:
    """Run a task across repositories, filtering for errors and failures."""
    repo_list = repos.split(",") if repos else None
    controller.do_command(task, repo_list, max_workers, verbose)
