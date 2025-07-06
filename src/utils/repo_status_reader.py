"""Repository status reader for Git repositories.

This module provides read-only status information for Git repositories
with JSON-serializable output suitable for CQRS queries.
"""

from git import Repo, exc
import pathlib
import json

class RepoStatusReader:
    def __init__(self, root):
        self.repo = Repo(pathlib.Path(root).expanduser().resolve())

    def get_summary_json(self):
        head = self.repo.head.commit
        try:
            ahead = len(list(self.repo.iter_commits(f'@{{u}}..', quiet=True)))
            behind = len(list(self.repo.iter_commits(f'..@{{u}}', quiet=True)))
        except (exc.GitCommandError, ValueError):
            ahead = 0
            behind = 0
        return {
            "branch": self.repo.active_branch.name,
            "clean": not self.repo.is_dirty(untracked_files=True),
            "ahead": ahead,
            "behind": behind,
            "last_commit": {"sha": head.hexsha, "message": head.message.strip()},
            "changes": {
                "staged":   [i.a_path for i in self.repo.index.diff("HEAD")],
                "unstaged": [i.a_path for i in self.repo.index.diff(None)],
                "untracked": self.repo.untracked_files,
            },
        }


# Example usage and tests
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python repo_status_reader.py <repo_path>")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    
    try:
        reader = RepoStatusReader(repo_path)
        
        print("=== Summary ===")
        summary = reader.get_summary_json()
        print(json.dumps(summary, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1) 