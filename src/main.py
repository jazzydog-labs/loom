#!/usr/bin/env python3
"""Main loom application."""

from __future__ import annotations

import sys
from typing import Optional

import typer
from rich.console import Console

from .app import LoomController
console = Console()
app = typer.Typer()
controller = LoomController(console=console)


def main() -> None:
    """Entry point used by loom.py."""
    if len(sys.argv) == 1:
        controller.start(app)
    else:
        app()


@app.command()
def init(
    dev_root: Optional[str] = typer.Option(None, "--dev-root", "-d", help="Development root directory"),
    bootstrap: bool = typer.Option(True, "--bootstrap/--no-bootstrap", help="Run foundry-bootstrap after setup"),
) -> None:
    """Initialize the foundry ecosystem."""
    controller.init(dev_root, bootstrap)


@app.command()
def details() -> None:
    """Show detailed git status for all repositories."""
    controller.show_details()


@app.command()
def go(
    repo_name: Optional[str] = typer.Argument(None, help="Repository name to enter directly"),
    output_command: bool = typer.Option(False, "--output-command", "-o", help="Output only the cd command"),
) -> None:
    """Enter a repository with context loaded."""
    controller.go(repo_name, output_command)


if __name__ == "__main__":
    main()
