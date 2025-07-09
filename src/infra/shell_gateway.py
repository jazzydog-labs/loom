"""ShellGateway for secure shell command execution with concurrency control."""
import asyncio
import subprocess
import threading
from pathlib import Path
from typing import Union, List, Optional, Dict, Any, Callable
import os
import signal
import time
import shlex
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass
from enum import Enum


class ShellPermissionError(Exception):
    """Raised when a shell command is not permitted."""
    pass


class ShellTimeoutError(Exception):
    """Raised when a shell command times out."""
    pass


class ShellSecurityError(Exception):
    """Raised when a shell command is deemed unsafe."""
    pass


@dataclass
class ShellResult:
    """Result of shell command execution."""
    command: str
    return_code: int
    stdout: str
    stderr: str
    duration: float
    success: bool
    pid: Optional[int] = None
    
    def __post_init__(self):
        self.success = self.return_code == 0


class ShellMode(Enum):
    """Shell execution modes."""
    SAFE = "safe"          # Only allow safe commands
    RESTRICTED = "restricted"  # Allow commands with restrictions
    PERMISSIVE = "permissive"  # Allow most commands with safety checks


class ShellGateway:
    """Gateway for secure shell command execution with concurrency control.
    
    This gateway provides secure shell command execution with:
    - Concurrency control to prevent resource exhaustion
    - Command validation and safety checks
    - Timeout management
    - Resource cleanup
    - Working directory sandboxing
    """
    
    # Safe commands that are generally allowed
    SAFE_COMMANDS = {
        'ls', 'cat', 'echo', 'pwd', 'whoami', 'date', 'which', 'head', 'tail',
        'grep', 'find', 'sort', 'uniq', 'wc', 'cut', 'awk', 'sed', 'tr',
        'git', 'python', 'python3', 'node', 'npm', 'yarn', 'pip', 'pip3',
        'just', 'make', 'cmake', 'cargo', 'go', 'java', 'javac', 'mvn',
        'docker', 'kubectl', 'helm', 'terraform', 'ansible', 'sleep', 'false'
    }
    
    # Dangerous commands that should be blocked
    DANGEROUS_COMMANDS = {
        'rm', 'rmdir', 'mv', 'cp', 'dd', 'shred', 'kill', 'killall',
        'shutdown', 'reboot', 'halt', 'poweroff', 'su', 'sudo', 'passwd',
        'chown', 'chmod', 'chgrp', 'mount', 'umount', 'fdisk', 'mkfs',
        'format', 'del', 'deltree', 'rd', 'erase', 'format'
    }
    
    def __init__(self, 
                 max_concurrent: int = 10,
                 default_timeout: float = 30.0,
                 mode: ShellMode = ShellMode.SAFE,
                 allowed_paths: Optional[List[Union[str, Path]]] = None,
                 allowed_commands: Optional[List[str]] = None,
                 blocked_commands: Optional[List[str]] = None):
        """Initialize ShellGateway.
        
        Args:
            max_concurrent: Maximum number of concurrent shell commands
            default_timeout: Default timeout for commands in seconds
            mode: Shell execution mode (safe, restricted, permissive)
            allowed_paths: List of directories where commands can be executed
            allowed_commands: Additional commands to allow
            blocked_commands: Additional commands to block
        """
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.mode = mode
        self.allowed_paths = [Path(p).resolve() for p in (allowed_paths or [])]
        
        # Build command sets
        self.safe_commands = set(self.SAFE_COMMANDS)
        if allowed_commands:
            self.safe_commands.update(allowed_commands)
        
        self.dangerous_commands = set(self.DANGEROUS_COMMANDS)
        if blocked_commands:
            self.dangerous_commands.update(blocked_commands)
        
        # Concurrency control
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self._semaphore = threading.Semaphore(max_concurrent)
        self._active_processes = {}
        self._process_lock = threading.Lock()
    
    def _validate_command(self, command: str) -> None:
        """Validate command for security and safety.
        
        Args:
            command: Command to validate
            
        Raises:
            ShellSecurityError: If command is deemed unsafe
        """
        # Parse command to get the base command
        try:
            parts = shlex.split(command)
        except ValueError as e:
            raise ShellSecurityError(f"Invalid command syntax: {e}")
        
        if not parts:
            raise ShellSecurityError("Empty command")
        
        base_cmd = parts[0]
        
        # Extract just the command name if it's a path
        if '/' in base_cmd:
            base_cmd = Path(base_cmd).name
        
        # Check against dangerous commands
        if base_cmd in self.dangerous_commands:
            raise ShellSecurityError(f"Command '{base_cmd}' is not allowed")
        
        # Check mode-specific restrictions
        if self.mode == ShellMode.SAFE:
            if base_cmd not in self.safe_commands:
                raise ShellSecurityError(f"Command '{base_cmd}' not in safe commands list")
        
        # Check for dangerous patterns
        dangerous_patterns = [
            '$(', '`', '&&', '||', ';', '|', '>', '>>', '<',
            'eval', 'exec', 'system'
        ]
        
        if self.mode != ShellMode.PERMISSIVE:
            for pattern in dangerous_patterns:
                if pattern in command:
                    raise ShellSecurityError(f"Command contains dangerous pattern: {pattern}")
    
    def _validate_working_directory(self, cwd: Union[str, Path]) -> Path:
        """Validate working directory.
        
        Args:
            cwd: Working directory path
            
        Returns:
            Validated Path object
            
        Raises:
            ShellPermissionError: If directory is not allowed
        """
        cwd_path = Path(cwd).resolve()
        
        # Check if within allowed paths
        if self.allowed_paths:
            if not any(self._is_subpath(cwd_path, allowed) 
                      for allowed in self.allowed_paths):
                raise ShellPermissionError(
                    f"Working directory {cwd} is outside allowed directories"
                )
        
        return cwd_path
    
    def _is_subpath(self, path: Path, parent: Path) -> bool:
        """Check if path is a subpath of parent."""
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False
    
    def _execute_process(self, command: str, cwd: Optional[Path] = None,
                        env: Optional[Dict[str, str]] = None,
                        timeout: Optional[float] = None,
                        input_data: Optional[str] = None) -> ShellResult:
        """Execute a single shell command.
        
        Args:
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            timeout: Command timeout
            input_data: Data to pass to stdin
            
        Returns:
            ShellResult with execution details
        """
        start_time = time.time()
        timeout = timeout or self.default_timeout
        
        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        # Execute command
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
                env=process_env,
                cwd=cwd,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            # Track process
            with self._process_lock:
                self._active_processes[process.pid] = process
            
            try:
                stdout, stderr = process.communicate(input=input_data, timeout=timeout)
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                # Kill process group
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                
                # Wait a bit for graceful termination
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    if os.name != 'nt':
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        process.kill()
                
                raise ShellTimeoutError(f"Command timed out after {timeout} seconds")
            
            finally:
                # Remove from active processes
                with self._process_lock:
                    self._active_processes.pop(process.pid, None)
        
        except ShellTimeoutError:
            # Re-raise timeout errors
            raise
        
        except FileNotFoundError:
            return ShellResult(
                command=command,
                return_code=127,
                stdout="",
                stderr="Command not found",
                duration=time.time() - start_time,
                success=False
            )
        
        except Exception as e:
            return ShellResult(
                command=command,
                return_code=1,
                stdout="",
                stderr=str(e),
                duration=time.time() - start_time,
                success=False
            )
        
        return ShellResult(
            command=command,
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
            duration=time.time() - start_time,
            success=return_code == 0,
            pid=process.pid
        )
    
    def execute(self, command: str, 
                cwd: Optional[Union[str, Path]] = None,
                env: Optional[Dict[str, str]] = None,
                timeout: Optional[float] = None,
                input_data: Optional[str] = None,
                check_security: bool = True) -> ShellResult:
        """Execute a shell command.
        
        Args:
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            timeout: Command timeout in seconds
            input_data: Data to pass to stdin
            check_security: Whether to perform security checks
            
        Returns:
            ShellResult with execution details
            
        Raises:
            ShellSecurityError: If command is not allowed
            ShellPermissionError: If directory is not allowed
            ShellTimeoutError: If command times out
        """
        # Security validation
        if check_security:
            self._validate_command(command)
        
        # Validate working directory
        if cwd:
            cwd = self._validate_working_directory(cwd)
        
        # Acquire semaphore for concurrency control
        with self._semaphore:
            return self._execute_process(command, cwd, env, timeout, input_data)
    
    def execute_many(self, commands: List[str],
                    cwd: Optional[Union[str, Path]] = None,
                    env: Optional[Dict[str, str]] = None,
                    timeout: Optional[float] = None,
                    max_workers: Optional[int] = None,
                    check_security: bool = True) -> List[ShellResult]:
        """Execute multiple shell commands concurrently.
        
        Args:
            commands: List of commands to execute
            cwd: Working directory
            env: Environment variables
            timeout: Command timeout in seconds
            max_workers: Maximum concurrent workers (defaults to max_concurrent)
            check_security: Whether to perform security checks
            
        Returns:
            List of ShellResult objects
        """
        if not commands:
            return []
        
        # Validate all commands first if security checking is enabled
        if check_security:
            for cmd in commands:
                self._validate_command(cmd)
        
        # Validate working directory
        if cwd:
            cwd = self._validate_working_directory(cwd)
        
        # Use ThreadPoolExecutor for concurrent execution
        max_workers = min(max_workers or self.max_concurrent, len(commands))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all commands
            future_to_cmd = {
                executor.submit(self._execute_process, cmd, cwd, env, timeout): cmd
                for cmd in commands
            }
            
            # Collect results
            results = []
            for future in as_completed(future_to_cmd):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    cmd = future_to_cmd[future]
                    results.append(ShellResult(
                        command=cmd,
                        return_code=1,
                        stdout="",
                        stderr=str(e),
                        duration=0.0,
                        success=False
                    ))
            
            return results
    
    def execute_pipeline(self, commands: List[str],
                        cwd: Optional[Union[str, Path]] = None,
                        env: Optional[Dict[str, str]] = None,
                        timeout: Optional[float] = None,
                        check_security: bool = True) -> ShellResult:
        """Execute commands in a pipeline (output of one becomes input of next).
        
        Args:
            commands: List of commands to execute in pipeline
            cwd: Working directory
            env: Environment variables
            timeout: Total timeout for entire pipeline
            check_security: Whether to perform security checks
            
        Returns:
            ShellResult with final pipeline output
        """
        if not commands:
            raise ValueError("No commands provided for pipeline")
        
        # Validate all commands
        if check_security:
            for cmd in commands:
                self._validate_command(cmd)
        
        # Validate working directory
        if cwd:
            cwd = self._validate_working_directory(cwd)
        
        # Execute pipeline
        start_time = time.time()
        current_input = None
        
        for i, command in enumerate(commands):
            try:
                result = self._execute_process(command, cwd, env, timeout, current_input)
                
                if not result.success:
                    # Pipeline failed
                    return ShellResult(
                        command=" | ".join(commands),
                        return_code=result.return_code,
                        stdout=result.stdout,
                        stderr=f"Pipeline failed at step {i+1}: {result.stderr}",
                        duration=time.time() - start_time,
                        success=False
                    )
                
                # Use output as input for next command
                current_input = result.stdout
                
            except Exception as e:
                return ShellResult(
                    command=" | ".join(commands),
                    return_code=1,
                    stdout="",
                    stderr=f"Pipeline error at step {i+1}: {str(e)}",
                    duration=time.time() - start_time,
                    success=False
                )
        
        return ShellResult(
            command=" | ".join(commands),
            return_code=0,
            stdout=current_input or "",
            stderr="",
            duration=time.time() - start_time,
            success=True
        )
    
    def kill_all(self) -> int:
        """Kill all active processes.
        
        Returns:
            Number of processes killed
        """
        killed = 0
        with self._process_lock:
            for pid, process in list(self._active_processes.items()):
                try:
                    if os.name != 'nt':
                        os.killpg(os.getpgid(pid), signal.SIGTERM)
                    else:
                        process.terminate()
                    killed += 1
                except (ProcessLookupError, OSError):
                    pass
            self._active_processes.clear()
        
        return killed
    
    def get_active_count(self) -> int:
        """Get number of active processes.
        
        Returns:
            Number of currently running processes
        """
        with self._process_lock:
            return len(self._active_processes)
    
    def shutdown(self) -> None:
        """Shutdown the gateway and cleanup resources."""
        # Kill all active processes
        self.kill_all()
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
    
    # Convenience methods for common operations
    def ls(self, path: Union[str, Path] = ".", options: str = "") -> ShellResult:
        """List directory contents."""
        return self.execute(f"ls {options} {shlex.quote(str(path))}")
    
    def cat(self, filename: Union[str, Path]) -> ShellResult:
        """Display file contents."""
        return self.execute(f"cat {shlex.quote(str(filename))}")
    
    def grep(self, pattern: str, filename: Union[str, Path], options: str = "") -> ShellResult:
        """Search for pattern in file."""
        return self.execute(f"grep {options} {shlex.quote(pattern)} {shlex.quote(str(filename))}")
    
    def find(self, path: Union[str, Path] = ".", pattern: str = "*", options: str = "") -> ShellResult:
        """Find files matching pattern."""
        return self.execute(f"find {shlex.quote(str(path))} {options} -name {shlex.quote(pattern)}")
    
    def git(self, args: str, cwd: Optional[Union[str, Path]] = None) -> ShellResult:
        """Execute git command."""
        return self.execute(f"git {args}", cwd=cwd)
    
    def python(self, script: str, args: str = "", cwd: Optional[Union[str, Path]] = None) -> ShellResult:
        """Execute Python script."""
        return self.execute(f"python3 {shlex.quote(script)} {args}", cwd=cwd)
    
    def node(self, script: str, args: str = "", cwd: Optional[Union[str, Path]] = None) -> ShellResult:
        """Execute Node.js script."""
        return self.execute(f"node {shlex.quote(script)} {args}", cwd=cwd)