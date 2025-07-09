import subprocess
import os
import time
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GitCommandError(Exception):
    """Custom exception for Git command failures."""
    
    def __init__(self, command: str, return_code: int, stdout: str, stderr: str):
        self.command = command
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(f"Git command failed with return code {return_code}: {command}")


class GitGateway:
    """Gateway to the Git CLI with proper subprocess handling."""
    
    def __init__(self, retry_count: int = 3, retry_delay: float = 1.0):
        """Initialize GitGateway with retry configuration.
        
        Args:
            retry_count: Number of times to retry failed commands
            retry_delay: Delay in seconds between retries
        """
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._git_executable = self._find_git_executable()
    
    def _find_git_executable(self) -> str:
        """Find the git executable path.
        
        Returns:
            Path to git executable
            
        Raises:
            RuntimeError: If git is not found
        """
        # Try common locations
        for cmd in ["git", "/usr/bin/git", "/usr/local/bin/git"]:
            try:
                result = subprocess.run([cmd, "--version"], 
                                      capture_output=True, 
                                      text=True,
                                      timeout=5)
                if result.returncode == 0:
                    return cmd
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        
        raise RuntimeError("Git executable not found. Please ensure git is installed and in PATH.")
    
    def run(self, args: List[str], cwd: Optional[Union[str, Path]] = None, 
            input_data: Optional[str] = None, env: Optional[Dict[str, str]] = None,
            timeout: Optional[int] = None, check: bool = True,
            retry: bool = True) -> Dict[str, Any]:
        """Execute a git command with proper error handling and retries.
        
        Args:
            args: Git command arguments (e.g., ['status', '--porcelain'])
            cwd: Working directory for the command
            input_data: Optional input to send to the command
            env: Optional environment variables
            timeout: Command timeout in seconds
            check: Whether to raise exception on non-zero return code
            retry: Whether to retry on failure
            
        Returns:
            Dictionary with command results:
                - command: The full command executed
                - args: The git arguments
                - return_code: Process return code
                - stdout: Standard output
                - stderr: Standard error
                - success: Boolean indicating success
                
        Raises:
            GitCommandError: If command fails and check=True
            subprocess.TimeoutExpired: If command times out
        """
        # Build full command
        cmd = [self._git_executable] + args
        cmd_str = " ".join(cmd)
        
        # Prepare environment
        cmd_env = os.environ.copy()
        if env:
            cmd_env.update(env)
        
        # Convert Path to string if needed
        if cwd and isinstance(cwd, Path):
            cwd = str(cwd)
        
        # Retry logic
        attempts = self.retry_count if retry else 1
        last_error = None
        
        for attempt in range(attempts):
            try:
                # Log attempt
                if attempt > 0:
                    logger.debug(f"Retrying git command (attempt {attempt + 1}/{attempts}): {cmd_str}")
                else:
                    logger.debug(f"Executing git command: {cmd_str}")
                
                # Execute command
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    input=input_data,
                    capture_output=True,
                    text=True,
                    env=cmd_env,
                    timeout=timeout
                )
                
                # Build result dictionary
                output = {
                    "command": cmd_str,
                    "args": args,
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "success": result.returncode == 0
                }
                
                # Check for errors
                if check and result.returncode != 0:
                    error = GitCommandError(
                        cmd_str,
                        result.returncode,
                        result.stdout,
                        result.stderr
                    )
                    
                    # Retry on certain errors
                    if retry and attempt < attempts - 1 and self._should_retry(result):
                        last_error = error
                        time.sleep(self.retry_delay)
                        continue
                    
                    raise error
                
                return output
                
            except subprocess.TimeoutExpired as e:
                logger.error(f"Git command timed out: {cmd_str}")
                if attempt < attempts - 1 and retry:
                    time.sleep(self.retry_delay)
                    continue
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error executing git command: {cmd_str}: {str(e)}")
                if attempt < attempts - 1 and retry:
                    last_error = e
                    time.sleep(self.retry_delay)
                    continue
                raise
        
        # If we get here, all retries failed
        if last_error:
            raise last_error
    
    def _should_retry(self, result: subprocess.CompletedProcess) -> bool:
        """Determine if a command should be retried based on the error.
        
        Args:
            result: The subprocess result
            
        Returns:
            True if command should be retried
        """
        # Retry on lock errors
        error_output = result.stderr.lower()
        retry_patterns = [
            "unable to create",
            "cannot lock ref",
            "unable to access",
            "resource temporarily unavailable",
            "another git process"
        ]
        
        return any(pattern in error_output for pattern in retry_patterns)
    
    # Convenience methods for common git operations
    
    def status(self, cwd: Union[str, Path], porcelain: bool = True) -> Dict[str, Any]:
        """Get repository status.
        
        Args:
            cwd: Repository directory
            porcelain: Use porcelain format for parsing
            
        Returns:
            Status result dictionary
        """
        args = ["status"]
        if porcelain:
            args.append("--porcelain")
        return self.run(args, cwd=cwd)
    
    def add(self, files: List[str], cwd: Union[str, Path]) -> Dict[str, Any]:
        """Add files to staging area.
        
        Args:
            files: List of files to add
            cwd: Repository directory
            
        Returns:
            Command result dictionary
        """
        args = ["add"] + files
        return self.run(args, cwd=cwd)
    
    def commit(self, message: str, cwd: Union[str, Path], 
               amend: bool = False, no_edit: bool = False) -> Dict[str, Any]:
        """Create a commit.
        
        Args:
            message: Commit message
            cwd: Repository directory
            amend: Whether to amend the previous commit
            no_edit: Skip editor when amending
            
        Returns:
            Command result dictionary
        """
        args = ["commit", "-m", message]
        if amend:
            args.append("--amend")
            if no_edit:
                args.append("--no-edit")
        return self.run(args, cwd=cwd)
    
    def push(self, cwd: Union[str, Path], remote: str = "origin", 
             branch: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """Push changes to remote.
        
        Args:
            cwd: Repository directory
            remote: Remote name
            branch: Branch name (current branch if None)
            force: Force push
            
        Returns:
            Command result dictionary
        """
        args = ["push", remote]
        if branch:
            args.append(branch)
        if force:
            args.append("--force")
        return self.run(args, cwd=cwd)
    
    def pull(self, cwd: Union[str, Path], remote: str = "origin",
             branch: Optional[str] = None, rebase: bool = False) -> Dict[str, Any]:
        """Pull changes from remote.
        
        Args:
            cwd: Repository directory
            remote: Remote name
            branch: Branch name (current branch if None)
            rebase: Use rebase instead of merge
            
        Returns:
            Command result dictionary
        """
        args = ["pull", remote]
        if branch:
            args.append(branch)
        if rebase:
            args.append("--rebase")
        return self.run(args, cwd=cwd)
    
    def clone(self, url: str, destination: Union[str, Path], 
              depth: Optional[int] = None) -> Dict[str, Any]:
        """Clone a repository.
        
        Args:
            url: Repository URL
            destination: Destination directory
            depth: Shallow clone depth
            
        Returns:
            Command result dictionary
        """
        args = ["clone", url, str(destination)]
        if depth:
            args.extend(["--depth", str(depth)])
        return self.run(args)
    
    def checkout(self, branch: str, cwd: Union[str, Path], 
                 create: bool = False) -> Dict[str, Any]:
        """Checkout a branch.
        
        Args:
            branch: Branch name
            cwd: Repository directory
            create: Create new branch
            
        Returns:
            Command result dictionary
        """
        args = ["checkout"]
        if create:
            args.append("-b")
        args.append(branch)
        return self.run(args, cwd=cwd)
    
    def branch(self, cwd: Union[str, Path], all_branches: bool = False,
               remotes: bool = False) -> Dict[str, Any]:
        """List branches.
        
        Args:
            cwd: Repository directory
            all_branches: Show all branches
            remotes: Show remote branches
            
        Returns:
            Command result dictionary
        """
        args = ["branch"]
        if all_branches:
            args.append("-a")
        elif remotes:
            args.append("-r")
        return self.run(args, cwd=cwd)
    
    def log(self, cwd: Union[str, Path], oneline: bool = False,
            limit: Optional[int] = None, since: Optional[str] = None) -> Dict[str, Any]:
        """Get commit log.
        
        Args:
            cwd: Repository directory
            oneline: Use oneline format
            limit: Limit number of commits
            since: Show commits since date
            
        Returns:
            Command result dictionary
        """
        args = ["log"]
        if oneline:
            args.append("--oneline")
        if limit:
            args.extend(["-n", str(limit)])
        if since:
            args.extend(["--since", since])
        return self.run(args, cwd=cwd)
    
    def diff(self, cwd: Union[str, Path], cached: bool = False,
             name_only: bool = False) -> Dict[str, Any]:
        """Show differences.
        
        Args:
            cwd: Repository directory
            cached: Show staged changes
            name_only: Show only file names
            
        Returns:
            Command result dictionary
        """
        args = ["diff"]
        if cached:
            args.append("--cached")
        if name_only:
            args.append("--name-only")
        return self.run(args, cwd=cwd)
    
    def stash(self, cwd: Union[str, Path], command: str = "save",
              message: Optional[str] = None, include_untracked: bool = False) -> Dict[str, Any]:
        """Stash operations.
        
        Args:
            cwd: Repository directory
            command: Stash command (save, pop, list, etc.)
            message: Stash message (for save)
            include_untracked: Include untracked files
            
        Returns:
            Command result dictionary
        """
        args = ["stash", command]
        if command == "save" and message:
            args.append(message)
        if include_untracked:
            args.append("-u")
        return self.run(args, cwd=cwd)
    
    def remote(self, cwd: Union[str, Path], verbose: bool = False) -> Dict[str, Any]:
        """List remotes.
        
        Args:
            cwd: Repository directory
            verbose: Show verbose output
            
        Returns:
            Command result dictionary
        """
        args = ["remote"]
        if verbose:
            args.append("-v")
        return self.run(args, cwd=cwd)
