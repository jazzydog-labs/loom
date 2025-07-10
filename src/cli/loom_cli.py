"""Typer CLI mapping commands to the LoomController."""

from typing import Optional
import typer
from rich.console import Console
import json
import sys

from ..app.loom_controller import LoomController

# Import JsonActionRouter conditionally to avoid breaking CLI if jsonschema not installed
try:
    from ..app.json_action_router import JsonActionRouter
    HAS_JSON_ROUTER = True
except ImportError:
    HAS_JSON_ROUTER = False

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
def just(
    recipe: str = typer.Argument(..., help="Just recipe to run (e.g., 'test' runs 'just test')"),
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
    """Run a just recipe across repositories with single-line output."""
    repo_list = repos.split(",") if repos else None
    controller.just_command(recipe, repo_list, max_workers, verbose)


@app.command("json")
def json_action(
    action_input: Optional[str] = typer.Argument(
        None, 
        help="JSON action as string, file path, or '-' for stdin"
    ),
    pretty: bool = typer.Option(
        True, "--pretty/--no-pretty", 
        help="Pretty print output"
    ),
    schema_dir: Optional[str] = typer.Option(
        None, "--schema-dir", 
        help="Directory containing JSON schemas"
    ),
) -> None:
    """Execute Loom actions via JSON interface.
    
    Examples:
        loom json '{"action": "repo.status", "version": "1.0"}'
        loom json action.json
        echo '{"action": "freeze.create", "payload": {"name": "backup"}}' | loom json -
    """
    if not HAS_JSON_ROUTER:
        console.print("[red]Error: JSON Action Router requires jsonschema package.[/red]")
        console.print("Install with: pip install jsonschema")
        raise typer.Exit(1)
    
    # Initialize router with all handlers
    from pathlib import Path
    router = JsonActionRouter(Path(schema_dir) if schema_dir else None)
    
    # Register all handlers
    from ..app.action_handlers import (
        FreezeCreateHandler, FreezeRestoreHandler, FreezeListHandler,
        BulkExecuteHandler,
        StashSaveHandler, StashRestoreHandler, StashListHandler,
        RepoStatusHandler, RepoHealthHandler,
        JustRunHandler
    )
    
    # Register handlers
    router.register_handler(FreezeCreateHandler(router))
    router.register_handler(FreezeRestoreHandler(router))
    router.register_handler(FreezeListHandler(router))
    router.register_handler(BulkExecuteHandler(router))
    router.register_handler(StashSaveHandler(router))
    router.register_handler(StashRestoreHandler(router))
    router.register_handler(StashListHandler(router))
    router.register_handler(RepoStatusHandler(router))
    router.register_handler(RepoHealthHandler(router))
    router.register_handler(JustRunHandler(router))
    
    # Get action data
    action_data = None
    
    if action_input is None:
        # Show available actions
        console.print("[bold]Available Actions:[/bold]")
        actions = router.list_actions()
        for name, info in sorted(actions.items()):
            console.print(f"  • {name}: {info['description']}")
        return
    
    if action_input == "-":
        # Read from stdin
        action_data = sys.stdin.read()
    elif action_input.startswith("{"):
        # Direct JSON string
        action_data = action_input
    else:
        # File path
        try:
            with open(action_input, 'r') as f:
                action_data = f.read()
        except FileNotFoundError:
            console.print(f"[red]Error: File not found: {action_input}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error reading file: {e}[/red]")
            raise typer.Exit(1)
    
    # Execute action
    try:
        # Check if it's a pipeline
        parsed = json.loads(action_data) if isinstance(action_data, str) else action_data
        if parsed.get("action") == "pipeline":
            result = router.execute_pipeline(parsed.get("payload", {}))
        else:
            result = router.execute(action_data)
        
        # Output result
        result_dict = result.to_dict()
        
        if pretty:
            console.print_json(data=result_dict)
        else:
            print(json.dumps(result_dict))
        
        # Exit with appropriate code
        if not result.success:
            raise typer.Exit(1)
            
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error executing action: {e}[/red]")
        raise typer.Exit(1)
