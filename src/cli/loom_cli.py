"""Typer CLI mapping commands to the LoomController."""

import typer
from ..app.loom_controller import LoomController

app = typer.Typer()
controller = LoomController()

@app.command()
def status():
    typer.echo(controller.status())
