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
