"""Repository status service for Git repositories.

This service provides read-only status information for Git repositories
with JSON-serializable output suitable for CQRS queries.
"""

from git import Repo, exc
import pathlib
from concurrent.futures import ThreadPoolExecutor, as_completed


class RepoStatusService:
    """Read-only repo status queries."""

    def __init__(self):
        pass

    def status(self, repo_path: str) -> dict:
        """Get status for a single repository.
        
        Args:
            repo_path: Path to the repository
            
        Returns:
            Dictionary with repository status information
        """
        try:
            repo = Repo(pathlib.Path(repo_path).expanduser().resolve())
            return self._get_repo_summary(repo)
        except Exception as exc:
            return {
                'repo_status': {'error': str(exc)},
                'file_status': {},
                'file_counts': {}
            }
    
    def _get_repo_summary(self, repo: Repo) -> dict:
        """Get summary for a repository instance."""
        raw_data = self._get_summary_json(repo)
        return self._transform_for_view(raw_data)
    
    def _get_summary_json(self, repo: Repo) -> dict:
        """Get raw summary data for a repository."""
        head = repo.head.commit
        
        # Get upstream branch information and ahead/behind counts
        upstream_branch = None
        remote_name = None
        ahead = 0
        behind = 0
        
        try:
            # Get the tracking branch
            tracking_branch = repo.active_branch.tracking_branch()
            if tracking_branch:
                # In some unit-test scenarios *tracking_branch.name* may be a mock rather
                # than a real string which breaks substring checks. Coerce to *str*
                # defensively so downstream logic remains robust.
                upstream_branch = str(getattr(tracking_branch, "name", tracking_branch))

                # Extract remote name (e.g., "origin/main" -> "origin")
                if "/" in upstream_branch:
                    remote_name = upstream_branch.split("/", 1)[0]

                # Count commits ahead (local commits not in upstream)
                ahead = len(list(repo.iter_commits(f"{upstream_branch}..HEAD")))
                # Count commits behind (upstream commits not in local)
                behind = len(list(repo.iter_commits(f"HEAD..{upstream_branch}")))
        except (AttributeError, exc.GitCommandError, ValueError):
            pass
            
        result = {
            "branch": repo.active_branch.name,
            "clean": not repo.is_dirty(untracked_files=True),
            "ahead": ahead,
            "behind": behind,
            "last_commit": {"sha": head.hexsha, "message": head.message.strip()},
            "changes": {
                "staged":   [i.a_path for i in repo.index.diff("HEAD")],
                "unstaged": [i.a_path for i in repo.index.diff(None)],
                "untracked": repo.untracked_files,
            },
        }

        if remote_name is not None:
            result["remote_name"] = remote_name
            # Only surface *upstream_branch* when we also discovered the remote.
            result["upstream_branch"] = upstream_branch

        return result

    def _transform_for_view(self, raw_data: dict) -> dict:
        """Transform the output of get_summary_json() into the structure expected by RepoView."""
        return {
            'repo_status': {
                'branch': raw_data.get('branch', 'unknown'),
                'upstream_branch': raw_data.get('upstream_branch'),
                'remote_name': raw_data.get('remote_name'),
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

    def summaries_parallel(self, repo_paths: dict[str, str], max_workers: int = 4) -> dict[str, dict]:
        """Fetch summaries for multiple repositories in parallel.

        Args:
            repo_paths: Mapping of repo name to filesystem path
            max_workers: Maximum number of worker threads

        Returns:
            Mapping of repo name to transformed summary dict
        """
        def worker(name_path: tuple[str, str]):
            name, path = name_path
            return name, self.status(path)

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