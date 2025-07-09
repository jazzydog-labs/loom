#!/usr/bin/env python3
"""Integration tests for RepoStatusService using the actual service."""

import unittest
from unittest.mock import Mock, patch
from src.services.repo_status_service import RepoStatusService


class TestRepoStatusServiceIntegration(unittest.TestCase):
    """Integration tests for RepoStatusService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = RepoStatusService()
        
    def test_init(self):
        """Test RepoStatusService initialization."""
        service = RepoStatusService()
        self.assertIsNotNone(service)

    @patch('src.services.repo_status_service.Repo')
    def test_status_with_mock_repo(self, mock_repo_class):
        """Test status method with mocked repository."""
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
        result = self.service.status("/test/repo/path")
        
        # Assertions
        self.assertIn('repo_status', result)
        self.assertIn('file_status', result)
        self.assertIn('file_counts', result)
        
        repo_status = result['repo_status']
        self.assertEqual(repo_status['branch'], 'main')
        self.assertTrue(repo_status['is_clean'])

    def test_status_with_invalid_path(self):
        """Test status method with invalid path."""
        result = self.service.status("/invalid/path")
        
        self.assertIn('repo_status', result)
        self.assertIn('error', result['repo_status'])


if __name__ == '__main__':
    unittest.main()