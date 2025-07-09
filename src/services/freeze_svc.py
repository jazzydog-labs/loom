import json
import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from git import Repo, InvalidGitRepositoryError
from ..domain.freeze_snapshot import FreezeSnapshot
from ..domain.repo import Repo as DomainRepo


class FreezeSvc:
    """Service orchestrating freeze creation and checkout."""

    def __init__(self, snapshots_dir: Optional[Path] = None):
        """Initialize the FreezeSvc with optional snapshots directory."""
        self.snapshots_dir = snapshots_dir or Path.home() / ".loom" / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def create_freeze(self, repos: List[DomainRepo], tag: str) -> FreezeSnapshot:
        """Create a freeze snapshot of the current state of repositories.
        
        Args:
            repos: List of repository objects to snapshot
            tag: Tag name for the freeze snapshot
            
        Returns:
            FreezeSnapshot object representing the created snapshot
            
        Raises:
            ValueError: If tag already exists
            InvalidGitRepositoryError: If a repo path is not a valid git repository
        """
        snapshot_id = f"{tag}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        snapshot_path = self.snapshots_dir / f"{snapshot_id}.json"
        
        if snapshot_path.exists():
            raise ValueError(f"Freeze snapshot with tag '{tag}' already exists")
        
        repo_commits = {}
        repo_details = {}
        
        for repo in repos:
            try:
                git_repo = Repo(repo.path)
                
                # Get current commit SHA
                current_commit = git_repo.head.commit.hexsha
                repo_commits[repo.name] = current_commit
                
                # Capture additional details for restoration
                current_branch = git_repo.active_branch.name if git_repo.active_branch else "detached"
                is_dirty = git_repo.is_dirty()
                untracked_files = git_repo.untracked_files
                
                repo_details[repo.name] = {
                    "path": str(repo.path),
                    "branch": current_branch,
                    "commit": current_commit,
                    "is_dirty": is_dirty,
                    "untracked_files": list(untracked_files),
                    "created_at": datetime.datetime.now().isoformat()
                }
                
            except InvalidGitRepositoryError:
                raise InvalidGitRepositoryError(f"'{repo.path}' is not a valid git repository")
        
        # Create FreezeSnapshot using the domain model
        snapshot = FreezeSnapshot(repos=repo_commits)
        
        # Save snapshot metadata to disk for restoration
        snapshot_data = {
            "id": snapshot_id,
            "tag": tag,
            "bom_hash": snapshot.bom_hash,
            "created_at": datetime.datetime.now().isoformat(),
            "repositories": repo_details
        }
        
        with open(snapshot_path, 'w') as f:
            json.dump(snapshot_data, f, indent=2)
        
        return snapshot

    def checkout(self, freeze_id: str, repos: List[DomainRepo]) -> Dict[str, Any]:
        """Restore repositories to a freeze snapshot state.
        
        Args:
            freeze_id: ID of the freeze snapshot to restore
            repos: List of repository objects to restore
            
        Returns:
            Dictionary with restoration results
            
        Raises:
            FileNotFoundError: If freeze snapshot doesn't exist
            InvalidGitRepositoryError: If a repo path is not a valid git repository
        """
        snapshot_path = self.snapshots_dir / f"{freeze_id}.json"
        
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Freeze snapshot '{freeze_id}' not found")
        
        # Load snapshot data
        with open(snapshot_path, 'r') as f:
            snapshot_data = json.load(f)
        
        # Create lookup for snapshot repository states
        snapshot_repos = snapshot_data["repositories"]
        
        results = {
            "restored": [],
            "skipped": [],
            "errors": []
        }
        
        for repo in repos:
            if repo.name not in snapshot_repos:
                results["skipped"].append(f"{repo.name}: not in freeze snapshot")
                continue
                
            try:
                git_repo = Repo(repo.path)
                snapshot_state = snapshot_repos[repo.name]
                target_commit = snapshot_state["commit"]
                
                # Stash current changes if dirty
                if git_repo.is_dirty() or git_repo.untracked_files:
                    stash_msg = f"loom-freeze-backup-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    git_repo.git.stash("push", "-u", "-m", stash_msg)
                
                # Reset to specific commit
                git_repo.head.reset(target_commit, index=True, working_tree=True)
                
                results["restored"].append(f"{repo.name}: restored to {target_commit[:8]}")
                
            except Exception as e:
                results["errors"].append(f"{repo.name}: {str(e)}")
        
        return results

    def list_freezes(self) -> List[Dict[str, Any]]:
        """List all available freeze snapshots.
        
        Returns:
            List of freeze snapshot metadata
        """
        freezes = []
        
        for snapshot_file in self.snapshots_dir.glob("*.json"):
            try:
                with open(snapshot_file, 'r') as f:
                    snapshot_data = json.load(f)
                
                freeze_info = {
                    "id": snapshot_data["id"],
                    "tag": snapshot_data["tag"],
                    "bom_hash": snapshot_data["bom_hash"],
                    "created_at": snapshot_data["created_at"],
                    "repo_count": len(snapshot_data["repositories"])
                }
                freezes.append(freeze_info)
                
            except (json.JSONDecodeError, KeyError):
                # Skip invalid snapshot files
                continue
        
        return sorted(freezes, key=lambda x: x["created_at"], reverse=True)

    def delete_freeze(self, freeze_id: str) -> bool:
        """Delete a freeze snapshot.
        
        Args:
            freeze_id: ID of the freeze snapshot to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        snapshot_path = self.snapshots_dir / f"{freeze_id}.json"
        
        if snapshot_path.exists():
            snapshot_path.unlink()
            return True
        
        return False
