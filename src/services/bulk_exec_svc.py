"""Bulk execution service for running commands across multiple repositories."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..domain.repo import Repo
from ..domain.foundry import Foundry


@dataclass
class CommandResult:
    """Result of executing a command in a repository."""
    repo_name: str
    repo_path: str
    command: str
    success: bool
    stdout: str
    stderr: str
    return_code: int
    error: Optional[str] = None


class BulkExecSvc:
    """Execute commands across multiple repositories."""

    def __init__(self, foundry: Optional[Foundry] = None):
        """Initialize the service with an optional Foundry instance."""
        self.foundry = foundry

    def run(self, command: str, repos: Optional[List[Repo]] = None, 
            cwd_relative: bool = True, max_workers: int = 8) -> Dict[str, CommandResult]:
        """Execute a command across multiple repositories in parallel.
        
        Args:
            command: Shell command to execute in each repository
            repos: List of repositories to run command in. If None, uses all repos from foundry
            cwd_relative: If True, execute command with cwd set to repo directory
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary mapping repo name to CommandResult
        """
        if repos is None:
            if self.foundry is None:
                raise ValueError("No repositories specified and no foundry configured")
            repos = self.foundry.all_repos()
        
        if not repos:
            return {}
        
        results: Dict[str, CommandResult] = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_repo = {
                executor.submit(self._execute_in_repo, repo, command, cwd_relative): repo
                for repo in repos
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_repo):
                repo = future_to_repo[future]
                try:
                    result = future.result()
                    results[repo.name] = result
                except Exception as exc:
                    # Capture any unexpected errors
                    results[repo.name] = CommandResult(
                        repo_name=repo.name,
                        repo_path=repo.path,
                        command=command,
                        success=False,
                        stdout="",
                        stderr="",
                        return_code=-1,
                        error=f"Unexpected error: {str(exc)}"
                    )
        
        return results
    
    def run_with_aggregation(self, command: str, repos: Optional[List[Repo]] = None,
                           cwd_relative: bool = True, max_workers: int = 8) -> Dict[str, Union[Dict[str, CommandResult], List[str]]]:
        """Execute command and provide aggregated results.
        
        Returns a dictionary with:
            - "results": Individual CommandResult for each repo
            - "successful": List of repo names where command succeeded
            - "failed": List of repo names where command failed
            - "summary": Summary statistics
        """
        results = self.run(command, repos, cwd_relative, max_workers)
        
        successful = [name for name, result in results.items() if result.success]
        failed = [name for name, result in results.items() if not result.success]
        
        return {
            "results": results,
            "successful": successful,
            "failed": failed,
            "summary": {
                "total": len(results),
                "succeeded": len(successful),
                "failed": len(failed),
                "success_rate": len(successful) / len(results) if results else 0.0
            }
        }
    
    def _execute_in_repo(self, repo: Repo, command: str, cwd_relative: bool) -> CommandResult:
        """Execute a command in a specific repository."""
        repo_path = Path(repo.path).expanduser().resolve()
        
        # Check if repo directory exists
        if not repo_path.exists():
            return CommandResult(
                repo_name=repo.name,
                repo_path=str(repo_path),
                command=command,
                success=False,
                stdout="",
                stderr=f"Repository directory does not exist: {repo_path}",
                return_code=-1
            )
        
        try:
            # Execute the command
            cwd = repo_path if cwd_relative else None
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            return CommandResult(
                repo_name=repo.name,
                repo_path=str(repo_path),
                command=command,
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )
            
        except subprocess.TimeoutExpired:
            return CommandResult(
                repo_name=repo.name,
                repo_path=str(repo_path),
                command=command,
                success=False,
                stdout="",
                stderr="Command timed out after 5 minutes",
                return_code=-1,
                error="TimeoutExpired"
            )
        except Exception as e:
            return CommandResult(
                repo_name=repo.name,
                repo_path=str(repo_path),
                command=command,
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                error=type(e).__name__
            )