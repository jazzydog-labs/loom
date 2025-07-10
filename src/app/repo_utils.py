"""Utility functions for repository management."""
from typing import List, Optional
from pathlib import Path
import os

from src.domain.repo import Repo


def resolve_repos(patterns: Optional[List[str]] = None, root_dir: Optional[str] = None) -> List[Repo]:
    """Resolve repository patterns to Repo instances.
    
    Args:
        patterns: List of repo patterns. If None or contains "*", returns all repos.
        root_dir: Root directory to search for repos. If None, uses current directory.
    
    Returns:
        List of Repo instances
    """
    if root_dir is None:
        root_dir = os.getcwd()
    
    root_path = Path(root_dir).expanduser().resolve()
    
    # For now, simple implementation - just check if current dir is a repo
    # In a full implementation, this would scan for all repos under root_dir
    repos = []
    
    # Check if root_path itself is a git repo
    git_dir = root_path / ".git"
    if git_dir.exists() and git_dir.is_dir():
        repo_name = root_path.name
        repos.append(Repo(name=repo_name, path=str(root_path)))
    
    # If patterns specified and not wildcard, filter
    if patterns and "*" not in patterns:
        filtered_repos = []
        for repo in repos:
            if repo.name in patterns:
                filtered_repos.append(repo)
        return filtered_repos
    
    return repos


def get_repo_by_name(name: str, root_dir: Optional[str] = None) -> Optional[Repo]:
    """Get a specific repository by name.
    
    Args:
        name: Repository name
        root_dir: Root directory to search
        
    Returns:
        Repo instance or None if not found
    """
    repos = resolve_repos([name], root_dir)
    return repos[0] if repos else None