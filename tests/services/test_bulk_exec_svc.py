"""Unit tests for BulkExecSvc."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import subprocess
from pathlib import Path

from src.services.bulk_exec_svc import BulkExecSvc, CommandResult
from src.domain.repo import Repo
from src.domain.foundry import Foundry


class TestBulkExecSvc(unittest.TestCase):
    """Test suite for BulkExecSvc."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock repositories
        self.repo1 = Repo(name="repo1", path="/test/repo1")
        self.repo2 = Repo(name="repo2", path="/test/repo2")
        self.repo3 = Repo(name="repo3", path="/test/repo3")
        
        # Create mock foundry
        self.foundry = Mock(spec=Foundry)
        self.foundry.all_repos.return_value = [self.repo1, self.repo2, self.repo3]
        
        # Create service instances
        self.service = BulkExecSvc()
        self.service_with_foundry = BulkExecSvc(foundry=self.foundry)

    def test_init(self):
        """Test service initialization."""
        service = BulkExecSvc()
        self.assertIsNone(service.foundry)
        
        service_with_foundry = BulkExecSvc(foundry=self.foundry)
        self.assertEqual(service_with_foundry.foundry, self.foundry)

    @patch('src.services.bulk_exec_svc.Path')
    @patch('src.services.bulk_exec_svc.subprocess.run')
    def test_run_single_repo_success(self, mock_run, mock_path):
        """Test running command in single repository successfully."""
        # Setup mocks
        mock_path_obj = Mock()
        mock_path.return_value = mock_path_obj
        mock_path_obj.expanduser.return_value = mock_path_obj
        mock_path_obj.resolve.return_value = mock_path_obj
        mock_path_obj.exists.return_value = True
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Success output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        # Execute
        results = self.service.run("echo test", repos=[self.repo1])
        
        # Verify
        self.assertEqual(len(results), 1)
        self.assertIn("repo1", results)
        result = results["repo1"]
        self.assertTrue(result.success)
        self.assertEqual(result.stdout, "Success output")
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.return_code, 0)

    @patch('src.services.bulk_exec_svc.Path')
    @patch('src.services.bulk_exec_svc.subprocess.run')
    def test_run_multiple_repos_parallel(self, mock_run, mock_path):
        """Test running command in multiple repositories in parallel."""
        # Setup path mocks for each repo
        repo_paths = {
            "/test/repo1": "repo1",
            "/test/repo2": "repo2", 
            "/test/repo3": "repo3"
        }
        
        def mock_path_func(path):
            mock_path_obj = Mock()
            mock_path_obj.expanduser.return_value = mock_path_obj
            mock_path_obj.resolve.return_value = mock_path_obj
            mock_path_obj.exists.return_value = True
            mock_path_obj.__str__ = lambda self: path
            return mock_path_obj
        
        mock_path.side_effect = mock_path_func
        
        def mock_subprocess_run(*args, **kwargs):
            mock_result = Mock()
            cwd = kwargs.get('cwd')
            # Identify repo based on cwd
            if cwd and str(cwd) == "/test/repo1":
                mock_result.returncode = 0
                mock_result.stdout = "repo1 output"
                mock_result.stderr = ""
            elif cwd and str(cwd) == "/test/repo2":
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = "repo2 error"
            elif cwd and str(cwd) == "/test/repo3":
                mock_result.returncode = 0
                mock_result.stdout = "repo3 output"
                mock_result.stderr = ""
            else:
                # Default case
                mock_result.returncode = 0
                mock_result.stdout = "unknown repo"
                mock_result.stderr = ""
            return mock_result
        
        mock_run.side_effect = mock_subprocess_run
        
        # Execute
        results = self.service.run("test command", repos=[self.repo1, self.repo2, self.repo3])
        
        # Verify
        self.assertEqual(len(results), 3)
        
        # Check repo1 succeeded
        self.assertTrue(results["repo1"].success)
        self.assertEqual(results["repo1"].stdout, "repo1 output")
        
        # Check repo2 failed
        self.assertFalse(results["repo2"].success)
        self.assertEqual(results["repo2"].stderr, "repo2 error")
        self.assertEqual(results["repo2"].return_code, 1)
        
        # Check repo3 succeeded
        self.assertTrue(results["repo3"].success)
        self.assertEqual(results["repo3"].stdout, "repo3 output")

    def test_run_with_no_repos_error(self):
        """Test running command with no repositories specified."""
        with self.assertRaises(ValueError) as context:
            self.service.run("echo test")
        
        self.assertIn("No repositories specified", str(context.exception))

    def test_run_with_foundry_repos(self):
        """Test running command using foundry's repositories."""
        with patch('src.services.bulk_exec_svc.Path') as mock_path:
            with patch('src.services.bulk_exec_svc.subprocess.run') as mock_run:
                # Setup mocks
                mock_path_obj = Mock()
                mock_path.return_value = mock_path_obj
                mock_path_obj.expanduser.return_value = mock_path_obj
                mock_path_obj.resolve.return_value = mock_path_obj
                mock_path_obj.exists.return_value = True
                
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "Success"
                mock_result.stderr = ""
                mock_run.return_value = mock_result
                
                # Execute using foundry's repos
                results = self.service_with_foundry.run("echo test")
                
                # Verify all foundry repos were used
                self.assertEqual(len(results), 3)
                self.assertIn("repo1", results)
                self.assertIn("repo2", results)
                self.assertIn("repo3", results)

    @patch('src.services.bulk_exec_svc.Path')
    def test_run_with_non_existent_repo(self, mock_path):
        """Test running command in non-existent repository."""
        # Setup mock to simulate non-existent directory
        mock_path_obj = Mock()
        mock_path.return_value = mock_path_obj
        mock_path_obj.expanduser.return_value = mock_path_obj
        mock_path_obj.resolve.return_value = mock_path_obj
        mock_path_obj.exists.return_value = False
        
        # Execute
        results = self.service.run("echo test", repos=[self.repo1])
        
        # Verify
        self.assertEqual(len(results), 1)
        result = results["repo1"]
        self.assertFalse(result.success)
        self.assertIn("does not exist", result.stderr)
        self.assertEqual(result.return_code, -1)

    @patch('src.services.bulk_exec_svc.Path')
    @patch('src.services.bulk_exec_svc.subprocess.run')
    def test_run_with_timeout(self, mock_run, mock_path):
        """Test command timeout handling."""
        # Setup mocks
        mock_path_obj = Mock()
        mock_path.return_value = mock_path_obj
        mock_path_obj.expanduser.return_value = mock_path_obj
        mock_path_obj.resolve.return_value = mock_path_obj
        mock_path_obj.exists.return_value = True
        
        # Simulate timeout
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 300)
        
        # Execute
        results = self.service.run("sleep 600", repos=[self.repo1])
        
        # Verify
        result = results["repo1"]
        self.assertFalse(result.success)
        self.assertIn("timed out", result.stderr)
        self.assertEqual(result.error, "TimeoutExpired")

    @patch('src.services.bulk_exec_svc.Path')
    @patch('src.services.bulk_exec_svc.subprocess.run')
    def test_run_with_aggregation(self, mock_run, mock_path):
        """Test run_with_aggregation method."""
        # Setup path mocks
        def mock_path_func(path):
            mock_path_obj = Mock()
            mock_path_obj.expanduser.return_value = mock_path_obj
            mock_path_obj.resolve.return_value = mock_path_obj
            mock_path_obj.exists.return_value = True
            mock_path_obj.__str__ = lambda self: path
            return mock_path_obj
        
        mock_path.side_effect = mock_path_func
        
        def mock_subprocess_run(*args, **kwargs):
            mock_result = Mock()
            cwd = kwargs.get('cwd')
            # repo1 and repo3 succeed, repo2 fails
            if cwd and str(cwd) == "/test/repo2":
                mock_result.returncode = 1
                mock_result.stdout = ""
                mock_result.stderr = "error"
            else:
                mock_result.returncode = 0
                mock_result.stdout = "success"
                mock_result.stderr = ""
            return mock_result
        
        mock_run.side_effect = mock_subprocess_run
        
        # Execute
        aggregated = self.service.run_with_aggregation(
            "test command", 
            repos=[self.repo1, self.repo2, self.repo3]
        )
        
        # Verify structure
        self.assertIn("results", aggregated)
        self.assertIn("successful", aggregated)
        self.assertIn("failed", aggregated)
        self.assertIn("summary", aggregated)
        
        # Verify content
        self.assertEqual(set(aggregated["successful"]), {"repo1", "repo3"})
        self.assertEqual(aggregated["failed"], ["repo2"])
        
        summary = aggregated["summary"]
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["succeeded"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertAlmostEqual(summary["success_rate"], 2/3)

    def test_empty_repos_list(self):
        """Test with empty repository list."""
        results = self.service.run("echo test", repos=[])
        self.assertEqual(results, {})

    @patch('src.services.bulk_exec_svc.Path')
    def test_cwd_relative_false(self, mock_path):
        """Test running command without changing to repo directory."""
        with patch('src.services.bulk_exec_svc.subprocess.run') as mock_run:
            # Setup mocks
            mock_path_obj = Mock()
            mock_path.return_value = mock_path_obj
            mock_path_obj.expanduser.return_value = mock_path_obj
            mock_path_obj.resolve.return_value = mock_path_obj
            mock_path_obj.exists.return_value = True
            
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Success"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            # Execute with cwd_relative=False
            results = self.service.run("pwd", repos=[self.repo1], cwd_relative=False)
            
            # Verify subprocess.run was called with cwd=None
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            self.assertIsNone(call_kwargs['cwd'])


if __name__ == '__main__':
    unittest.main()