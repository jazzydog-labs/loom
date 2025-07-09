import pytest
from unittest.mock import Mock, patch, MagicMock, call
import subprocess
import os
import time

from src.infra.git_gateway import GitGateway, GitCommandError


class TestGitGateway:
    """Test suite for GitGateway."""
    
    @pytest.fixture
    def git_gateway(self):
        """Create a GitGateway instance."""
        with patch.object(GitGateway, '_find_git_executable', return_value='/usr/bin/git'):
            return GitGateway()
    
    @pytest.fixture
    def mock_subprocess_run(self):
        """Mock subprocess.run for testing."""
        with patch('subprocess.run') as mock_run:
            yield mock_run
    
    def test_init_default_configuration(self):
        """Test GitGateway initialization with default configuration."""
        with patch.object(GitGateway, '_find_git_executable', return_value='/usr/bin/git'):
            gateway = GitGateway()
            assert gateway.retry_count == 3
            assert gateway.retry_delay == 1.0
            assert gateway._git_executable == '/usr/bin/git'
    
    def test_init_custom_configuration(self):
        """Test GitGateway initialization with custom configuration."""
        with patch.object(GitGateway, '_find_git_executable', return_value='/usr/bin/git'):
            gateway = GitGateway(retry_count=5, retry_delay=2.0)
            assert gateway.retry_count == 5
            assert gateway.retry_delay == 2.0
    
    def test_find_git_executable_success(self):
        """Test finding git executable successfully."""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            gateway = GitGateway()
            assert gateway._git_executable == 'git'
            mock_run.assert_called_once_with(['git', '--version'], 
                                            capture_output=True, 
                                            text=True, 
                                            timeout=5)
    
    def test_find_git_executable_fallback(self):
        """Test finding git executable with fallback paths."""
        def side_effect(cmd, **kwargs):
            if cmd[0] == 'git':
                raise FileNotFoundError()
            elif cmd[0] == '/usr/bin/git':
                result = Mock()
                result.returncode = 0
                return result
            raise FileNotFoundError()
        
        with patch('subprocess.run', side_effect=side_effect):
            gateway = GitGateway()
            assert gateway._git_executable == '/usr/bin/git'
    
    def test_find_git_executable_not_found(self):
        """Test error when git executable is not found."""
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            with pytest.raises(RuntimeError, match="Git executable not found"):
                GitGateway()
    
    def test_run_simple_command_success(self, git_gateway, mock_subprocess_run):
        """Test running a simple git command successfully."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "branch output"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.run(['branch'])
        
        assert result['command'] == '/usr/bin/git branch'
        assert result['args'] == ['branch']
        assert result['return_code'] == 0
        assert result['stdout'] == "branch output"
        assert result['stderr'] == ""
        assert result['success'] is True
        
        mock_subprocess_run.assert_called_once_with(
            ['/usr/bin/git', 'branch'],
            cwd=None,
            input=None,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            timeout=None
        )
    
    def test_run_command_with_cwd(self, git_gateway, mock_subprocess_run):
        """Test running command with working directory."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "status output"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.run(['status'], cwd='/path/to/repo')
        
        assert result['success'] is True
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args
        assert call_args[1]['cwd'] == '/path/to/repo'
    
    def test_run_command_with_path_object(self, git_gateway, mock_subprocess_run):
        """Test running command with Path object as cwd."""
        from pathlib import Path
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.run(['status'], cwd=Path('/path/to/repo'))
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args
        assert call_args[1]['cwd'] == '/path/to/repo'
    
    def test_run_command_failure_with_check(self, git_gateway, mock_subprocess_run):
        """Test command failure with check=True."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error: pathspec 'nonexistent' did not match"
        mock_subprocess_run.return_value = mock_result
        
        with pytest.raises(GitCommandError) as exc_info:
            git_gateway.run(['checkout', 'nonexistent'], check=True)
        
        error = exc_info.value
        assert error.return_code == 1
        assert error.command == '/usr/bin/git checkout nonexistent'
        assert 'nonexistent' in error.stderr
    
    def test_run_command_failure_without_check(self, git_gateway, mock_subprocess_run):
        """Test command failure with check=False."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error message"
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.run(['checkout', 'nonexistent'], check=False)
        
        assert result['success'] is False
        assert result['return_code'] == 1
        assert result['stderr'] == "error message"
    
    def test_run_command_with_timeout(self, git_gateway, mock_subprocess_run):
        """Test running command with timeout."""
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired('cmd', 30)
        
        with pytest.raises(subprocess.TimeoutExpired):
            git_gateway.run(['clone', 'large-repo'], timeout=30)
    
    def test_run_command_with_retry_on_lock_error(self, git_gateway, mock_subprocess_run):
        """Test retry logic on lock errors."""
        # First attempt fails with lock error
        mock_result1 = Mock()
        mock_result1.returncode = 1
        mock_result1.stdout = ""
        mock_result1.stderr = "fatal: Unable to create '.git/index.lock': File exists."
        
        # Second attempt succeeds
        mock_result2 = Mock()
        mock_result2.returncode = 0
        mock_result2.stdout = "success"
        mock_result2.stderr = ""
        
        mock_subprocess_run.side_effect = [mock_result1, mock_result2]
        
        with patch('time.sleep') as mock_sleep:  # Mock sleep to speed up test
            result = git_gateway.run(['add', '.'])
        
        assert result['success'] is True
        assert result['stdout'] == "success"
        assert mock_subprocess_run.call_count == 2
        mock_sleep.assert_called_once_with(1.0)
    
    def test_run_command_retry_exhausted(self, git_gateway, mock_subprocess_run):
        """Test when all retries are exhausted."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "fatal: cannot lock ref"
        
        mock_subprocess_run.return_value = mock_result
        
        with patch('time.sleep'):
            with pytest.raises(GitCommandError):
                git_gateway.run(['push'])
        
        assert mock_subprocess_run.call_count == 3  # Default retry count
    
    def test_run_command_no_retry(self, git_gateway, mock_subprocess_run):
        """Test command with retry=False."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "fatal: cannot lock ref"
        
        mock_subprocess_run.return_value = mock_result
        
        with pytest.raises(GitCommandError):
            git_gateway.run(['push'], retry=False)
        
        assert mock_subprocess_run.call_count == 1  # No retries
    
    def test_status_command(self, git_gateway, mock_subprocess_run):
        """Test status convenience method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "M file.txt"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.status('/repo/path')
        
        assert result['success'] is True
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ['/usr/bin/git', 'status', '--porcelain']
    
    def test_add_command(self, git_gateway, mock_subprocess_run):
        """Test add convenience method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.add(['file1.txt', 'file2.txt'], '/repo/path')
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ['/usr/bin/git', 'add', 'file1.txt', 'file2.txt']
    
    def test_commit_command(self, git_gateway, mock_subprocess_run):
        """Test commit convenience method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "[main abc123] Test commit"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.commit("Test commit", '/repo/path')
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ['/usr/bin/git', 'commit', '-m', 'Test commit']
    
    def test_commit_amend(self, git_gateway, mock_subprocess_run):
        """Test commit with amend option."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "[main abc123] Test commit"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.commit("Test commit", '/repo/path', amend=True, no_edit=True)
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ['/usr/bin/git', 'commit', '-m', 'Test commit', '--amend', '--no-edit']
    
    def test_push_command(self, git_gateway, mock_subprocess_run):
        """Test push convenience method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Everything up-to-date"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.push('/repo/path', branch='main', force=True)
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ['/usr/bin/git', 'push', 'origin', 'main', '--force']
    
    def test_pull_command(self, git_gateway, mock_subprocess_run):
        """Test pull convenience method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Already up to date."
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.pull('/repo/path', branch='main', rebase=True)
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ['/usr/bin/git', 'pull', 'origin', 'main', '--rebase']
    
    def test_clone_command(self, git_gateway, mock_subprocess_run):
        """Test clone convenience method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Cloning into 'repo'..."
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.clone('https://github.com/user/repo.git', '/path/to/repo', depth=1)
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ['/usr/bin/git', 'clone', 'https://github.com/user/repo.git', '/path/to/repo', '--depth', '1']
    
    def test_checkout_command(self, git_gateway, mock_subprocess_run):
        """Test checkout convenience method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Switched to branch 'feature'"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.checkout('feature', '/repo/path', create=True)
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ['/usr/bin/git', 'checkout', '-b', 'feature']
    
    def test_branch_command(self, git_gateway, mock_subprocess_run):
        """Test branch convenience method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "* main\n  feature"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.branch('/repo/path', all_branches=True)
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ['/usr/bin/git', 'branch', '-a']
    
    def test_log_command(self, git_gateway, mock_subprocess_run):
        """Test log convenience method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123 Initial commit"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.log('/repo/path', oneline=True, limit=10, since="2024-01-01")
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ['/usr/bin/git', 'log', '--oneline', '-n', '10', '--since', '2024-01-01']
    
    def test_diff_command(self, git_gateway, mock_subprocess_run):
        """Test diff convenience method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "file1.txt\nfile2.txt"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.diff('/repo/path', cached=True, name_only=True)
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ['/usr/bin/git', 'diff', '--cached', '--name-only']
    
    def test_stash_command(self, git_gateway, mock_subprocess_run):
        """Test stash convenience method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Saved working directory"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.stash('/repo/path', message="WIP", include_untracked=True)
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ['/usr/bin/git', 'stash', 'save', 'WIP', '-u']
    
    def test_remote_command(self, git_gateway, mock_subprocess_run):
        """Test remote convenience method."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "origin\tupstream"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        result = git_gateway.remote('/repo/path', verbose=True)
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ['/usr/bin/git', 'remote', '-v']
    
    def test_should_retry_patterns(self, git_gateway):
        """Test _should_retry method with various error patterns."""
        # Test lock error
        result = Mock()
        result.stderr = "fatal: Unable to create '.git/index.lock': File exists."
        assert git_gateway._should_retry(result) is True
        
        # Test cannot lock ref
        result.stderr = "error: cannot lock ref 'refs/heads/main'"
        assert git_gateway._should_retry(result) is True
        
        # Test resource unavailable
        result.stderr = "fatal: resource temporarily unavailable"
        assert git_gateway._should_retry(result) is True
        
        # Test another git process
        result.stderr = "Another git process seems to be running"
        assert git_gateway._should_retry(result) is True
        
        # Test non-retryable error
        result.stderr = "fatal: not a git repository"
        assert git_gateway._should_retry(result) is False
    
    def test_environment_variables(self, git_gateway, mock_subprocess_run):
        """Test passing environment variables."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        custom_env = {'GIT_AUTHOR_NAME': 'Test User'}
        result = git_gateway.run(['commit', '-m', 'test'], env=custom_env)
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[1]
        assert 'GIT_AUTHOR_NAME' in call_args['env']
        assert call_args['env']['GIT_AUTHOR_NAME'] == 'Test User'
    
    def test_input_data(self, git_gateway, mock_subprocess_run):
        """Test passing input data to command."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Applied patch"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        patch_data = "diff --git a/file.txt b/file.txt\n..."
        result = git_gateway.run(['apply', '-'], input_data=patch_data)
        
        assert result['success'] is True
        call_args = mock_subprocess_run.call_args[1]
        assert call_args['input'] == patch_data