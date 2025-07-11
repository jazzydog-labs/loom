"""Git operations for loom repository management."""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class GitManager:
    """Manages git operations for repositories."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    def is_git_repo(self, path: Path) -> bool:
        """Check if a directory is a git repository."""
        return (path / ".git").exists()
    
    def clone_repo(self, url: str, path: Path, branch: str = "main") -> bool:
        """Clone a repository to the specified path."""
        try:
            # Create parent directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Clone the repository
            cmd = [
                "git", "clone", 
                "--branch", branch,
                "--depth", "1",
                url, str(path)
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully cloned {url} to {path}")
                return True
            else:
                logger.error(f"Failed to clone {url}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout cloning {url}")
            return False
        except Exception as e:
            logger.error(f"Error cloning {url}: {e}")
            return False
    
    def pull_repo(self, path: Path) -> Tuple[bool, bool, int]:
        """Pull latest changes for a repository.
        
        Returns:
            Tuple of (success, had_changes, commits_pulled) where:
            - success: True if git pull succeeded
            - had_changes: True if changes were actually pulled from upstream
            - commits_pulled: Number of commits pulled from upstream
        """
        try:
            # Get current HEAD before pulling to count commits pulled
            pre_pull_head = None
            try:
                head_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                if head_result.returncode == 0:
                    pre_pull_head = head_result.stdout.strip()
            except Exception:
                pass  # If we can't get HEAD, we'll just not count commits
            
            cmd = ["git", "pull"]
            result = subprocess.run(
                cmd, 
                cwd=path,
                capture_output=True, 
                text=True, 
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                # Check if changes were actually pulled
                output = result.stdout.strip()
                had_changes = not ("Already up to date" in output or "Already up-to-date" in output)
                
                commits_pulled = 0
                if had_changes and pre_pull_head:
                    # Count commits between the old HEAD and new HEAD
                    try:
                        count_result = subprocess.run(
                            ["git", "rev-list", "--count", f"{pre_pull_head}..HEAD"],
                            cwd=path,
                            capture_output=True,
                            text=True,
                            timeout=self.timeout
                        )
                        if count_result.returncode == 0:
                            commits_pulled = int(count_result.stdout.strip())
                    except Exception:
                        pass  # If we can't count, we'll just show that changes were pulled
                
                logger.info(f"Successfully pulled {path}")
                return True, had_changes, commits_pulled
            else:
                logger.error(f"Failed to pull {path}: {result.stderr}")
                return False, False, 0
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout pulling {path}")
            return False, False, 0
        except Exception as e:
            logger.error(f"Error pulling {path}: {e}")
            return False, False, 0
    
    def push_repo(self, path: Path) -> Tuple[bool, bool]:
        """Push local commits to upstream.
        
        Returns:
            Tuple of (success, had_changes) where:
            - success: True if git push succeeded
            - had_changes: True if commits were actually pushed to upstream
        """
        try:
            cmd = ["git", "push"]
            result = subprocess.run(
                cmd, 
                cwd=path,
                capture_output=True, 
                text=True, 
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                # Check if commits were actually pushed
                output = result.stdout.strip() + result.stderr.strip()
                had_changes = not ("Everything up-to-date" in output)
                
                logger.info(f"Successfully pushed {path}")
                return True, had_changes
            else:
                logger.error(f"Failed to push {path}: {result.stderr}")
                return False, False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout pushing {path}")
            return False, False
        except Exception as e:
            logger.error(f"Error pushing {path}: {e}")
            return False, False
    
    def get_repo_status(self, path: Path) -> Dict[str, str]:
        """Get the status of a git repository."""
        status = {
            "path": str(path),
            "exists": path.exists(),
            "is_git": False,
            "branch": None,
            "status": "unknown",
            "ahead": "0",
            "behind": "0",
            "modified": False,
            "untracked": False
        }
        
        if not path.exists():
            status["status"] = "missing"
            return status
        
        if not self.is_git_repo(path):
            status["status"] = "not_git"
            return status
        
        status["is_git"] = True
        
        try:
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            if result.returncode == 0:
                status["branch"] = result.stdout.strip()
            
            # Get status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
                status["modified"] = any(line.startswith('M') for line in lines)
                status["untracked"] = any(line.startswith('??') for line in lines)
                
                if not lines:
                    status["status"] = "clean"
                elif status["modified"] or status["untracked"]:
                    status["status"] = "dirty"
                else:
                    status["status"] = "clean"
            
            # Get ahead/behind info
            result = subprocess.run(
                ["git", "rev-list", "--count", "--left-right", "@{u}...HEAD"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split('\t')
                if len(parts) == 2:
                    status["behind"] = parts[0]
                    status["ahead"] = parts[1]
            
        except Exception as e:
            logger.error(f"Error getting status for {path}: {e}")
            status["status"] = "error"
        
        return status
    
    def execute_command(self, path: Path, command: List[str]) -> Tuple[bool, str, str]:
        """Execute a command in a repository directory."""
        try:
            result = subprocess.run(
                command,
                cwd=path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            return (
                result.returncode == 0,
                result.stdout,
                result.stderr
            )
            
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e) 