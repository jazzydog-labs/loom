#!/usr/bin/env python3
"""Main loom application."""

import sys

from .cli import app  # Typer application with all commands
from .cli.loom_cli import controller  # shared controller instance


def main() -> None:
    """Entry point used by loom.py."""
    if len(sys.argv) == 1:
        controller.start(app)
    else:
        app()


if __name__ == "__main__":
    main()
