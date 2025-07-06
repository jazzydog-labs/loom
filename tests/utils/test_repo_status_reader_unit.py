#!/usr/bin/env python3
"""Unit tests for RepoStatusReader using mocks for proper isolation."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from pathlib import Path
from git import exc

from src.utils.repo_status_reader import RepoStatusReader


class TestRepoStatusReader(unittest.TestCase):
    """Unit tests for RepoStatusReader class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_repo_path = "/test/repo/path"
        
    @patch('src.utils.repo_status_reader.Repo')
    @patch('src.utils.repo_status_reader.pathlib.Path')
    def test_init(self, mock_path, mock_repo):
        """Test RepoStatusReader initialization."""
        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.expanduser.return_value = mock_path_instance
        mock_path_instance.resolve.return_value = mock_path_instance
        
        reader = RepoStatusReader(self.test_repo_path)
        
        mock_path.assert_called_once_with(self.test_repo_path)
        mock_path_instance.expanduser.assert_called_once()
        mock_path_instance.resolve.assert_called_once()
        mock_repo.assert_called_once_with(mock_path_instance)

    @patch('src.utils.repo_status_reader.Repo')
    @patch('src.utils.repo_status_reader.pathlib.Path')
    def test_get_summary_json_clean_repo(self, mock_path, mock_repo):
        """Test get_summary_json with clean repository."""
        # Setup mocks
        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.expanduser.return_value = mock_path_instance
        mock_path_instance.resolve.return_value = mock_path_instance
        
        mock_repo_instance = Mock()
        mock_repo.return_value = mock_repo_instance
        
        # Mock commit
        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_commit.message = "Test commit message\n"
        mock_repo_instance.head.commit = mock_commit
        
        # Mock branch
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo_instance.active_branch = mock_branch
        
        # Mock clean repo
        mock_repo_instance.is_dirty.return_value = False
        
        # Mock ahead/behind counts
        mock_repo_instance.iter_commits.side_effect = [
            [1, 2],  # ahead commits
            [3]      # behind commits
        ]
        
        # Mock changes
        mock_repo_instance.index.diff.side_effect = [
            [],  # staged files (HEAD diff)
            []   # unstaged files (None diff)
        ]
        mock_repo_instance.untracked_files = []
        
        # Test
        reader = RepoStatusReader(self.test_repo_path)
        result = reader.get_summary_json()
        
        # Assertions
        expected = {
            "branch": "main",
            "clean": True,
            "ahead": 2,
            "behind": 1,
            "last_commit": {
                "sha": "abc123def456",
                "message": "Test commit message"
            },
            "changes": {
                "staged": [],
                "unstaged": [],
                "untracked": []
            }
        }
        
        self.assertEqual(result, expected)
        mock_repo_instance.is_dirty.assert_called_once_with(untracked_files=True)

    @patch('src.utils.repo_status_reader.Repo')
    @patch('src.utils.repo_status_reader.pathlib.Path')
    def test_get_summary_json_dirty_repo(self, mock_path, mock_repo):
        """Test get_summary_json with dirty repository."""
        # Setup mocks
        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.expanduser.return_value = mock_path_instance
        mock_path_instance.resolve.return_value = mock_path_instance
        
        mock_repo_instance = Mock()
        mock_repo.return_value = mock_repo_instance
        
        # Mock commit
        mock_commit = Mock()
        mock_commit.hexsha = "def456abc123"
        mock_commit.message = "Another commit"
        mock_repo_instance.head.commit = mock_commit
        
        # Mock branch
        mock_branch = Mock()
        mock_branch.name = "feature-branch"
        mock_repo_instance.active_branch = mock_branch
        
        # Mock dirty repo
        mock_repo_instance.is_dirty.return_value = True
        
        # Mock ahead/behind counts
        mock_repo_instance.iter_commits.side_effect = [
            [],   # ahead commits
            [1, 2, 3]  # behind commits
        ]
        
        # Mock changes with files
        mock_staged_diff = Mock()
        mock_staged_diff.a_path = "staged_file.py"
        mock_unstaged_diff = Mock()
        mock_unstaged_diff.a_path = "unstaged_file.py"
        
        mock_repo_instance.index.diff.side_effect = [
            [mock_staged_diff],    # staged files
            [mock_unstaged_diff]   # unstaged files
        ]
        mock_repo_instance.untracked_files = ["untracked_file.txt"]
        
        # Test
        reader = RepoStatusReader(self.test_repo_path)
        result = reader.get_summary_json()
        
        # Assertions
        expected = {
            "branch": "feature-branch",
            "clean": False,
            "ahead": 0,
            "behind": 3,
            "last_commit": {
                "sha": "def456abc123",
                "message": "Another commit"
            },
            "changes": {
                "staged": ["staged_file.py"],
                "unstaged": ["unstaged_file.py"],
                "untracked": ["untracked_file.txt"]
            }
        }
        
        self.assertEqual(result, expected)

    @patch('src.utils.repo_status_reader.Repo')
    @patch('src.utils.repo_status_reader.pathlib.Path')
    def test_get_summary_json_no_upstream(self, mock_path, mock_repo):
        """Test get_summary_json when no upstream is configured."""
        # Setup mocks
        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.expanduser.return_value = mock_path_instance
        mock_path_instance.resolve.return_value = mock_path_instance
        
        mock_repo_instance = Mock()
        mock_repo.return_value = mock_repo_instance
        
        # Mock commit
        mock_commit = Mock()
        mock_commit.hexsha = "no_upstream_sha"
        mock_commit.message = "No upstream commit"
        mock_repo_instance.head.commit = mock_commit
        
        # Mock branch
        mock_branch = Mock()
        mock_branch.name = "local-only"
        mock_repo_instance.active_branch = mock_branch
        
        # Mock clean repo
        mock_repo_instance.is_dirty.return_value = False
        
        # Mock GitCommandError for no upstream
        mock_repo_instance.iter_commits.side_effect = exc.GitCommandError("No upstream", 128)
        
        # Mock changes
        mock_repo_instance.index.diff.side_effect = [[], []]
        mock_repo_instance.untracked_files = []
        
        # Test
        reader = RepoStatusReader(self.test_repo_path)
        result = reader.get_summary_json()
        
        # Assertions - should default to 0 for ahead/behind
        self.assertEqual(result["ahead"], 0)
        self.assertEqual(result["behind"], 0)
        self.assertEqual(result["branch"], "local-only")

    @patch('src.utils.repo_status_reader.Repo')
    @patch('src.utils.repo_status_reader.pathlib.Path')
    def test_get_summary_json_value_error(self, mock_path, mock_repo):
        """Test get_summary_json when ValueError is raised."""
        # Setup mocks
        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.expanduser.return_value = mock_path_instance
        mock_path_instance.resolve.return_value = mock_path_instance
        
        mock_repo_instance = Mock()
        mock_repo.return_value = mock_repo_instance
        
        # Mock commit
        mock_commit = Mock()
        mock_commit.hexsha = "value_error_sha"
        mock_commit.message = "Value error commit"
        mock_repo_instance.head.commit = mock_commit
        
        # Mock branch
        mock_branch = Mock()
        mock_branch.name = "error-branch"
        mock_repo_instance.active_branch = mock_branch
        
        # Mock clean repo
        mock_repo_instance.is_dirty.return_value = False
        
        # Mock ValueError for upstream comparison
        mock_repo_instance.iter_commits.side_effect = ValueError("Invalid reference")
        
        # Mock changes
        mock_repo_instance.index.diff.side_effect = [[], []]
        mock_repo_instance.untracked_files = []
        
        # Test
        reader = RepoStatusReader(self.test_repo_path)
        result = reader.get_summary_json()
        
        # Assertions - should default to 0 for ahead/behind
        self.assertEqual(result["ahead"], 0)
        self.assertEqual(result["behind"], 0)

    @patch('src.utils.repo_status_reader.Repo')
    @patch('src.utils.repo_status_reader.pathlib.Path')
    def test_get_summary_json_multiple_files(self, mock_path, mock_repo):
        """Test get_summary_json with multiple files in different states."""
        # Setup mocks
        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.expanduser.return_value = mock_path_instance
        mock_path_instance.resolve.return_value = mock_path_instance
        
        mock_repo_instance = Mock()
        mock_repo.return_value = mock_repo_instance
        
        # Mock commit
        mock_commit = Mock()
        mock_commit.hexsha = "multi_file_sha"
        mock_commit.message = "Multiple files commit\n\nWith body"
        mock_repo_instance.head.commit = mock_commit
        
        # Mock branch
        mock_branch = Mock()
        mock_branch.name = "multi-file-branch"
        mock_repo_instance.active_branch = mock_branch
        
        # Mock dirty repo
        mock_repo_instance.is_dirty.return_value = True
        
        # Mock ahead/behind counts
        mock_repo_instance.iter_commits.side_effect = [
            [1, 2, 3, 4, 5],  # ahead commits
            []                # behind commits
        ]
        
        # Mock changes with multiple files
        mock_staged_diffs = [Mock(), Mock()]
        mock_staged_diffs[0].a_path = "file1.py"
        mock_staged_diffs[1].a_path = "file2.py"
        
        mock_unstaged_diffs = [Mock(), Mock(), Mock()]
        mock_unstaged_diffs[0].a_path = "file3.py"
        mock_unstaged_diffs[1].a_path = "file4.py"
        mock_unstaged_diffs[2].a_path = "file5.py"
        
        mock_repo_instance.index.diff.side_effect = [
            mock_staged_diffs,    # staged files
            mock_unstaged_diffs   # unstaged files
        ]
        mock_repo_instance.untracked_files = ["new1.txt", "new2.txt"]
        
        # Test
        reader = RepoStatusReader(self.test_repo_path)
        result = reader.get_summary_json()
        
        # Assertions
        self.assertEqual(result["ahead"], 5)
        self.assertEqual(result["behind"], 0)
        self.assertEqual(result["changes"]["staged"], ["file1.py", "file2.py"])
        self.assertEqual(result["changes"]["unstaged"], ["file3.py", "file4.py", "file5.py"])
        self.assertEqual(result["changes"]["untracked"], ["new1.txt", "new2.txt"])
        self.assertEqual(result["last_commit"]["message"], "Multiple files commit\n\nWith body")

    def test_json_serializable_output(self):
        """Test that get_summary_json returns JSON-serializable output."""
        with patch('src.utils.repo_status_reader.Repo') as mock_repo, \
             patch('src.utils.repo_status_reader.pathlib.Path') as mock_path:
            
            # Setup basic mocks
            mock_path_instance = Mock()
            mock_path.return_value = mock_path_instance
            mock_path_instance.expanduser.return_value = mock_path_instance
            mock_path_instance.resolve.return_value = mock_path_instance
            
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            
            # Mock commit
            mock_commit = Mock()
            mock_commit.hexsha = "json_test_sha"
            mock_commit.message = "JSON test"
            mock_repo_instance.head.commit = mock_commit
            
            # Mock branch
            mock_branch = Mock()
            mock_branch.name = "json-test"
            mock_repo_instance.active_branch = mock_branch
            
            # Mock other values
            mock_repo_instance.is_dirty.return_value = False
            mock_repo_instance.iter_commits.side_effect = [[], []]
            mock_repo_instance.index.diff.side_effect = [[], []]
            mock_repo_instance.untracked_files = []
            
            # Test
            reader = RepoStatusReader(self.test_repo_path)
            result = reader.get_summary_json()
            
            # Should not raise an exception
            json_string = json.dumps(result)
            self.assertIsInstance(json_string, str)
            
            # Should be able to parse back
            parsed = json.loads(json_string)
            self.assertEqual(parsed, result)


if __name__ == "__main__":
    unittest.main() 