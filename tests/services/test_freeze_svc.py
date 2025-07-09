import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.services.freeze_svc import FreezeSvc
from src.domain.freeze_snapshot import FreezeSnapshot
from src.domain.repo import Repo as DomainRepo
from git import InvalidGitRepositoryError


class TestFreezeSvc:
    """Test suite for FreezeSvc."""
    
    @pytest.fixture
    def temp_snapshots_dir(self):
        """Create a temporary directory for snapshots."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def freeze_svc(self, temp_snapshots_dir):
        """Create a FreezeSvc instance with temporary snapshots directory."""
        return FreezeSvc(snapshots_dir=temp_snapshots_dir)
    
    @pytest.fixture
    def mock_repo(self):
        """Create a mock DomainRepo."""
        return DomainRepo(name="test-repo", path="/path/to/repo")
    
    @pytest.fixture
    def mock_git_repo(self):
        """Create a mock GitPython Repo."""
        mock_repo = Mock()
        mock_repo.head.commit.hexsha = "abc123def456"
        mock_repo.active_branch.name = "main"
        mock_repo.is_dirty.return_value = False
        mock_repo.untracked_files = []
        mock_repo.git.stash = Mock()
        mock_repo.head.reset = Mock()
        return mock_repo
    
    def test_init_creates_snapshots_directory(self, temp_snapshots_dir):
        """Test that FreezeSvc creates snapshots directory on initialization."""
        snapshots_dir = temp_snapshots_dir / "custom_snapshots"
        freeze_svc = FreezeSvc(snapshots_dir=snapshots_dir)
        
        assert snapshots_dir.exists()
        assert snapshots_dir.is_dir()
        assert freeze_svc.snapshots_dir == snapshots_dir
    
    def test_init_uses_default_snapshots_directory(self):
        """Test that FreezeSvc uses default snapshots directory when none provided."""
        with patch('pathlib.Path.home') as mock_home, \
             patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_home.return_value = Path("/mock/home")
            
            freeze_svc = FreezeSvc()
            
            expected_path = Path("/mock/home") / ".loom" / "snapshots"
            assert freeze_svc.snapshots_dir == expected_path
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    @patch('src.services.freeze_svc.Repo')
    def test_create_freeze_success(self, mock_repo_class, freeze_svc, mock_repo, mock_git_repo):
        """Test successful freeze creation."""
        mock_repo_class.return_value = mock_git_repo
        
        with patch('src.services.freeze_svc.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value.strftime.return_value = "20240101_120000"
            mock_datetime.datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
            
            result = freeze_svc.create_freeze([mock_repo], "test-tag")
            
            assert isinstance(result, FreezeSnapshot)
            assert result.repos == {"test-repo": "abc123def456"}
            assert result.bom_hash  # Should have a BOM hash
            
            # Verify snapshot file was created
            snapshot_files = list(freeze_svc.snapshots_dir.glob("*.json"))
            assert len(snapshot_files) == 1
            
            # Verify snapshot file contents
            with open(snapshot_files[0], 'r') as f:
                snapshot_data = json.load(f)
            
            assert snapshot_data["id"] == "test-tag_20240101_120000"
            assert snapshot_data["tag"] == "test-tag"
            assert snapshot_data["bom_hash"] == result.bom_hash
            assert "test-repo" in snapshot_data["repositories"]
    
    @patch('src.services.freeze_svc.Repo')
    def test_create_freeze_invalid_git_repo(self, mock_repo_class, freeze_svc, mock_repo):
        """Test freeze creation with invalid git repository."""
        mock_repo_class.side_effect = InvalidGitRepositoryError("Not a git repo")
        
        with pytest.raises(InvalidGitRepositoryError, match="'/path/to/repo' is not a valid git repository"):
            freeze_svc.create_freeze([mock_repo], "test-tag")
    
    @patch('src.services.freeze_svc.Repo')
    def test_create_freeze_duplicate_tag(self, mock_repo_class, freeze_svc, mock_repo, mock_git_repo):
        """Test freeze creation with duplicate tag."""
        mock_repo_class.return_value = mock_git_repo
        
        with patch('src.services.freeze_svc.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value.strftime.return_value = "20240101_120000"
            mock_datetime.datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
            
            # Create first freeze
            freeze_svc.create_freeze([mock_repo], "test-tag")
            
            # Try to create duplicate - should raise ValueError
            with pytest.raises(ValueError, match="Freeze snapshot with tag 'test-tag' already exists"):
                freeze_svc.create_freeze([mock_repo], "test-tag")
    
    @patch('src.services.freeze_svc.Repo')
    def test_checkout_success(self, mock_repo_class, freeze_svc, mock_repo, mock_git_repo):
        """Test successful freeze checkout."""
        mock_repo_class.return_value = mock_git_repo
        
        # Create a freeze first
        with patch('src.services.freeze_svc.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value.strftime.return_value = "20240101_120000"
            mock_datetime.datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
            
            freeze_svc.create_freeze([mock_repo], "test-tag")
            
            # Now checkout the freeze
            result = freeze_svc.checkout("test-tag_20240101_120000", [mock_repo])
            
            assert result["restored"] == ["test-repo: restored to abc123de"]
            assert result["skipped"] == []
            assert result["errors"] == []
            
            # Verify git operations were called
            mock_git_repo.head.reset.assert_called_once_with("abc123def456", index=True, working_tree=True)
    
    @patch('src.services.freeze_svc.Repo')
    def test_checkout_with_dirty_repo(self, mock_repo_class, freeze_svc, mock_repo, mock_git_repo):
        """Test checkout with dirty repository (should stash changes)."""
        mock_git_repo.is_dirty.return_value = True
        mock_git_repo.untracked_files = ["untracked.txt"]
        mock_repo_class.return_value = mock_git_repo
        
        # Create a freeze first
        with patch('src.services.freeze_svc.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value.strftime.return_value = "20240101_120000"
            mock_datetime.datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
            
            freeze_svc.create_freeze([mock_repo], "test-tag")
            
            # Make repo dirty for checkout
            mock_git_repo.is_dirty.return_value = True
            
            # Now checkout the freeze
            result = freeze_svc.checkout("test-tag_20240101_120000", [mock_repo])
            
            assert result["restored"] == ["test-repo: restored to abc123de"]
            
            # Verify stash was called
            mock_git_repo.git.stash.assert_called_once()
    
    def test_checkout_nonexistent_freeze(self, freeze_svc, mock_repo):
        """Test checkout with nonexistent freeze ID."""
        with pytest.raises(FileNotFoundError, match="Freeze snapshot 'nonexistent' not found"):
            freeze_svc.checkout("nonexistent", [mock_repo])
    
    @patch('src.services.freeze_svc.Repo')
    def test_checkout_repo_not_in_freeze(self, mock_repo_class, freeze_svc, mock_git_repo):
        """Test checkout with repo not in freeze snapshot."""
        mock_repo_class.return_value = mock_git_repo
        
        # Create freeze with one repo
        repo1 = DomainRepo(name="repo1", path="/path/to/repo1")
        repo2 = DomainRepo(name="repo2", path="/path/to/repo2")
        
        with patch('src.services.freeze_svc.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value.strftime.return_value = "20240101_120000"
            mock_datetime.datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
            
            freeze_svc.create_freeze([repo1], "test-tag")
            
            # Try to checkout with repo not in freeze
            result = freeze_svc.checkout("test-tag_20240101_120000", [repo2])
            
            assert result["restored"] == []
            assert result["skipped"] == ["repo2: not in freeze snapshot"]
            assert result["errors"] == []
    
    @patch('src.services.freeze_svc.Repo')
    def test_checkout_with_error(self, mock_repo_class, freeze_svc, mock_repo, mock_git_repo):
        """Test checkout with git error during restoration."""
        mock_repo_class.return_value = mock_git_repo
        
        # Create freeze first
        with patch('src.services.freeze_svc.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value.strftime.return_value = "20240101_120000"
            mock_datetime.datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
            
            freeze_svc.create_freeze([mock_repo], "test-tag")
            
            # Make reset fail
            mock_git_repo.head.reset.side_effect = Exception("Git error")
            
            result = freeze_svc.checkout("test-tag_20240101_120000", [mock_repo])
            
            assert result["restored"] == []
            assert result["skipped"] == []
            assert result["errors"] == ["test-repo: Git error"]
    
    def test_list_freezes_empty(self, freeze_svc):
        """Test listing freezes when none exist."""
        result = freeze_svc.list_freezes()
        assert result == []
    
    @patch('src.services.freeze_svc.Repo')
    def test_list_freezes_with_data(self, mock_repo_class, freeze_svc, mock_repo, mock_git_repo):
        """Test listing freezes with existing data."""
        mock_repo_class.return_value = mock_git_repo
        
        with patch('src.services.freeze_svc.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value.strftime.return_value = "20240101_120000"
            mock_datetime.datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
            
            freeze_svc.create_freeze([mock_repo], "test-tag")
            
            result = freeze_svc.list_freezes()
            
            assert len(result) == 1
            assert result[0]["id"] == "test-tag_20240101_120000"
            assert result[0]["tag"] == "test-tag"
            assert result[0]["repo_count"] == 1
            assert "bom_hash" in result[0]
            assert "created_at" in result[0]
    
    def test_list_freezes_ignores_invalid_files(self, freeze_svc, temp_snapshots_dir):
        """Test that list_freezes ignores invalid JSON files."""
        # Create invalid JSON file
        invalid_file = temp_snapshots_dir / "invalid.json"
        invalid_file.write_text("invalid json")
        
        # Create file with missing keys
        incomplete_file = temp_snapshots_dir / "incomplete.json"
        incomplete_file.write_text('{"id": "test"}')
        
        result = freeze_svc.list_freezes()
        assert result == []
    
    def test_delete_freeze_success(self, freeze_svc, temp_snapshots_dir):
        """Test successful freeze deletion."""
        # Create a freeze file
        freeze_file = temp_snapshots_dir / "test_freeze.json"
        freeze_file.write_text('{"id": "test_freeze", "tag": "test"}')
        
        result = freeze_svc.delete_freeze("test_freeze")
        
        assert result is True
        assert not freeze_file.exists()
    
    def test_delete_freeze_nonexistent(self, freeze_svc):
        """Test deletion of nonexistent freeze."""
        result = freeze_svc.delete_freeze("nonexistent")
        assert result is False
    
    @patch('src.services.freeze_svc.Repo')
    def test_create_freeze_with_multiple_repos(self, mock_repo_class, freeze_svc, mock_git_repo):
        """Test freeze creation with multiple repositories."""
        # Create multiple repos
        repo1 = DomainRepo(name="repo1", path="/path/to/repo1")
        repo2 = DomainRepo(name="repo2", path="/path/to/repo2")
        
        # Mock different commits for each repo
        mock_git_repo1 = Mock()
        mock_git_repo1.head.commit.hexsha = "commit1"
        mock_git_repo1.active_branch.name = "main"
        mock_git_repo1.is_dirty.return_value = False
        mock_git_repo1.untracked_files = []
        
        mock_git_repo2 = Mock()
        mock_git_repo2.head.commit.hexsha = "commit2"
        mock_git_repo2.active_branch.name = "develop"
        mock_git_repo2.is_dirty.return_value = True
        mock_git_repo2.untracked_files = ["file.txt"]
        
        mock_repo_class.side_effect = [mock_git_repo1, mock_git_repo2]
        
        with patch('src.services.freeze_svc.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value.strftime.return_value = "20240101_120000"
            mock_datetime.datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
            
            result = freeze_svc.create_freeze([repo1, repo2], "multi-repo-tag")
            
            assert result.repos == {"repo1": "commit1", "repo2": "commit2"}
            
            # Verify snapshot file contains both repos
            snapshot_files = list(freeze_svc.snapshots_dir.glob("*.json"))
            assert len(snapshot_files) == 1
            
            with open(snapshot_files[0], 'r') as f:
                snapshot_data = json.load(f)
            
            assert len(snapshot_data["repositories"]) == 2
            assert "repo1" in snapshot_data["repositories"]
            assert "repo2" in snapshot_data["repositories"]
            assert snapshot_data["repositories"]["repo1"]["branch"] == "main"
            assert snapshot_data["repositories"]["repo2"]["branch"] == "develop"
            assert snapshot_data["repositories"]["repo2"]["is_dirty"] is True