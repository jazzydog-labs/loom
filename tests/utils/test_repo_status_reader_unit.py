#!/usr/bin/env python3
"""Unit tests for RepoStatusReader."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
from pathlib import Path
import os

from utils.repo_status_reader import RepoStatusReader


class TestRepoStatusReader(unittest.TestCase):
    """Test cases for RepoStatusReader class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "test_repo"
        self.repo_path.mkdir()
        
        # Create a mock .git directory to make it look like a Git repository
        (self.repo_path / ".git").mkdir()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_init_with_valid_repo(self):
        """Test initialization with a valid repository path."""
        reader = RepoStatusReader(str(self.repo_path))
        self.assertEqual(reader.repo_root, self.repo_path.resolve())
    
    def test_init_with_nonexistent_path(self):
        """Test initialization with a non-existent path."""
        nonexistent_path = Path(self.temp_dir) / "nonexistent"
        with self.assertRaises(ValueError) as context:
            RepoStatusReader(str(nonexistent_path))
        self.assertIn("does not exist", str(context.exception))
    
    def test_init_with_non_git_repo(self):
        """Test initialization with a directory that's not a Git repository."""
        non_git_dir = Path(self.temp_dir) / "non_git"
        non_git_dir.mkdir()
        
        with self.assertRaises(ValueError) as context:
            RepoStatusReader(str(non_git_dir))
        self.assertIn("Not a Git repository", str(context.exception))
    
    @patch('src.utils.repo_status_reader.subprocess.run')
    def test_file_status_success(self, mock_run):
        """Test file_status() with successful Git output."""
        # Mock successful git status output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """M  src/main.py
A  new_file.txt
 M README.md
?? temp.log
D  old_file.txt
R  old_name.py -> new_name.py
UU conflicted_file.py"""
        mock_run.return_value = mock_result
        
        reader = RepoStatusReader(str(self.repo_path))
        result = reader.file_status()
        
        # Verify the structure
        expected_keys = {"staged", "modified", "untracked", "deleted", "renamed", "unmerged"}
        self.assertEqual(set(result.keys()), expected_keys)
        
        # Verify staged files
        self.assertEqual(len(result["staged"]), 3)  # M, A, D
        staged_paths = {item["path"] for item in result["staged"]}
        self.assertIn("src/main.py", staged_paths)
        self.assertIn("new_file.txt", staged_paths)
        self.assertIn("old_file.txt", staged_paths)
        
        # Verify modified files
        self.assertEqual(len(result["modified"]), 1)
        self.assertEqual(result["modified"][0]["path"], "README.md")
        
        # Verify untracked files
        self.assertEqual(len(result["untracked"]), 1)
        self.assertEqual(result["untracked"][0]["path"], "temp.log")
        
        # Verify renamed files
        self.assertEqual(len(result["renamed"]), 1)
        renamed = result["renamed"][0]
        self.assertEqual(renamed["path"], "new_name.py")
        self.assertEqual(renamed["original_path"], "old_name.py")
        
        # Verify unmerged files
        self.assertEqual(len(result["unmerged"]), 1)
        self.assertEqual(result["unmerged"][0]["path"], "conflicted_file.py")
    
    @patch('src.utils.repo_status_reader.subprocess.run')
    def test_file_status_failure(self, mock_run):
        """Test file_status() with Git command failure."""
        # Mock failed git status
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "fatal: not a git repository"
        mock_run.return_value = mock_result
        
        reader = RepoStatusReader(str(self.repo_path))
        result = reader.file_status()
        
        # Should return empty structure
        expected_keys = {"staged", "modified", "untracked", "deleted", "renamed", "unmerged"}
        self.assertEqual(set(result.keys()), expected_keys)
        for key in expected_keys:
            self.assertEqual(result[key], [])
    
    @patch('src.utils.repo_status_reader.subprocess.run')
    def test_repo_status_success(self, mock_run):
        """Test repo_status() with successful Git output."""
        # Mock multiple git commands
        def mock_run_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if cmd == ["git", "branch", "--show-current"]:
                mock_result.returncode = 0
                mock_result.stdout = "main\n"
            elif cmd == ["git", "log", "-1", "--format=%H%n%s"]:
                mock_result.returncode = 0
                mock_result.stdout = "a1b2c3d4e5f6789012345678901234567890abcd\nfeat: add new feature\n"
            elif cmd == ["git", "status", "--porcelain"]:
                mock_result.returncode = 0
                mock_result.stdout = "M  src/main.py\n"  # Not clean
            elif cmd == ["git", "rev-list", "--count", "--left-right", "@{u}...HEAD"]:
                mock_result.returncode = 0
                mock_result.stdout = "2\t1\n"  # 2 behind, 1 ahead
            elif cmd == ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]:
                mock_result.returncode = 0
                mock_result.stdout = "origin/main\n"
            else:
                mock_result.returncode = 1
                mock_result.stderr = "Unknown command"
            return mock_result
        
        mock_run.side_effect = mock_run_side_effect
        
        reader = RepoStatusReader(str(self.repo_path))
        result = reader.repo_status()
        
        # Verify the structure
        expected_keys = {"branch", "is_clean", "last_commit_sha", "last_commit_message", 
                        "ahead_count", "behind_count", "upstream_branch"}
        self.assertEqual(set(result.keys()), expected_keys)
        
        # Verify values
        self.assertEqual(result["branch"], "main")
        self.assertFalse(result["is_clean"])
        self.assertEqual(result["last_commit_sha"], "a1b2c3d4e5f6789012345678901234567890abcd")
        self.assertEqual(result["last_commit_message"], "feat: add new feature")
        self.assertEqual(result["ahead_count"], 1)
        self.assertEqual(result["behind_count"], 2)
        self.assertEqual(result["upstream_branch"], "origin/main")
    
    @patch('src.utils.repo_status_reader.subprocess.run')
    def test_repo_status_clean_repo(self, mock_run):
        """Test repo_status() with a clean repository."""
        def mock_run_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if cmd == ["git", "branch", "--show-current"]:
                mock_result.returncode = 0
                mock_result.stdout = "main\n"
            elif cmd == ["git", "log", "-1", "--format=%H%n%s"]:
                mock_result.returncode = 0
                mock_result.stdout = "a1b2c3d4e5f6789012345678901234567890abcd\nfeat: add new feature\n"
            elif cmd == ["git", "status", "--porcelain"]:
                mock_result.returncode = 0
                mock_result.stdout = ""  # Clean repository
            elif cmd == ["git", "rev-list", "--count", "--left-right", "@{u}...HEAD"]:
                mock_result.returncode = 0
                mock_result.stdout = "0\t0\n"  # Up to date
            elif cmd == ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]:
                mock_result.returncode = 0
                mock_result.stdout = "origin/main\n"
            else:
                mock_result.returncode = 1
                mock_result.stderr = "Unknown command"
            return mock_result
        
        mock_run.side_effect = mock_run_side_effect
        
        reader = RepoStatusReader(str(self.repo_path))
        result = reader.repo_status()
        
        self.assertTrue(result["is_clean"])
        self.assertEqual(result["ahead_count"], 0)
        self.assertEqual(result["behind_count"], 0)
    
    @patch('src.utils.repo_status_reader.subprocess.run')
    def test_repo_status_no_upstream(self, mock_run):
        """Test repo_status() with no upstream branch."""
        def mock_run_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if cmd == ["git", "branch", "--show-current"]:
                mock_result.returncode = 0
                mock_result.stdout = "main\n"
            elif cmd == ["git", "log", "-1", "--format=%H%n%s"]:
                mock_result.returncode = 0
                mock_result.stdout = "a1b2c3d4e5f6789012345678901234567890abcd\nfeat: add new feature\n"
            elif cmd == ["git", "status", "--porcelain"]:
                mock_result.returncode = 0
                mock_result.stdout = ""
            elif cmd == ["git", "rev-list", "--count", "--left-right", "@{u}...HEAD"]:
                mock_result.returncode = 128  # No upstream
                mock_result.stdout = ""
            elif cmd == ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]:
                mock_result.returncode = 128  # No upstream
                mock_result.stdout = ""
            else:
                mock_result.returncode = 1
                mock_result.stderr = "Unknown command"
            return mock_result
        
        mock_run.side_effect = mock_run_side_effect
        
        reader = RepoStatusReader(str(self.repo_path))
        result = reader.repo_status()
        
        self.assertEqual(result["ahead_count"], 0)
        self.assertEqual(result["behind_count"], 0)
        self.assertIsNone(result["upstream_branch"])
    
    @patch('src.utils.repo_status_reader.subprocess.run')
    def test_repo_status_git_failure(self, mock_run):
        """Test repo_status() with Git command failures."""
        # Mock failed git commands
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "fatal: not a git repository"
        mock_run.return_value = mock_result
        
        reader = RepoStatusReader(str(self.repo_path))
        result = reader.repo_status()
        
        # Should return error indicator
        self.assertIn("error", result)
    
    @patch('src.utils.repo_status_reader.subprocess.run')
    def test_summary(self, mock_run):
        """Test summary() method."""
        # Mock all the git commands needed for summary
        def mock_run_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if cmd == ["git", "status", "--porcelain", "--ignored=matching"]:
                mock_result.returncode = 0
                mock_result.stdout = """M  src/main.py
A  new_file.txt
 M README.md
?? temp.log"""
            elif cmd == ["git", "branch", "--show-current"]:
                mock_result.returncode = 0
                mock_result.stdout = "main\n"
            elif cmd == ["git", "log", "-1", "--format=%H%n%s"]:
                mock_result.returncode = 0
                mock_result.stdout = "a1b2c3d4e5f6789012345678901234567890abcd\nfeat: add new feature\n"
            elif cmd == ["git", "status", "--porcelain"]:
                mock_result.returncode = 0
                mock_result.stdout = "M  src/main.py\n"
            elif cmd == ["git", "rev-list", "--count", "--left-right", "@{u}...HEAD"]:
                mock_result.returncode = 0
                mock_result.stdout = "0\t1\n"
            elif cmd == ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]:
                mock_result.returncode = 0
                mock_result.stdout = "origin/main\n"
            else:
                mock_result.returncode = 1
                mock_result.stderr = "Unknown command"
            return mock_result
        
        mock_run.side_effect = mock_run_side_effect
        
        reader = RepoStatusReader(str(self.repo_path))
        result = reader.summary()
        
        # Verify the structure
        expected_keys = {"repository_path", "file_status", "file_counts", "repo_status", "timestamp"}
        self.assertEqual(set(result.keys()), expected_keys)
        
        # Verify repository path (handle macOS /private/var vs /var symlink)
        actual_path = Path(result["repository_path"]).resolve()
        expected_path = self.repo_path.resolve()
        self.assertEqual(actual_path, expected_path)
        
        # Verify file counts
        file_counts = result["file_counts"]
        self.assertEqual(file_counts["staged"], 2)  # M, A
        self.assertEqual(file_counts["modified"], 1)  # M
        self.assertEqual(file_counts["untracked"], 1)  # ??
        self.assertEqual(file_counts["deleted"], 0)
        self.assertEqual(file_counts["renamed"], 0)
        self.assertEqual(file_counts["unmerged"], 0)
        
        # Verify repo status
        repo_status = result["repo_status"]
        self.assertEqual(repo_status["branch"], "main")
        self.assertFalse(repo_status["is_clean"])
        self.assertEqual(repo_status["ahead_count"], 1)
        self.assertEqual(repo_status["behind_count"], 0)
    
    @patch('src.utils.repo_status_reader.subprocess.run')
    def test_execute_git_command_timeout(self, mock_run):
        """Test _execute_git_command with timeout."""
        from subprocess import TimeoutExpired
        
        mock_run.side_effect = TimeoutExpired(["git", "status"], 30)
        
        reader = RepoStatusReader(str(self.repo_path))
        success, stdout, stderr = reader._execute_git_command(["status"])
        
        self.assertFalse(success)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "Command timed out")
    
    @patch('src.utils.repo_status_reader.subprocess.run')
    def test_execute_git_command_exception(self, mock_run):
        """Test _execute_git_command with exception."""
        mock_run.side_effect = Exception("Unexpected error")
        
        reader = RepoStatusReader(str(self.repo_path))
        success, stdout, stderr = reader._execute_git_command(["status"])
        
        self.assertFalse(success)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "Unexpected error")


class TestRepoStatusReaderIntegration(unittest.TestCase):
    """Integration tests for RepoStatusReader with real Git commands."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "test_repo"
        self.repo_path.mkdir()
        
        # Initialize a real Git repository
        import subprocess
        subprocess.run(["git", "init"], cwd=self.repo_path, check=True)
        
        # Create a test file and commit it
        (self.repo_path / "test.txt").write_text("Hello, World!")
        subprocess.run(["git", "add", "test.txt"], cwd=self.repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.repo_path, check=True)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_real_git_repository(self):
        """Test with a real Git repository."""
        reader = RepoStatusReader(str(self.repo_path))
        
        # Test file_status with clean repo
        file_status = reader.file_status()
        self.assertEqual(len(file_status["staged"]), 0)
        self.assertEqual(len(file_status["modified"]), 0)
        self.assertEqual(len(file_status["untracked"]), 0)
        
        # Test repo_status
        repo_status = reader.repo_status()
        self.assertTrue(repo_status["is_clean"])
        self.assertIsNotNone(repo_status["last_commit_sha"])
        self.assertEqual(repo_status["last_commit_message"], "Initial commit")
        
        # Test summary
        summary = reader.summary()
        actual_path = Path(summary["repository_path"]).resolve()
        expected_path = self.repo_path.resolve()
        self.assertEqual(actual_path, expected_path)
        self.assertTrue(summary["repo_status"]["is_clean"])
    
    def test_real_git_repository_with_changes(self):
        """Test with a real Git repository that has changes."""
        # Create a new file
        (self.repo_path / "new_file.txt").write_text("New content")
        
        # Modify existing file
        (self.repo_path / "test.txt").write_text("Modified content")
        
        reader = RepoStatusReader(str(self.repo_path))
        
        # Test file_status with changes
        file_status = reader.file_status()
        
        # Should have at least one untracked file (new_file.txt)
        self.assertGreaterEqual(len(file_status["untracked"]), 1)
        
        # Should have changes (either modified or staged)
        total_changes = (len(file_status["modified"]) + 
                        len(file_status["staged"]) + 
                        len(file_status["untracked"]))
        self.assertGreater(total_changes, 0)
        
        # Test repo_status
        repo_status = reader.repo_status()
        self.assertFalse(repo_status["is_clean"])
        
        # Test summary
        summary = reader.summary()
        total_file_changes = sum(summary["file_counts"].values())
        self.assertGreater(total_file_changes, 0)


if __name__ == "__main__":
    print("This test module is intended to be run with pytest.\nUse: just test or pytest from the loom directory.") 