"""Unit tests for RepoStatusService."""

import unittest
from unittest.mock import Mock, MagicMock, patch
import json

from src.services.repo_status_service import RepoStatusService


class TestRepoStatusService(unittest.TestCase):
    """Test suite for RepoStatusService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = RepoStatusService()

    @patch('src.services.repo_status_service.Repo')
    def test_status_clean_repo(self, mock_repo_class):
        """Test status method with a clean repository."""
        # Setup mock repository
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        # Configure mock
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_branch.tracking_branch.return_value = None
        mock_repo.active_branch = mock_branch
        
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_commit.message = "Initial commit"
        mock_repo.head.commit = mock_commit
        
        mock_repo.is_dirty.return_value = False
        mock_repo.untracked_files = []
        mock_repo.index.diff.return_value = []
        
        # Call the method
        result = self.service.status("/path/to/repo")
        
        # Assertions
        self.assertIn('repo_status', result)
        self.assertIn('file_status', result)
        self.assertIn('file_counts', result)
        
        repo_status = result['repo_status']
        self.assertEqual(repo_status['branch'], 'main')
        self.assertTrue(repo_status['is_clean'])
        self.assertEqual(repo_status['ahead_count'], 0)
        self.assertEqual(repo_status['behind_count'], 0)

    @patch('src.services.repo_status_service.Repo')
    def test_status_with_error(self, mock_repo_class):
        """Test status method when repository access fails."""
        # Make Repo constructor raise an exception
        mock_repo_class.side_effect = Exception("Repository not found")
        
        # Call the method
        result = self.service.status("/invalid/path")
        
        # Assertions
        self.assertIn('repo_status', result)
        self.assertIn('error', result['repo_status'])
        self.assertEqual(result['repo_status']['error'], "Repository not found")

    @patch('src.services.repo_status_service.ThreadPoolExecutor')
    @patch('src.services.repo_status_service.as_completed')
    def test_summaries_parallel(self, mock_as_completed, mock_executor_class):
        """Test parallel summary fetching."""
        # Setup
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Create mock futures
        future1 = Mock()
        future1.result.return_value = ("repo1", {"repo_status": {"branch": "main"}})
        future2 = Mock()
        future2.result.return_value = ("repo2", {"repo_status": {"branch": "develop"}})
        
        mock_as_completed.return_value = [future1, future2]
        
        # Mock the status method
        with patch.object(self.service, 'status') as mock_status:
            mock_status.side_effect = [
                {"repo_status": {"branch": "main"}},
                {"repo_status": {"branch": "develop"}}
            ]
            
            # Call the method
            repo_paths = {"repo1": "/path1", "repo2": "/path2"}
            result = self.service.summaries_parallel(repo_paths)
        
        # Assertions
        self.assertEqual(len(result), 2)
        self.assertIn("repo1", result)
        self.assertIn("repo2", result)

    def test_transform_for_view(self):
        """Test the transformation of raw data for view."""
        raw_data = {
            "branch": "feature/test",
            "clean": False,
            "ahead": 2,
            "behind": 1,
            "last_commit": {
                "sha": "def456",
                "message": "Add feature"
            },
            "changes": {
                "staged": ["file1.py"],
                "unstaged": ["file2.py", "file3.py"],
                "untracked": ["file4.txt"]
            },
            "remote_name": "origin",
            "upstream_branch": "origin/feature/test"
        }
        
        result = self.service._transform_for_view(raw_data)
        
        # Check repo_status
        repo_status = result['repo_status']
        self.assertEqual(repo_status['branch'], 'feature/test')
        self.assertFalse(repo_status['is_clean'])
        self.assertEqual(repo_status['ahead_count'], 2)
        self.assertEqual(repo_status['behind_count'], 1)
        self.assertEqual(repo_status['last_commit_message'], 'Add feature')
        self.assertEqual(repo_status['upstream_branch'], 'origin/feature/test')
        
        # Check file counts
        file_counts = result['file_counts']
        self.assertEqual(file_counts['staged'], 1)
        self.assertEqual(file_counts['modified'], 2)
        self.assertEqual(file_counts['untracked'], 1)


if __name__ == '__main__':
    unittest.main()