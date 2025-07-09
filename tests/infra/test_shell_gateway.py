import pytest
import tempfile
import time
import os
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from concurrent.futures import ThreadPoolExecutor

from src.infra.shell_gateway import (
    ShellGateway, ShellResult, ShellMode, 
    ShellPermissionError, ShellTimeoutError, ShellSecurityError
)


class TestShellResult:
    """Test suite for ShellResult."""
    
    def test_shell_result_success(self):
        """Test ShellResult with successful command."""
        result = ShellResult(
            command="echo hello",
            return_code=0,
            stdout="hello\n",
            stderr="",
            duration=0.1,
            success=True
        )
        assert result.success is True
        assert result.return_code == 0
    
    def test_shell_result_failure(self):
        """Test ShellResult with failed command."""
        result = ShellResult(
            command="false",
            return_code=1,
            stdout="",
            stderr="",
            duration=0.1,
            success=False
        )
        assert result.success is False
        assert result.return_code == 1
    
    def test_shell_result_post_init(self):
        """Test ShellResult success is set correctly in __post_init__."""
        # Success case
        result = ShellResult(
            command="echo test",
            return_code=0,
            stdout="test",
            stderr="",
            duration=0.1,
            success=False  # This should be overridden
        )
        assert result.success is True
        
        # Failure case
        result = ShellResult(
            command="false",
            return_code=1,
            stdout="",
            stderr="",
            duration=0.1,
            success=True  # This should be overridden
        )
        assert result.success is False


class TestShellGateway:
    """Test suite for ShellGateway."""
    
    @pytest.fixture
    def shell_gateway(self):
        """Create a basic ShellGateway instance."""
        return ShellGateway(max_concurrent=2, default_timeout=5.0)
    
    @pytest.fixture
    def safe_gateway(self):
        """Create ShellGateway in safe mode."""
        return ShellGateway(mode=ShellMode.SAFE)
    
    @pytest.fixture
    def restricted_gateway(self):
        """Create ShellGateway in restricted mode."""
        return ShellGateway(mode=ShellMode.RESTRICTED)
    
    @pytest.fixture
    def permissive_gateway(self):
        """Create ShellGateway in permissive mode."""
        return ShellGateway(mode=ShellMode.PERMISSIVE)
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_init_default(self):
        """Test ShellGateway initialization with defaults."""
        gateway = ShellGateway()
        assert gateway.max_concurrent == 10
        assert gateway.default_timeout == 30.0
        assert gateway.mode == ShellMode.SAFE
        assert gateway.allowed_paths == []
        assert len(gateway.safe_commands) > 0
        assert len(gateway.dangerous_commands) > 0
    
    def test_init_custom_settings(self):
        """Test ShellGateway with custom settings."""
        gateway = ShellGateway(
            max_concurrent=5,
            default_timeout=10.0,
            mode=ShellMode.PERMISSIVE,
            allowed_paths=['/tmp'],
            allowed_commands=['custom_cmd'],
            blocked_commands=['blocked_cmd']
        )
        assert gateway.max_concurrent == 5
        assert gateway.default_timeout == 10.0
        assert gateway.mode == ShellMode.PERMISSIVE
        assert 'custom_cmd' in gateway.safe_commands
        assert 'blocked_cmd' in gateway.dangerous_commands
    
    def test_validate_command_safe_mode(self, safe_gateway):
        """Test command validation in safe mode."""
        # Safe command should pass
        safe_gateway._validate_command("echo hello")
        safe_gateway._validate_command("ls -la")
        
        # Dangerous command should fail
        with pytest.raises(ShellSecurityError):
            safe_gateway._validate_command("rm -rf /")
        
        # Unknown command should fail in safe mode
        with pytest.raises(ShellSecurityError):
            safe_gateway._validate_command("unknown_command")
    
    def test_validate_command_restricted_mode(self, restricted_gateway):
        """Test command validation in restricted mode."""
        # Safe command should pass
        restricted_gateway._validate_command("echo hello")
        
        # Dangerous command should fail
        with pytest.raises(ShellSecurityError):
            restricted_gateway._validate_command("rm -rf /")
        
        # Command with dangerous pattern should fail
        with pytest.raises(ShellSecurityError):
            restricted_gateway._validate_command("echo $(whoami)")
    
    def test_validate_command_permissive_mode(self, permissive_gateway):
        """Test command validation in permissive mode."""
        # Safe command should pass
        permissive_gateway._validate_command("echo hello")
        
        # Dangerous command should still fail
        with pytest.raises(ShellSecurityError):
            permissive_gateway._validate_command("rm -rf /")
        
        # Command with dangerous pattern should pass in permissive mode
        permissive_gateway._validate_command("echo $(whoami)")
    
    def test_validate_command_syntax_error(self, shell_gateway):
        """Test command validation with syntax errors."""
        with pytest.raises(ShellSecurityError, match="Invalid command syntax"):
            shell_gateway._validate_command("echo 'unclosed quote")
    
    def test_validate_command_empty(self, shell_gateway):
        """Test command validation with empty command."""
        with pytest.raises(ShellSecurityError, match="Empty command"):
            shell_gateway._validate_command("")
    
    def test_validate_working_directory(self, shell_gateway, temp_dir):
        """Test working directory validation."""
        # Unrestricted should pass
        validated = shell_gateway._validate_working_directory(temp_dir)
        assert validated == temp_dir.resolve()
        
        # Restricted should fail outside allowed paths
        restricted = ShellGateway(allowed_paths=[temp_dir])
        with pytest.raises(ShellPermissionError):
            restricted._validate_working_directory('/etc')
    
    def test_is_subpath(self, shell_gateway):
        """Test subpath checking."""
        parent = Path('/home/user')
        child = Path('/home/user/documents')
        not_child = Path('/etc')
        
        assert shell_gateway._is_subpath(child, parent) is True
        assert shell_gateway._is_subpath(not_child, parent) is False
    
    def test_execute_simple_command(self, shell_gateway):
        """Test executing a simple command."""
        result = shell_gateway.execute("echo hello")
        assert result.success is True
        assert result.return_code == 0
        assert "hello" in result.stdout
        assert result.command == "echo hello"
        assert result.duration > 0
    
    def test_execute_command_with_cwd(self, shell_gateway, temp_dir):
        """Test executing command with working directory."""
        # Create a test file
        test_file = temp_dir / 'test.txt'
        test_file.write_text('content')
        
        result = shell_gateway.execute("ls test.txt", cwd=temp_dir)
        assert result.success is True
        assert "test.txt" in result.stdout
    
    def test_execute_command_with_env(self, shell_gateway):
        """Test executing command with environment variables."""
        result = shell_gateway.execute("echo $TEST_VAR", env={'TEST_VAR': 'test_value'})
        assert result.success is True
        assert "test_value" in result.stdout
    
    def test_execute_command_with_input(self, shell_gateway):
        """Test executing command with input data."""
        result = shell_gateway.execute("cat", input_data="hello world")
        assert result.success is True
        assert "hello world" in result.stdout
    
    def test_execute_command_timeout(self, shell_gateway):
        """Test command timeout."""
        with pytest.raises(ShellTimeoutError):
            shell_gateway.execute("sleep 10", timeout=0.1, check_security=False)
    
    def test_execute_command_not_found(self, shell_gateway):
        """Test executing non-existent command."""
        result = shell_gateway.execute("nonexistent_command_xyz", check_security=False)
        assert result.success is False
        assert result.return_code == 127
        assert "command not found" in result.stderr.lower()
    
    def test_execute_command_security_bypass(self, shell_gateway):
        """Test bypassing security checks."""
        # This should fail with security check
        with pytest.raises(ShellSecurityError):
            shell_gateway.execute("rm -rf /tmp/test")
        
        # This should pass without security check
        result = shell_gateway.execute("echo test", check_security=False)
        assert result.success is True
    
    def test_execute_many_commands(self, shell_gateway):
        """Test executing multiple commands concurrently."""
        commands = ["echo 1", "echo 2", "echo 3"]
        results = shell_gateway.execute_many(commands)
        
        assert len(results) == 3
        assert all(result.success for result in results)
        
        # Check that all commands were executed
        outputs = [result.stdout.strip() for result in results]
        assert set(outputs) == {"1", "2", "3"}
    
    def test_execute_many_empty_list(self, shell_gateway):
        """Test executing empty command list."""
        results = shell_gateway.execute_many([])
        assert results == []
    
    def test_execute_many_with_failure(self, shell_gateway):
        """Test executing multiple commands with some failures."""
        commands = ["echo success", "false", "echo success2"]
        results = shell_gateway.execute_many(commands, check_security=False)
        
        assert len(results) == 3
        # Results may be in different order due to concurrency
        success_results = [r for r in results if r.success]
        failure_results = [r for r in results if not r.success]
        
        assert len(success_results) == 2
        assert len(failure_results) == 1
        assert failure_results[0].command == "false"
    
    def test_execute_pipeline_success(self, shell_gateway):
        """Test successful pipeline execution."""
        commands = ["echo hello world", "grep hello", "wc -w"]
        result = shell_gateway.execute_pipeline(commands)
        
        assert result.success is True
        assert "2" in result.stdout  # word count (hello world = 2 words)
    
    def test_execute_pipeline_failure(self, shell_gateway):
        """Test pipeline with failure."""
        commands = ["echo hello", "false", "echo world"]
        result = shell_gateway.execute_pipeline(commands, check_security=False)
        
        assert result.success is False
        assert "Pipeline failed at step 2" in result.stderr
    
    def test_execute_pipeline_empty(self, shell_gateway):
        """Test pipeline with empty commands."""
        with pytest.raises(ValueError, match="No commands provided"):
            shell_gateway.execute_pipeline([])
    
    def test_kill_all_processes(self, shell_gateway):
        """Test killing all active processes."""
        # This test is tricky because processes finish quickly
        # We'll test the interface exists
        killed = shell_gateway.kill_all()
        assert isinstance(killed, int)
        assert killed >= 0
    
    def test_get_active_count(self, shell_gateway):
        """Test getting active process count."""
        count = shell_gateway.get_active_count()
        assert isinstance(count, int)
        assert count >= 0
    
    def test_context_manager(self):
        """Test ShellGateway as context manager."""
        with ShellGateway() as gateway:
            result = gateway.execute("echo test")
            assert result.success is True
        
        # Gateway should be shut down after context
        assert gateway._executor._shutdown is True
    
    def test_convenience_methods(self, shell_gateway, temp_dir):
        """Test convenience methods."""
        # Create test file
        test_file = temp_dir / 'test.txt'
        test_file.write_text('hello world\ntest line')
        
        # Test ls
        result = shell_gateway.ls(temp_dir)
        assert result.success is True
        assert 'test.txt' in result.stdout
        
        # Test cat
        result = shell_gateway.cat(test_file)
        assert result.success is True
        assert 'hello world' in result.stdout
        
        # Test grep
        result = shell_gateway.grep('hello', test_file)
        assert result.success is True
        assert 'hello world' in result.stdout
        
        # Test find
        result = shell_gateway.find(temp_dir, '*.txt')
        assert result.success is True
        assert 'test.txt' in result.stdout
    
    def test_git_convenience_method(self, shell_gateway, temp_dir):
        """Test git convenience method."""
        # Initialize git repo
        shell_gateway.execute("git init", cwd=temp_dir, check_security=False)
        
        # Test git method
        result = shell_gateway.git("status", cwd=temp_dir)
        assert result.success is True
        assert "On branch" in result.stdout
    
    def test_python_convenience_method(self, shell_gateway, temp_dir):
        """Test python convenience method."""
        # Create test script
        script = temp_dir / 'test.py'
        script.write_text('print("hello from python")')
        
        result = shell_gateway.python(str(script), cwd=temp_dir)
        assert result.success is True
        assert "hello from python" in result.stdout
    
    def test_shutdown(self, shell_gateway):
        """Test gateway shutdown."""
        shell_gateway.shutdown()
        assert shell_gateway._executor._shutdown is True
    
    def test_concurrency_control(self):
        """Test that concurrency is properly controlled."""
        gateway = ShellGateway(max_concurrent=2)
        
        # Submit more commands than max_concurrent
        commands = ["sleep 0.1"] * 5
        start_time = time.time()
        results = gateway.execute_many(commands, check_security=False)
        duration = time.time() - start_time
        
        # Should take longer than if all ran simultaneously
        assert len(results) == 5
        assert all(result.success for result in results)
        # With max_concurrent=2, 5 commands should take at least 3 batches
        assert duration > 0.2  # At least 2 batches of 0.1s each
        
        gateway.shutdown()
    
    @pytest.mark.skipif(os.name == 'nt', reason="Signal handling different on Windows")
    def test_process_cleanup_on_timeout(self, shell_gateway):
        """Test that processes are properly cleaned up on timeout."""
        initial_count = shell_gateway.get_active_count()
        
        try:
            shell_gateway.execute("sleep 10", timeout=0.1, check_security=False)
        except ShellTimeoutError:
            pass
        
        # Process should be cleaned up
        final_count = shell_gateway.get_active_count()
        assert final_count == initial_count
    
    def test_path_command_extraction(self, shell_gateway):
        """Test extracting command from path."""
        # Command with path should extract base command
        with pytest.raises(ShellSecurityError):
            shell_gateway._validate_command("/bin/rm file.txt")
    
    def test_dangerous_pattern_detection(self, restricted_gateway):
        """Test detection of dangerous patterns."""
        dangerous_commands = [
            "echo $(whoami)",
            "echo `whoami`",
            "echo test && rm file",
            "echo test || rm file",
            "echo test; rm file",
            "echo test | rm file",
            "echo test > file",
            "echo test >> file",
            "echo test < file"
        ]
        
        for cmd in dangerous_commands:
            with pytest.raises(ShellSecurityError):
                restricted_gateway._validate_command(cmd)
    
    def test_safe_commands_list(self, shell_gateway):
        """Test that safe commands are properly defined."""
        safe_commands = shell_gateway.safe_commands
        
        # Should include common safe commands
        assert 'ls' in safe_commands
        assert 'cat' in safe_commands
        assert 'echo' in safe_commands
        assert 'git' in safe_commands
        assert 'python3' in safe_commands
    
    def test_dangerous_commands_list(self, shell_gateway):
        """Test that dangerous commands are properly defined."""
        dangerous_commands = shell_gateway.dangerous_commands
        
        # Should include dangerous commands
        assert 'rm' in dangerous_commands
        assert 'sudo' in dangerous_commands
        assert 'kill' in dangerous_commands
        assert 'shutdown' in dangerous_commands
    
    def test_command_allowlist_extension(self):
        """Test extending allowed commands."""
        gateway = ShellGateway(allowed_commands=['custom_tool'])
        assert 'custom_tool' in gateway.safe_commands
        
        # Should be able to use custom command
        gateway._validate_command('custom_tool --help')
    
    def test_command_blocklist_extension(self):
        """Test extending blocked commands."""
        gateway = ShellGateway(blocked_commands=['git'])
        assert 'git' in gateway.dangerous_commands
        
        # Should not be able to use blocked command
        with pytest.raises(ShellSecurityError):
            gateway._validate_command('git status')
    
    def test_result_properties(self, shell_gateway):
        """Test ShellResult properties."""
        result = shell_gateway.execute("echo test")
        
        assert hasattr(result, 'command')
        assert hasattr(result, 'return_code')
        assert hasattr(result, 'stdout')
        assert hasattr(result, 'stderr')
        assert hasattr(result, 'duration')
        assert hasattr(result, 'success')
        assert hasattr(result, 'pid')
    
    def test_execute_with_restricted_path(self, temp_dir):
        """Test execution with path restrictions."""
        allowed_dir = temp_dir / 'allowed'
        allowed_dir.mkdir()
        
        gateway = ShellGateway(allowed_paths=[allowed_dir])
        
        # Should work in allowed directory
        result = gateway.execute("pwd", cwd=allowed_dir)
        assert result.success is True
        
        # Should fail outside allowed directory
        with pytest.raises(ShellPermissionError):
            gateway.execute("pwd", cwd=temp_dir)
    
    def test_pipeline_with_path_restrictions(self, temp_dir):
        """Test pipeline execution with path restrictions."""
        allowed_dir = temp_dir / 'allowed'
        allowed_dir.mkdir()
        
        gateway = ShellGateway(allowed_paths=[allowed_dir])
        
        # Should work in allowed directory
        result = gateway.execute_pipeline(["echo test", "cat"], cwd=allowed_dir)
        assert result.success is True
        
        # Should fail outside allowed directory
        with pytest.raises(ShellPermissionError):
            gateway.execute_pipeline(["echo test", "cat"], cwd=temp_dir)