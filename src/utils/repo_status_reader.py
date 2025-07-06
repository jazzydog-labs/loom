"""Repository status reader for Git repositories.

This module provides read-only status information for Git repositories
with JSON-serializable output suitable for CQRS queries.
"""

from git import Repo, exc
import pathlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    def _transform_for_view(self, raw_data: dict) -> dict:
        """Transform the output of get_summary_json() into the structure expected by RepoView."""
        return {
            'repo_status': {
                'branch': raw_data.get('branch', 'unknown'),
                'is_clean': raw_data.get('clean', True),
                'ahead_count': raw_data.get('ahead', 0),
                'behind_count': raw_data.get('behind', 0),
                'last_commit_message': raw_data.get('last_commit', {}).get('message', 'No commits'),
                'last_commit_sha': raw_data.get('last_commit', {}).get('sha', ''),
            },
            'file_status': {
                'staged': [{'path': p} for p in raw_data.get('changes', {}).get('staged', [])],
                'modified': [{'path': p} for p in raw_data.get('changes', {}).get('unstaged', [])],
                'untracked': [{'path': p} for p in raw_data.get('changes', {}).get('untracked', [])],
                'deleted': [],
                'renamed': [],
                'unmerged': []
            },
            'file_counts': {
                'staged': len(raw_data.get('changes', {}).get('staged', [])),
                'modified': len(raw_data.get('changes', {}).get('unstaged', [])),
                'untracked': len(raw_data.get('changes', {}).get('untracked', [])),
                'deleted': 0,
                'renamed': 0,
                'unmerged': 0
            }
        }

    @classmethod
    def summaries_parallel(cls, repo_paths: dict[str, str], max_workers: int = 4) -> dict[str, dict]:
        """Fetch summaries for multiple repositories in parallel.

        Args:
            repo_paths: Mapping of repo name to filesystem path
            max_workers: Maximum number of worker threads

        Returns:
            Mapping of repo name to transformed summary dict
        """
        def worker(name_path: tuple[str, str]):
            name, path = name_path
            try:
                reader = cls(path)
                raw = reader.get_summary_json()
                transformed = reader._transform_for_view(raw)
                return name, transformed
            except Exception as exc:
                return name, {
                    'repo_status': {'error': str(exc)},
                    'file_status': {},
                    'file_counts': {}
                }

        results: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_name = {
                executor.submit(worker, item): item[0]
                for item in repo_paths.items()
            }
            for future in as_completed(future_to_name):
                name, summary = future.result()
                results[name] = summary

        # Return results sorted by repo name
        return dict(sorted(results.items(), key=lambda x: x[0]))


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