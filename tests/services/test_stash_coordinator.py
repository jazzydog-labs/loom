import pytest
from unittest.mock import Mock, patch, MagicMock, call
from git import GitCommandError, InvalidGitRepositoryError

from src.services.stash_coordinator import StashCoordinator
from src.domain.repo import Repo as DomainRepo


class TestStashCoordinator:
    """Test suite for StashCoordinator."""
    
    @pytest.fixture
    def stash_coordinator(self):
        """Create a StashCoordinator instance."""
        return StashCoordinator()
    
    @pytest.fixture
    def mock_repos(self):
        """Create mock repository objects."""
        return [
            DomainRepo(name="repo1", path="/path/to/repo1"),
            DomainRepo(name="repo2", path="/path/to/repo2"),
            DomainRepo(name="repo3", path="/path/to/repo3")
        ]
    
    @pytest.fixture
    def mock_git_repo(self):
        """Create a mock GitPython Repo."""
        mock_repo = Mock()
        mock_repo.is_dirty.return_value = False
        mock_repo.untracked_files = []
        mock_repo.git.stash = Mock()
        return mock_repo
    
    @patch('src.services.stash_coordinator.Repo')
    def test_stash_all_clean_repos(self, mock_repo_class, stash_coordinator, mock_repos, mock_git_repo):
        """Test stashing when all repos are clean."""
        mock_repo_class.return_value = mock_git_repo
        
        result = stash_coordinator.stash_all(mock_repos)
        
        assert len(result["stashed"]) == 0
        assert len(result["clean"]) == 3
        assert len(result["errors"]) == 0
        
        # Verify no stash commands were called
        mock_git_repo.git.stash.assert_not_called()
    
    @patch('src.services.stash_coordinator.Repo')
    @patch('src.services.stash_coordinator.datetime')
    def test_stash_all_dirty_repos(self, mock_datetime, mock_repo_class, stash_coordinator, mock_repos):
        """Test stashing when repos have changes."""
        # Mock datetime for consistent stash messages
        mock_datetime.datetime.now.return_value.strftime.return_value = "20240101_120000"
        
        # Create different states for each repo
        mock_git_repo1 = Mock()
        mock_git_repo1.is_dirty.return_value = True
        mock_git_repo1.untracked_files = []
        mock_git_repo1.git.stash = Mock()
        
        mock_git_repo2 = Mock()
        mock_git_repo2.is_dirty.return_value = False
        mock_git_repo2.untracked_files = ["new_file.txt"]
        mock_git_repo2.git.stash = Mock()
        
        mock_git_repo3 = Mock()
        mock_git_repo3.is_dirty.return_value = False
        mock_git_repo3.untracked_files = []
        mock_git_repo3.git.stash = Mock()
        
        mock_repo_class.side_effect = [mock_git_repo1, mock_git_repo2, mock_git_repo3]
        
        result = stash_coordinator.stash_all(mock_repos)
        
        assert len(result["stashed"]) == 2  # repo1 and repo2
        assert len(result["clean"]) == 1    # repo3
        assert len(result["errors"]) == 0
        
        # Verify stash commands were called with correct message
        expected_message = "loom-stash-20240101_120000"
        mock_git_repo1.git.stash.assert_called_once_with("push", "-u", "-m", expected_message)
        mock_git_repo2.git.stash.assert_called_once_with("push", "-u", "-m", expected_message)
        mock_git_repo3.git.stash.assert_not_called()
    
    @patch('src.services.stash_coordinator.Repo')
    def test_stash_all_with_custom_message(self, mock_repo_class, stash_coordinator, mock_repos):
        """Test stashing with custom message."""
        mock_git_repo = Mock()
        mock_git_repo.is_dirty.return_value = True
        mock_git_repo.untracked_files = []
        mock_git_repo.git.stash = Mock()
        
        mock_repo_class.return_value = mock_git_repo
        
        result = stash_coordinator.stash_all(mock_repos[:1], message="feature-work")
        
        assert len(result["stashed"]) == 1
        mock_git_repo.git.stash.assert_called_once_with("push", "-u", "-m", "loom-stash-feature-work")
    
    @patch('src.services.stash_coordinator.Repo')
    def test_stash_all_invalid_repo(self, mock_repo_class, stash_coordinator, mock_repos):
        """Test stashing with invalid git repository."""
        mock_repo_class.side_effect = InvalidGitRepositoryError("Not a git repo")
        
        result = stash_coordinator.stash_all(mock_repos[:1])
        
        assert len(result["stashed"]) == 0
        assert len(result["clean"]) == 0
        assert len(result["errors"]) == 1
        assert "Not a valid git repository" in result["errors"][0]["error"]
    
    @patch('src.services.stash_coordinator.Repo')
    def test_unstash_all_no_stashes(self, mock_repo_class, stash_coordinator, mock_repos, mock_git_repo):
        """Test unstashing when no stashes exist."""
        mock_git_repo.git.stash.return_value = ""  # Empty stash list
        mock_repo_class.return_value = mock_git_repo
        
        result = stash_coordinator.unstash_all(mock_repos)
        
        assert len(result["unstashed"]) == 0
        assert len(result["no_stash"]) == 3
        assert len(result["conflicts"]) == 0
        assert len(result["errors"]) == 0
    
    @patch('src.services.stash_coordinator.Repo')
    def test_unstash_all_with_loom_stashes(self, mock_repo_class, stash_coordinator, mock_repos):
        """Test unstashing loom-created stashes."""
        mock_git_repo = Mock()
        # Mock stash list with loom stashes
        mock_git_repo.git.stash.side_effect = [
            # First call: list
            "stash@{0}: On main: loom-stash-20240101_120000\nstash@{1}: On main: manual stash",
            # Second call: apply
            None,
            # Third call: drop
            None
        ]
        
        mock_repo_class.return_value = mock_git_repo
        
        result = stash_coordinator.unstash_all(mock_repos[:1])
        
        assert len(result["unstashed"]) == 1
        assert result["unstashed"][0]["stash"] == "stash@{0}"
        assert result["unstashed"][0]["status"] == "Applied and dropped"
        
        # Verify correct stash operations
        calls = mock_git_repo.git.stash.call_args_list
        assert calls[0] == call("list")
        assert calls[1] == call("apply", "stash@{0}")
        assert calls[2] == call("drop", "stash@{0}")
    
    @patch('src.services.stash_coordinator.Repo')
    def test_unstash_all_with_conflicts(self, mock_repo_class, stash_coordinator, mock_repos):
        """Test unstashing with merge conflicts."""
        mock_git_repo = Mock()
        mock_git_repo.git.stash.side_effect = [
            # First call: list
            "stash@{0}: On main: loom-stash-conflict",
            # Second call: apply (raises conflict error)
            GitCommandError("git stash apply", 1, b"", b"CONFLICT")
        ]
        
        mock_repo_class.return_value = mock_git_repo
        
        result = stash_coordinator.unstash_all(mock_repos[:1])
        
        assert len(result["unstashed"]) == 0
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["error"] == "Merge conflicts detected"
        assert result["conflicts"][0]["resolution"] == "Manual intervention required"
    
    @patch('src.services.stash_coordinator.Repo')
    def test_list_stashes(self, mock_repo_class, stash_coordinator, mock_repos):
        """Test listing stashes across repositories."""
        # Mock different stash states
        mock_git_repo1 = Mock()
        mock_git_repo1.git.stash.return_value = (
            "stash@{0}: On main: loom-stash-20240101_120000\n"
            "stash@{1}: On feature: WIP on feature"
        )
        
        mock_git_repo2 = Mock()
        mock_git_repo2.git.stash.return_value = ""  # No stashes
        
        mock_git_repo3 = Mock()
        mock_git_repo3.git.stash.return_value = "stash@{0}: On develop: manual save"
        
        mock_repo_class.side_effect = [mock_git_repo1, mock_git_repo2, mock_git_repo3]
        
        result = stash_coordinator.list_stashes(mock_repos)
        
        assert len(result) == 2  # Only repos with stashes
        assert "repo1" in result
        assert "repo3" in result
        assert "repo2" not in result  # No stashes
        
        # Check repo1 stashes
        assert len(result["repo1"]) == 2
        assert result["repo1"][0]["ref"] == "stash@{0}"
        assert result["repo1"][0]["is_loom"] is True
        assert result["repo1"][1]["ref"] == "stash@{1}"
        assert result["repo1"][1]["is_loom"] is False
    
    @patch('src.services.stash_coordinator.Repo')
    def test_clear_loom_stashes(self, mock_repo_class, stash_coordinator, mock_repos):
        """Test clearing loom-created stashes."""
        mock_git_repo = Mock()
        mock_git_repo.git.stash.side_effect = [
            # First call: list
            (
                "stash@{0}: On main: loom-stash-20240101_120000\n"
                "stash@{1}: On main: manual stash\n"
                "stash@{2}: On main: loom-stash-20240101_110000"
            ),
            # Second call: drop stash@{2}
            None,
            # Third call: drop stash@{0}
            None
        ]
        
        mock_repo_class.return_value = mock_git_repo
        
        result = stash_coordinator.clear_loom_stashes(mock_repos[:1])
        
        assert len(result["cleared"]) == 1
        assert result["cleared"][0]["repo"] == "repo1"
        assert result["cleared"][0]["count"] == 2
        
        # Verify only loom stashes were dropped
        calls = mock_git_repo.git.stash.call_args_list
        assert calls[0] == call("list")
        assert calls[1] == call("drop", "stash@{2}")  # Dropped in reverse order
        assert calls[2] == call("drop", "stash@{0}")
    
    @patch('src.services.stash_coordinator.Repo')
    def test_clear_loom_stashes_no_loom_stashes(self, mock_repo_class, stash_coordinator, mock_repos):
        """Test clearing when no loom stashes exist."""
        mock_git_repo = Mock()
        mock_git_repo.git.stash.return_value = "stash@{0}: On main: manual stash"
        
        mock_repo_class.return_value = mock_git_repo
        
        result = stash_coordinator.clear_loom_stashes(mock_repos[:1])
        
        assert len(result["cleared"]) == 0
        assert len(result["no_stashes"]) == 1
        assert "repo1" in result["no_stashes"]
    
    @patch('src.services.stash_coordinator.Repo')
    def test_stash_status(self, mock_repo_class, stash_coordinator, mock_repos):
        """Test getting stash status across repositories."""
        # Mock different stash states
        mock_git_repo1 = Mock()
        mock_git_repo1.git.stash.return_value = (
            "stash@{0}: On main: loom-stash-20240101_120000\n"
            "stash@{1}: On feature: manual stash"
        )
        
        mock_git_repo2 = Mock()
        mock_git_repo2.git.stash.return_value = "stash@{0}: On main: loom-stash-backup"
        
        mock_git_repo3 = Mock()
        mock_git_repo3.git.stash.return_value = ""
        
        mock_repo_class.side_effect = [mock_git_repo1, mock_git_repo2, mock_git_repo3]
        
        result = stash_coordinator.stash_status(mock_repos)
        
        # Check summary
        assert result["summary"]["total_repos"] == 3
        assert result["summary"]["repos_with_stashes"] == 2
        assert result["summary"]["repos_with_loom_stashes"] == 2
        assert result["summary"]["total_stashes"] == 3
        assert result["summary"]["loom_stashes"] == 2
        
        # Check details
        assert len(result["details"]) == 2
        assert "repo1" in result["details"]
        assert "repo2" in result["details"]
    
    @patch('src.services.stash_coordinator.Repo')
    def test_unstash_with_specific_ref(self, mock_repo_class, stash_coordinator, mock_repos):
        """Test unstashing with specific stash reference."""
        mock_git_repo = Mock()
        mock_git_repo.git.stash.side_effect = [
            # First call: list
            "stash@{0}: On main: latest\nstash@{1}: On main: target",
            # Second call: apply specific stash
            None,
            # Third call: drop
            None
        ]
        
        mock_repo_class.return_value = mock_git_repo
        
        result = stash_coordinator.unstash_all(mock_repos[:1], stash_ref="stash@{1}")
        
        assert len(result["unstashed"]) == 1
        assert result["unstashed"][0]["stash"] == "stash@{1}"
        
        # Verify specific stash was applied
        calls = mock_git_repo.git.stash.call_args_list
        assert calls[1] == call("apply", "stash@{1}")
    
    @patch('src.services.stash_coordinator.Repo')
    def test_stash_all_with_exception(self, mock_repo_class, stash_coordinator, mock_repos):
        """Test stashing with general exception."""
        mock_git_repo = Mock()
        mock_git_repo.is_dirty.side_effect = Exception("Unexpected error")
        
        mock_repo_class.return_value = mock_git_repo
        
        result = stash_coordinator.stash_all(mock_repos[:1])
        
        assert len(result["errors"]) == 1
        assert result["errors"][0]["error"] == "Unexpected error"
    
    @patch('src.services.stash_coordinator.Repo')
    def test_list_stashes_with_malformed_output(self, mock_repo_class, stash_coordinator, mock_repos):
        """Test listing stashes with malformed git output."""
        mock_git_repo = Mock()
        mock_git_repo.git.stash.return_value = "malformed stash output without colons"
        
        mock_repo_class.return_value = mock_git_repo
        
        result = stash_coordinator.list_stashes(mock_repos[:1])
        
        # Should handle gracefully and return empty
        assert len(result) == 0
    
    @patch('src.services.stash_coordinator.Repo')
    def test_mixed_stash_states(self, mock_repo_class, stash_coordinator, mock_repos):
        """Test stashing with mixed states across repos."""
        # Create repos with different states
        mock_git_repo1 = Mock()
        mock_git_repo1.is_dirty.return_value = True
        mock_git_repo1.untracked_files = []
        mock_git_repo1.git.stash = Mock()
        
        mock_git_repo2 = Mock()
        mock_git_repo2.side_effect = InvalidGitRepositoryError("Not a git repo")
        
        mock_git_repo3 = Mock()
        mock_git_repo3.is_dirty.return_value = False
        mock_git_repo3.untracked_files = []
        mock_git_repo3.git.stash = Mock()
        
        mock_repo_class.side_effect = [mock_git_repo1, InvalidGitRepositoryError("Not a git repo"), mock_git_repo3]
        
        result = stash_coordinator.stash_all(mock_repos)
        
        assert len(result["stashed"]) == 1  # repo1
        assert len(result["clean"]) == 1    # repo3
        assert len(result["errors"]) == 1   # repo2
        
        assert result["stashed"][0]["repo"] == "repo1"
        assert result["clean"][0]["repo"] == "repo3"
        assert result["errors"][0]["repo"] == "repo2"