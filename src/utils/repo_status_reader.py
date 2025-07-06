"""Repository status reader for Git repositories.

This module provides read-only status information for Git repositories
with JSON-serializable output suitable for CQRS queries.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class FileStatus:
    """Represents the status of a single file."""
    path: str
    status: str  # 'staged', 'modified', 'untracked', 'deleted', 'renamed', 'unmerged'
    original_path: Optional[str] = None  # For renamed files


@dataclass
class RepoStatus:
    """Represents the overall status of a repository."""
    branch: str
    is_clean: bool
    last_commit_sha: str
    last_commit_message: str
    ahead_count: int
    behind_count: int
    upstream_branch: Optional[str] = None


class RepoStatusReader:
    """Read-only status information for a local Git repository."""
    
    def __init__(self, repo_root: str):
        """Initialize with the repository root path.
        
        Args:
            repo_root: Path to the Git repository root directory
        """
        self.repo_root = Path(repo_root).resolve()
        self._validate_repo()
    
    def _validate_repo(self) -> None:
        """Validate that the repository exists and is a Git repository."""
        if not self.repo_root.exists():
            raise ValueError(f"Repository path does not exist: {self.repo_root}")
        
        if not (self.repo_root / ".git").exists():
            raise ValueError(f"Not a Git repository: {self.repo_root}")
    
    def _execute_git_command(self, args: List[str]) -> tuple[bool, str, str]:
        """Execute a Git command and return (success, stdout, stderr)."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
    
    def file_status(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get staged, modified, and untracked files with their paths.
        
        Returns:
            Dictionary with keys 'staged', 'modified', 'untracked', 'deleted', 
            'renamed', 'unmerged', each containing a list of file status dictionaries.
        """
        success, stdout, stderr = self._execute_git_command([
            "status", "--porcelain", "--ignored=matching"
        ])
        
        # Initialize result structure
        result = {
            "staged": [],
            "modified": [],
            "untracked": [],
            "deleted": [],
            "renamed": [],
            "unmerged": []
        }
        
        if not success:
            logger.error(f"Failed to get git status: {stderr}")
            return result
        
        for line in stdout.strip().split('\n'):
            if not line.strip():
                continue
            
            # Parse porcelain format: XY PATH
            # X = status of index, Y = status of working tree
            status_code = line[:2]
            path_part = line[3:]
            
            # Handle renamed files (format: XY ORIGINAL_PATH -> NEW_PATH)
            if " -> " in path_part:
                original_path, new_path = path_part.split(" -> ", 1)
                file_status = {
                    "path": new_path,
                    "status": "renamed",
                    "original_path": original_path
                }
                result["renamed"].append(file_status)
                continue
            
            # Parse status codes
            index_status = status_code[0]
            working_status = status_code[1]
            
            if index_status == 'M' or working_status == 'M':
                # Modified files
                if index_status == 'M':
                    result["staged"].append({"path": path_part, "status": "modified"})
                if working_status == 'M' and index_status != 'M':
                    result["modified"].append({"path": path_part, "status": "modified"})
            
            elif index_status == 'A':
                # Added files
                result["staged"].append({"path": path_part, "status": "added"})
            
            elif index_status == 'D' or working_status == 'D':
                # Deleted files
                if index_status == 'D':
                    result["staged"].append({"path": path_part, "status": "deleted"})
                if working_status == 'D' and index_status != 'D':
                    result["deleted"].append({"path": path_part, "status": "deleted"})
            
            elif working_status == '?':
                # Untracked files
                result["untracked"].append({"path": path_part, "status": "untracked"})
            
            elif index_status == 'U' or working_status == 'U':
                # Unmerged files
                result["unmerged"].append({"path": path_part, "status": "unmerged"})
        
        return result
    
    def repo_status(self) -> Dict[str, Any]:
        """Get current branch, clean/dirty flag, last commit info, and ahead/behind counts.
        
        Returns:
            Dictionary with repository status information.
        """
        # Get current branch
        success, stdout, stderr = self._execute_git_command(["branch", "--show-current"])
        if not success:
            logger.error(f"Failed to get current branch: {stderr}")
            return {"error": "Failed to get current branch"}
        
        branch = stdout.strip()
        
        # Get last commit info
        success, stdout, stderr = self._execute_git_command([
            "log", "-1", "--format=%H%n%s"
        ])
        if not success:
            logger.error(f"Failed to get last commit: {stderr}")
            return {"error": "Failed to get last commit"}
        
        lines = stdout.strip().split('\n')
        if len(lines) >= 2:
            last_commit_sha = lines[0]
            last_commit_message = lines[1]
        else:
            last_commit_sha = ""
            last_commit_message = ""
        
        # Check if working directory is clean
        success, stdout, stderr = self._execute_git_command(["status", "--porcelain"])
        is_clean = success and not stdout.strip()
        
        # Get ahead/behind counts
        ahead_count = 0
        behind_count = 0
        upstream_branch = None
        
        success, stdout, stderr = self._execute_git_command([
            "rev-list", "--count", "--left-right", "@{u}...HEAD"
        ])
        
        if success and stdout.strip():
            parts = stdout.strip().split('\t')
            if len(parts) == 2:
                behind_count = int(parts[0])
                ahead_count = int(parts[1])
        
        # Get upstream branch name
        success, stdout, stderr = self._execute_git_command([
            "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"
        ])
        if success and stdout.strip():
            upstream_branch = stdout.strip()
        
        return {
            "branch": branch,
            "is_clean": is_clean,
            "last_commit_sha": last_commit_sha,
            "last_commit_message": last_commit_message,
            "ahead_count": ahead_count,
            "behind_count": behind_count,
            "upstream_branch": upstream_branch
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get consolidated snapshot combining file and repository status.
        
        Returns:
            Dictionary with complete repository status information.
        """
        file_status = self.file_status()
        repo_status = self.repo_status()

        file_counts = {
            "staged": len(file_status["staged"]),
            "modified": len(file_status["modified"]),
            "untracked": len(file_status["untracked"]),
            "deleted": len(file_status["deleted"]),
            "renamed": len(file_status["renamed"]),
            "unmerged": len(file_status["unmerged"])
        }
        
        return {
            "repository_path": str(self.repo_root),
            "file_status": file_status,
            "file_counts": file_counts,
            "repo_status": repo_status,
            "timestamp": None  # Could be added if needed
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
        
        print("=== File Status ===")
        file_status = reader.file_status()
        print(json.dumps(file_status, indent=2))
        
        print("\n=== Repository Status ===")
        repo_status = reader.repo_status()
        print(json.dumps(repo_status, indent=2))
        
        print("\n=== Summary ===")
        summary = reader.summary()
        print(json.dumps(summary, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1) 