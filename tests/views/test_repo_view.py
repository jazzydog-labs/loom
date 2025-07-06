#!/usr/bin/env python3
"""Tests for RepoView class."""

import unittest
from unittest.mock import Mock, patch
from rich.console import Console
import tempfile
import shutil
from pathlib import Path

from src.views.repo_view import RepoView
from src.utils.repo_status_reader import RepoStatusReader


class TestRepoView(unittest.TestCase):
    """Test cases for RepoView class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "test_repo"
        self.repo_path.mkdir()
        
        # Create a mock .git directory to make it look like a Git repository
        (self.repo_path / ".git").mkdir()
        
        # Create a mock console
        self.console = Mock(spec=Console)
        self.view = RepoView(console=self.console)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_init_with_console(self):
        """Test initialization with a console instance."""
        console = Mock(spec=Console)
        view = RepoView(console=console)
        self.assertEqual(view.console, console)
    
    def test_init_without_console(self):
        """Test initialization without a console instance."""
        view = RepoView()
        self.assertIsInstance(view.console, Console)
    
    def test_symbols_configuration(self):
        """Test that symbols are properly configured."""
        expected_symbols = [
            'folder', 'dir_sep', 'root', 'added', 'modified', 'deleted',
            'renamed', 'copied', 'unmerged', 'untracked', 'ignored',
            'stash', 'clean', 'branch', 'success',
            'warning', 'error', 'ahead', 'behind'
        ]
        
        for symbol_name in expected_symbols:
            self.assertIn(symbol_name, self.view.symbols)
            self.assertIsInstance(self.view.symbols[symbol_name], str)
    
    def test_display_summary_clean_repo(self):
        """Test displaying summary for a clean repository."""
        summary = {
            'repo_status': {
                'branch': 'main',
                'is_clean': True,
                'last_commit_sha': 'abc123',
                'last_commit_message': 'Initial commit',
                'ahead_count': 0,
                'behind_count': 0,
                'upstream_branch': 'origin/main'
            },
            'file_status': {
                'staged': [],
                'modified': [],
                'untracked': [],
                'deleted': [],
                'renamed': [],
                'unmerged': []
            },
            'file_counts': {
                'staged': 0,
                'modified': 0,
                'untracked': 0,
                'deleted': 0,
                'renamed': 0,
                'unmerged': 0
            }
        }
        
        self.view.display_summary("test-repo", summary)
        
        # Verify console.print was called for header and clean message
        self.assertGreaterEqual(self.console.print.call_count, 2)
    
    def test_display_summary_dirty_repo(self):
        """Test displaying summary for a dirty repository."""
        summary = {
            'repo_status': {
                'branch': 'main',
                'is_clean': False,
                'last_commit_sha': 'abc123',
                'last_commit_message': 'Initial commit',
                'ahead_count': 1,
                'behind_count': 0,
                'upstream_branch': 'origin/main'
            },
            'file_status': {
                'staged': [{'path': 'src/main.py', 'status': 'modified'}],
                'modified': [{'path': 'README.md', 'status': 'modified'}],
                'untracked': [{'path': 'new_file.txt', 'status': 'untracked'}],
                'deleted': [],
                'renamed': [],
                'unmerged': []
            },
            'file_counts': {
                'staged': 1,
                'modified': 1,
                'untracked': 1,
                'deleted': 0,
                'renamed': 0,
                'unmerged': 0
            }
        }
        
        self.view.display_summary("test-repo", summary)
        
        # Verify console.print was called multiple times
        self.assertGreaterEqual(self.console.print.call_count, 3)
    
    def test_display_status_table(self):
        """Test displaying status table."""
        statuses = {
            'repo1': {
                'status': 'clean',
                'branch': 'main',
                'ahead': 0,
                'behind': 0,
                'path': '/path/to/repo1'
            },
            'repo2': {
                'status': 'dirty',
                'branch': 'feature',
                'ahead': 2,
                'behind': 1,
                'path': '/path/to/repo2'
            }
        }
        
        self.view.display_status_table(statuses)
        
        # Verify console.print was called
        self.console.print.assert_called_once()
    
    def test_display_json(self):
        """Test displaying JSON data."""
        data = {'key': 'value', 'number': 42}
        
        self.view.display_json(data, pretty=True)
        
        # Verify console.print was called
        self.console.print.assert_called_once()
    
    def test_display_repo_status_with_error(self):
        """Test displaying repository status with error."""
        repo_status = {'error': 'Failed to get current branch'}
        
        self.view.display_repo_status(repo_status)
        
        # Verify console.print was called for error message
        self.console.print.assert_called_once()
    
    def test_display_repo_status_clean(self):
        """Test displaying clean repository status."""
        repo_status = {
            'branch': 'main',
            'is_clean': True,
            'last_commit_sha': 'abc123',
            'last_commit_message': 'Initial commit',
            'ahead_count': 0,
            'behind_count': 0,
            'upstream_branch': 'origin/main'
        }
        
        self.view.display_repo_status(repo_status)
        
        # Verify console.print was called multiple times
        self.assertGreaterEqual(self.console.print.call_count, 3)
    
    def test_group_files_by_directory(self):
        """Test grouping files by directory."""
        file_status = {
            'staged': [
                {'path': 'src/main.py', 'status': 'modified'},
                {'path': 'src/utils/helper.py', 'status': 'added'}
            ],
            'modified': [
                {'path': 'README.md', 'status': 'modified'}
            ],
            'untracked': [
                {'path': 'docs/new_file.txt', 'status': 'untracked'}
            ],
            'deleted': [],
            'renamed': [],
            'unmerged': []
        }
        
        result = self.view._group_files_by_directory(file_status)
        
        # Debug output
        print(f"Result: {result}")
        print(f"src files: {result.get('src', [])}")
        print(f"root files: {result.get('', [])}")
        print(f"docs files: {result.get('docs', [])}")
        
        # Verify directories are created
        self.assertIn('src', result)
        self.assertIn('src/utils', result)
        self.assertIn('', result)  # Root directory for README.md
        self.assertIn('docs', result)
        
        # Verify files are grouped correctly
        self.assertEqual(len(result['src']), 1)
        self.assertEqual(len(result['src/utils']), 1)
        self.assertEqual(len(result['']), 1)
        self.assertEqual(len(result['docs']), 1)
    
    def test_get_status_color(self):
        """Test getting status colors."""
        self.assertEqual(self.view._get_status_color('clean'), 'green')
        self.assertEqual(self.view._get_status_color('dirty'), 'red')
        self.assertEqual(self.view._get_status_color('missing'), 'red')
        self.assertEqual(self.view._get_status_color('not_git'), 'yellow')
        self.assertEqual(self.view._get_status_color('error'), 'red')
        self.assertEqual(self.view._get_status_color('unknown'), 'white')


if __name__ == "__main__":
    unittest.main() 