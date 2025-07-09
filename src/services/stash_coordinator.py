import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from git import Repo, InvalidGitRepositoryError, GitCommandError
from ..domain.repo import Repo as DomainRepo


class StashCoordinator:
    """Stash/unstash across all repositories."""

    def __init__(self):
        """Initialize the StashCoordinator."""
        self.stash_prefix = "loom-stash"
    
    def stash_all(self, repos: List[DomainRepo], message: Optional[str] = None) -> Dict[str, Any]:
        """Stash changes across all repositories.
        
        Args:
            repos: List of repository objects to stash
            message: Optional message for the stash
            
        Returns:
            Dictionary with stash results per repository
        """
        if message is None:
            message = f"{self.stash_prefix}-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            message = f"{self.stash_prefix}-{message}"
        
        results = {
            "stashed": [],
            "clean": [],
            "errors": []
        }
        
        for repo in repos:
            try:
                git_repo = Repo(repo.path)
                
                # Check if repo has changes to stash
                if git_repo.is_dirty() or git_repo.untracked_files:
                    # Stash including untracked files
                    git_repo.git.stash("push", "-u", "-m", message)
                    results["stashed"].append({
                        "repo": repo.name,
                        "message": message,
                        "has_changes": True
                    })
                else:
                    results["clean"].append({
                        "repo": repo.name,
                        "message": "No changes to stash"
                    })
                    
            except InvalidGitRepositoryError:
                results["errors"].append({
                    "repo": repo.name,
                    "error": f"Not a valid git repository: {repo.path}"
                })
            except Exception as e:
                results["errors"].append({
                    "repo": repo.name,
                    "error": str(e)
                })
        
        return results
    
    def unstash_all(self, repos: List[DomainRepo], stash_ref: Optional[str] = None) -> Dict[str, Any]:
        """Unstash changes across all repositories.
        
        Args:
            repos: List of repository objects to unstash
            stash_ref: Optional stash reference (default: latest stash)
            
        Returns:
            Dictionary with unstash results per repository
        """
        results = {
            "unstashed": [],
            "no_stash": [],
            "conflicts": [],
            "errors": []
        }
        
        for repo in repos:
            try:
                git_repo = Repo(repo.path)
                
                # Check if there are any stashes
                stash_list = git_repo.git.stash("list").strip()
                if not stash_list:
                    results["no_stash"].append({
                        "repo": repo.name,
                        "message": "No stashes found"
                    })
                    continue
                
                # Find the appropriate stash
                if stash_ref:
                    # Use specific stash reference
                    target_stash = stash_ref
                else:
                    # Find latest loom stash
                    stashes = stash_list.split('\n')
                    loom_stashes = [s for s in stashes if self.stash_prefix in s]
                    
                    if not loom_stashes:
                        results["no_stash"].append({
                            "repo": repo.name,
                            "message": "No loom stashes found"
                        })
                        continue
                    
                    # Extract stash reference (e.g., "stash@{0}")
                    target_stash = loom_stashes[0].split(':')[0]
                
                # Try to apply the stash
                try:
                    git_repo.git.stash("apply", target_stash)
                    # If successful, drop the stash
                    git_repo.git.stash("drop", target_stash)
                    results["unstashed"].append({
                        "repo": repo.name,
                        "stash": target_stash,
                        "status": "Applied and dropped"
                    })
                except GitCommandError as e:
                    if "conflict" in str(e).lower():
                        results["conflicts"].append({
                            "repo": repo.name,
                            "stash": target_stash,
                            "error": "Merge conflicts detected",
                            "resolution": "Manual intervention required"
                        })
                    else:
                        raise
                        
            except InvalidGitRepositoryError:
                results["errors"].append({
                    "repo": repo.name,
                    "error": f"Not a valid git repository: {repo.path}"
                })
            except Exception as e:
                results["errors"].append({
                    "repo": repo.name,
                    "error": str(e)
                })
        
        return results
    
    def list_stashes(self, repos: List[DomainRepo]) -> Dict[str, List[Dict[str, str]]]:
        """List all stashes across repositories.
        
        Args:
            repos: List of repository objects to check
            
        Returns:
            Dictionary mapping repo names to their stashes
        """
        stashes = {}
        
        for repo in repos:
            try:
                git_repo = Repo(repo.path)
                stash_list = git_repo.git.stash("list").strip()
                
                if stash_list:
                    repo_stashes = []
                    for stash_line in stash_list.split('\n'):
                        parts = stash_line.split(': ', 2)
                        if len(parts) >= 3:
                            stash_info = {
                                "ref": parts[0],
                                "branch": parts[1],
                                "message": parts[2],
                                "is_loom": self.stash_prefix in parts[2]
                            }
                            repo_stashes.append(stash_info)
                    
                    if repo_stashes:
                        stashes[repo.name] = repo_stashes
                        
            except Exception:
                # Skip repos with errors
                pass
        
        return stashes
    
    def clear_loom_stashes(self, repos: List[DomainRepo]) -> Dict[str, Any]:
        """Clear all loom-created stashes across repositories.
        
        Args:
            repos: List of repository objects to clear stashes from
            
        Returns:
            Dictionary with clear results per repository
        """
        results = {
            "cleared": [],
            "no_stashes": [],
            "errors": []
        }
        
        for repo in repos:
            try:
                git_repo = Repo(repo.path)
                stash_list = git_repo.git.stash("list").strip()
                
                if not stash_list:
                    results["no_stashes"].append(repo.name)
                    continue
                
                # Find and drop all loom stashes
                stashes = stash_list.split('\n')
                loom_stashes = [(s.split(':')[0], s) for s in stashes if self.stash_prefix in s]
                
                if not loom_stashes:
                    results["no_stashes"].append(repo.name)
                    continue
                
                dropped_count = 0
                for stash_ref, stash_line in reversed(loom_stashes):  # Drop in reverse order
                    try:
                        git_repo.git.stash("drop", stash_ref)
                        dropped_count += 1
                    except Exception:
                        pass  # Continue dropping others
                
                if dropped_count > 0:
                    results["cleared"].append({
                        "repo": repo.name,
                        "count": dropped_count
                    })
                    
            except Exception as e:
                results["errors"].append({
                    "repo": repo.name,
                    "error": str(e)
                })
        
        return results
    
    def stash_status(self, repos: List[DomainRepo]) -> Dict[str, Any]:
        """Get stash status across all repositories.
        
        Args:
            repos: List of repository objects to check
            
        Returns:
            Dictionary with stash status information
        """
        total_stashes = 0
        loom_stashes = 0
        repos_with_stashes = 0
        repos_with_loom_stashes = 0
        
        stash_details = self.list_stashes(repos)
        
        for repo_name, repo_stashes in stash_details.items():
            if repo_stashes:
                repos_with_stashes += 1
                total_stashes += len(repo_stashes)
                
                loom_count = sum(1 for s in repo_stashes if s["is_loom"])
                if loom_count > 0:
                    repos_with_loom_stashes += 1
                    loom_stashes += loom_count
        
        return {
            "summary": {
                "total_repos": len(repos),
                "repos_with_stashes": repos_with_stashes,
                "repos_with_loom_stashes": repos_with_loom_stashes,
                "total_stashes": total_stashes,
                "loom_stashes": loom_stashes
            },
            "details": stash_details
        }
