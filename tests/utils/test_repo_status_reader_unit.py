#!/usr/bin/env python3
"""Unit tests for RepoStatusReader."""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from src.utils.repo_status_reader import RepoStatusReader
from git import Repo


class TestRepoStatusReaderIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "repo"
        self.repo_path.mkdir()
        self.repo = Repo.init(self.repo_path)
        # Create a file and commit
        file_path = self.repo_path / "file.txt"
        file_path.write_text("hello")
        # Use relative path for GitPython compatibility
        rel_file_path = file_path.relative_to(self.repo_path)
        self.repo.index.add([str(rel_file_path)])
        self.repo.index.commit("initial commit")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_get_summary_json_clean(self):
        reader = RepoStatusReader(self.repo_path)
        summary = reader.get_summary_json()
        self.assertEqual(summary["branch"], self.repo.active_branch.name)
        self.assertTrue(summary["clean"])
        self.assertEqual(summary["ahead"], 0)
        self.assertEqual(summary["behind"], 0)
        self.assertIn("last_commit", summary)
        self.assertIn("changes", summary)
        self.assertEqual(summary["changes"]["staged"], [])
        self.assertEqual(summary["changes"]["unstaged"], [])
        self.assertEqual(summary["changes"]["untracked"], [])

    def test_get_summary_json_with_untracked(self):
        # Add an untracked file
        (self.repo_path / "untracked.txt").write_text("untracked")
        reader = RepoStatusReader(self.repo_path)
        summary = reader.get_summary_json()
        self.assertIn("untracked.txt", summary["changes"]["untracked"])
        self.assertFalse(summary["clean"])


if __name__ == "__main__":
    unittest.main() 