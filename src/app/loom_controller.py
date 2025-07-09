from typing import List, Optional
from rich.table import Table
from rich.panel import Panel

from ..controllers.loom_controller import LoomController as LegacyController
from ..services import FreezeSvc, BulkExecSvc, StashCoordinator, RepoStatusService
from ..events.event_bus import EventBus
from ..views.repo_view import RepoView
from ..domain.repo import Repo
from ..domain.foundry import Foundry

class LoomController(LegacyController):
    """Thin wrapper integrating new services."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.freeze_svc = FreezeSvc()
        self.bulk_exec_svc = BulkExecSvc()
        self.stash_coord = StashCoordinator()
        self.status_svc = RepoStatusService()
        self.events = EventBus()

    def status(self) -> str:
        return "TODO: aggregated status"
    
    def show_details(self) -> None:
        """Show repository details using the new RepoStatusService."""
        repos_config = self.config.load_repos()
        repos = repos_config.get("repos", [])
        if not repos:
            self.console.print("No repositories configured.")
            return

        dev_root = self.config.get_dev_root()
        foundry_dir = self.config.get_foundry_dir()
        if not dev_root:
            self.console.print(
                "Development root not configured. Please run 'loom init' first."
            )
            return

        repo_paths = {
            repo["name"]: repo["path"].replace("$DEV_ROOT", dev_root).replace(
                "$FOUNDRY_DIR", foundry_dir
            )
            for repo in repos
        }

        # Use the new RepoStatusService
        repos_data = self.status_svc.summaries_parallel(repo_paths)
        RepoView(self.console).display_multiple_repos(repos_data)
    
    def bulk_exec(self, command: str, repo_names: Optional[List[str]] = None, 
                  max_workers: int = 8, show_summary: bool = True) -> None:
        """Execute a command across multiple repositories using BulkExecSvc."""
        # Get repository configuration
        repos_config = self.config.load_repos()
        all_repos = repos_config.get("repos", [])
        
        if not all_repos:
            self.console.print("[red]No repositories configured.[/red]")
            return
        
        dev_root = self.config.get_dev_root()
        foundry_dir = self.config.get_foundry_dir()
        
        if not dev_root:
            self.console.print("[red]Development root not configured. Please run 'loom init' first.[/red]")
            return
        
        # Filter repositories if specific ones requested
        if repo_names:
            filtered_repos = [r for r in all_repos if r["name"] in repo_names]
            if not filtered_repos:
                self.console.print(f"[red]No matching repositories found: {', '.join(repo_names)}[/red]")
                return
        else:
            filtered_repos = all_repos
        
        # Create Repo objects
        repo_objects = []
        for repo_config in filtered_repos:
            path = repo_config["path"].replace("$DEV_ROOT", dev_root).replace("$FOUNDRY_DIR", foundry_dir)
            repo_objects.append(Repo(name=repo_config["name"], path=path))
        
        # Create a Foundry instance and set up BulkExecSvc
        foundry = Foundry(repo_objects)
        self.bulk_exec_svc.foundry = foundry
        
        # Display what we're about to do
        self.console.print(f"\n[bold]Executing command across {len(repo_objects)} repositories:[/bold]")
        self.console.print(f"[cyan]Command:[/cyan] {command}")
        self.console.print(f"[cyan]Repositories:[/cyan] {', '.join(r.name for r in repo_objects)}")
        self.console.print(f"[cyan]Workers:[/cyan] {max_workers}\n")
        
        # Execute with progress indication
        with self.console.status("[bold green]Executing command in parallel..."):
            if show_summary:
                results = self.bulk_exec_svc.run_with_aggregation(
                    command, repos=repo_objects, max_workers=max_workers
                )
                aggregated = results
            else:
                command_results = self.bulk_exec_svc.run(
                    command, repos=repo_objects, max_workers=max_workers
                )
                aggregated = {"results": command_results}
        
        # Display results
        self._display_bulk_exec_results(aggregated, show_summary)
    
    def _display_bulk_exec_results(self, aggregated: dict, show_summary: bool) -> None:
        """Display the results of bulk command execution."""
        results = aggregated["results"]
        
        # Create results table
        table = Table(title="Execution Results", show_lines=True)
        table.add_column("Repository", style="cyan", no_wrap=True)
        table.add_column("Status", style="bold")
        table.add_column("Return Code", justify="center")
        table.add_column("Output", style="dim", overflow="fold")
        
        # Sort results by repo name for consistent display
        sorted_results = sorted(results.items(), key=lambda x: x[0])
        
        for repo_name, result in sorted_results:
            status = "[green]✓ Success[/green]" if result.success else "[red]✗ Failed[/red]"
            
            # Combine stdout and stderr for output, truncate if too long
            output = ""
            if result.stdout:
                output += result.stdout.strip()
            if result.stderr:
                if output:
                    output += "\n---\n"
                output += f"[red]{result.stderr.strip()}[/red]"
            
            # Truncate very long output
            if len(output) > 200:
                output = output[:200] + "..."
            
            table.add_row(
                repo_name,
                status,
                str(result.return_code),
                output or "[dim]No output[/dim]"
            )
        
        self.console.print(table)
        
        # Show summary if requested
        if show_summary and "summary" in aggregated:
            summary = aggregated["summary"]
            
            summary_panel = Panel(
                f"[green]Succeeded:[/green] {summary['succeeded']}\n"
                f"[red]Failed:[/red] {summary['failed']}\n"
                f"[cyan]Total:[/cyan] {summary['total']}\n"
                f"[yellow]Success Rate:[/yellow] {summary['success_rate']:.1%}",
                title="Execution Summary",
                expand=False
            )
            self.console.print("\n")
            self.console.print(summary_panel)
            
            # List failed repos if any
            if aggregated.get("failed"):
                self.console.print("\n[red]Failed repositories:[/red]")
                for repo in aggregated["failed"]:
                    self.console.print(f"  - {repo}")
    
    def just_command(self, recipe: str, repo_names: Optional[List[str]] = None,
                     max_workers: int = 8, verbose: bool = False) -> None:
        """Run a just recipe across repositories with single-line output."""
        # Map common tasks to their commands
        command = f"just {recipe}"
        
        # Get repository configuration
        repos_config = self.config.load_repos()
        all_repos = repos_config.get("repos", [])
        
        if not all_repos:
            self.console.print("[red]No repositories configured.[/red]")
            return
        
        dev_root = self.config.get_dev_root()
        foundry_dir = self.config.get_foundry_dir()
        
        if not dev_root:
            self.console.print("[red]Development root not configured. Please run 'loom init' first.[/red]")
            return
        
        # Filter repositories if specific ones requested
        if repo_names:
            filtered_repos = [r for r in all_repos if r["name"] in repo_names]
            if not filtered_repos:
                self.console.print(f"[red]No matching repositories found: {', '.join(repo_names)}[/red]")
                return
        else:
            filtered_repos = all_repos
        
        # Create Repo objects
        repo_objects = []
        for repo_config in filtered_repos:
            path = repo_config["path"].replace("$DEV_ROOT", dev_root).replace("$FOUNDRY_DIR", foundry_dir)
            repo_objects.append(Repo(name=repo_config["name"], path=path))
        
        # Create a Foundry instance and set up BulkExecSvc
        foundry = Foundry(repo_objects)
        self.bulk_exec_svc.foundry = foundry
        
        # Display what we're about to do
        self.console.print(f"\n[bold]Running recipe '{recipe}' across {len(repo_objects)} repositories:[/bold]")
        self.console.print(f"[cyan]Command:[/cyan] {command}")
        self.console.print(f"[cyan]Mode:[/cyan] {'Verbose (all output)' if verbose else 'Single-line output'}")
        self.console.print(f"[cyan]Workers:[/cyan] {max_workers}\n")
        
        # Execute with progress indication
        with self.console.status(f"[bold green]Running '{command}' in parallel..."):
            results = self.bulk_exec_svc.run(
                command, repos=repo_objects, max_workers=max_workers
            )
        
        # Display results
        self._display_just_results(results, recipe, verbose)
    
    def _display_just_results(self, results: dict, recipe: str, verbose: bool) -> None:
        """Display the results of 'just' command execution with single-line output."""
        # Error patterns to look for
        error_patterns = [
            "error", "Error", "ERROR",
            "fail", "Fail", "FAIL", "Failed", "FAILED",
            "exception", "Exception", "EXCEPTION",
            "traceback", "Traceback",
            "assert", "Assert", "AssertionError",
            "abort", "Abort", "ABORT",
            "fatal", "Fatal", "FATAL",
            "❌", "✗", "⚠️",  # Common error symbols
            "not found", "No such file",
            "command not found",
            "recipe not found",  # just-specific error
        ]
        
        # Categorize results
        successful_repos = []
        failed_repos = []
        repos_with_errors = []
        
        for repo_name, result in sorted(results.items()):
            if not result.success:
                failed_repos.append((repo_name, result))
            else:
                # Check output for error patterns
                combined_output = f"{result.stdout} {result.stderr}".lower()
                has_error_pattern = any(pattern.lower() in combined_output for pattern in error_patterns)
                
                if has_error_pattern:
                    repos_with_errors.append((repo_name, result))
                else:
                    successful_repos.append(repo_name)
        
        # Display single-line results
        self.console.print(f"\n[bold]Recipe '{recipe}' Results:[/bold]")
        
        # In verbose mode, show all output in table format
        if verbose:
            table = Table(show_lines=True)
            table.add_column("Repository", style="cyan", no_wrap=True)
            table.add_column("Status", style="bold")
            table.add_column("Output", overflow="fold")
            
            for repo_name, result in sorted(results.items()):
                status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
                output = result.stdout + ("\n---\n" + result.stderr if result.stderr else "")
                table.add_row(repo_name, status, output or "[dim]No output[/dim]")
            
            self.console.print(table)
        else:
            # Single-line output format
            for repo_name, result in sorted(results.items()):
                if not result.success:
                    # Check if it's a missing justfile or recipe
                    if "justfile" in result.stderr.lower() or "recipe" in result.stderr.lower():
                        if "no justfile" in result.stderr.lower() or "justfile not found" in result.stderr.lower():
                            self.console.print(f"[yellow]{repo_name}[/yellow]: no justfile")
                        elif "recipe" in result.stderr.lower() and "not found" in result.stderr.lower():
                            self.console.print(f"[yellow]{repo_name}[/yellow]: no recipe '{recipe}'")
                        else:
                            self.console.print(f"[red]{repo_name}[/red]: {result.stderr.strip().split(chr(10))[0]}")
                    else:
                        self.console.print(f"[red]{repo_name}[/red]: {result.stderr.strip().split(chr(10))[0] if result.stderr else 'failed'}")
                else:
                    # Success - show first line of output or success indicator
                    if result.stdout:
                        first_line = result.stdout.strip().split('\n')[0]
                        self.console.print(f"[green]{repo_name}[/green]: {first_line}")
                    else:
                        self.console.print(f"[green]{repo_name}[/green]: ✓")
