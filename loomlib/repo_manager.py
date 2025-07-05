"""Repository management and orchestration for loom."""

import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

from .config import ConfigManager
from .git import GitManager

logger = logging.getLogger(__name__)


class RepoManager:
    """Manages the orchestration of all repositories in the foundry ecosystem."""
    
    def __init__(self, config_manager: ConfigManager, git_manager: GitManager):
        self.config = config_manager
        self.git = git_manager
    
    def get_dev_root(self) -> Optional[str]:
        """Get the development root directory."""
        return self.config.get_dev_root()
    
    def set_dev_root(self, dev_root: str) -> None:
        """Set the development root directory."""
        foundry_dir = self.config.get_foundry_dir() or "foundry"
        self.config.set_user_config(dev_root, foundry_dir)
    
    def get_repo_paths(self) -> Dict[str, str]:
        """Get all repository paths."""
        dev_root = self.get_dev_root()
        if not dev_root:
            return {}
        foundry_dir = self.config.get_foundry_dir() or "foundry"
        return self.config.get_repo_paths(dev_root, foundry_dir)
    
    def create_directory_structure(self, dev_root: str) -> bool:
        """Create the foundry directory structure."""
        try:
            foundry_dir = self.config.get_foundry_dir() or "foundry"
            foundry_path = Path(dev_root) / foundry_dir
            foundry_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created foundry directory structure at {foundry_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create directory structure: {e}")
            return False
    
    def clone_missing_repos(self, dev_root: str) -> Dict[str, bool]:
        """Clone repositories that don't exist."""
        foundry_dir = self.config.get_foundry_dir() or "foundry"
        repo_paths = self.config.get_repo_paths(dev_root, foundry_dir)
        repos_config = self.config.load_repos()
        results = {}
        
        for repo in repos_config.get('repos', []):
            name = repo['name']
            url = repo['url']
            path = Path(repo_paths[name])
            
            if path.exists() and self.git.is_git_repo(path):
                logger.info(f"Repository {name} already exists at {path}")
                results[name] = True
                continue
            
            logger.info(f"Cloning {name} from {url} to {path}")
            success = self.git.clone_repo(url, path)
            results[name] = success
        
        return results
    
    def move_loom_to_foundry(self, dev_root: str) -> bool:
        """Move the loom repository to the foundry directory."""
        current_loom_path = Path(__file__).parent.parent
        foundry_dir = self.config.get_foundry_dir() or "foundry"
        target_loom_path = Path(dev_root) / foundry_dir / "loom"
        
        # If loom is already in the correct location, do nothing
        if current_loom_path == target_loom_path:
            logger.info("Loom is already in the correct location")
            return True
        
        # If target already exists, don't overwrite
        if target_loom_path.exists():
            logger.warning(f"Target loom directory {target_loom_path} already exists")
            return False
        
        try:
            # Move the entire loom directory
            shutil.move(str(current_loom_path), str(target_loom_path))
            logger.info(f"Moved loom from {current_loom_path} to {target_loom_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to move loom: {e}")
            return False
    
    def pull_all_repos(self) -> Dict[str, bool]:
        """Pull latest changes for all repositories."""
        repo_paths = self.get_repo_paths()
        results = {}
        
        # Use parallel execution if configured
        parallel = self.config.get_config('parallel_operations', True)
        
        if parallel:
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_repo = {
                    executor.submit(self.git.pull_repo, Path(path)): name
                    for name, path in repo_paths.items()
                    if Path(path).exists() and self.git.is_git_repo(Path(path))
                }
                
                for future in as_completed(future_to_repo):
                    repo_name = future_to_repo[future]
                    try:
                        results[repo_name] = future.result()
                    except Exception as e:
                        logger.error(f"Error pulling {repo_name}: {e}")
                        results[repo_name] = False
        else:
            for name, path in repo_paths.items():
                path_obj = Path(path)
                if path_obj.exists() and self.git.is_git_repo(path_obj):
                    results[name] = self.git.pull_repo(path_obj)
                else:
                    results[name] = False
        
        return results
    
    def get_all_status(self) -> Dict[str, Dict[str, str]]:
        """Get status for all repositories."""
        repo_paths = self.get_repo_paths()
        results = {}
        
        # Use parallel execution if configured
        parallel = self.config.get_config('parallel_operations', True)
        
        if parallel:
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_repo = {
                    executor.submit(self.git.get_repo_status, Path(path)): name
                    for name, path in repo_paths.items()
                }
                
                for future in as_completed(future_to_repo):
                    repo_name = future_to_repo[future]
                    try:
                        results[repo_name] = future.result()
                    except Exception as e:
                        logger.error(f"Error getting status for {repo_name}: {e}")
                        results[repo_name] = {"status": "error", "path": repo_paths[repo_name]}
        else:
            for name, path in repo_paths.items():
                results[name] = self.git.get_repo_status(Path(path))
        
        return results
    
    def execute_in_all_repos(self, command: List[str]) -> Dict[str, Tuple[bool, str, str]]:
        """Execute a command in all repositories."""
        repo_paths = self.get_repo_paths()
        results = {}
        
        for name, path in repo_paths.items():
            path_obj = Path(path)
            if path_obj.exists() and self.git.is_git_repo(path_obj):
                success, stdout, stderr = self.git.execute_command(path_obj, command)
                results[name] = (success, stdout, stderr)
            else:
                results[name] = (False, "", f"Repository {name} not found or not a git repo")
        
        return results
    
    def get_detailed_status(self) -> Dict[str, Dict[str, str]]:
        """Get detailed git status and diff statistics for all repositories."""
        repo_paths = self.get_repo_paths()
        results = {}
        
        for name, path in repo_paths.items():
            path_obj = Path(path)
            if path_obj.exists() and self.git.is_git_repo(path_obj):
                # Get status
                success, stdout, stderr = self.git.execute_command(
                    path_obj, 
                    ["git", "status", "--short", "--branch", "--show-stash"]
                )
                if success:
                    # Get diff statistics for modified files
                    diff_stats = self._get_diff_statistics(path_obj)
                    results[name] = {
                        "status": stdout,
                        "diff_stats": diff_stats
                    }
                else:
                    results[name] = {
                        "status": f"Error: {stderr}",
                        "diff_stats": {}
                    }
            else:
                results[name] = {
                    "status": "Repository not found or not a git repository",
                    "diff_stats": {}
                }
        
        return results
    
    def _get_diff_statistics(self, path: Path) -> Dict[str, str]:
        """Get diff statistics for modified files in a repository."""
        diff_stats = {}
        
        # Get list of modified files
        success, stdout, stderr = self.git.execute_command(
            path, 
            ["git", "diff", "--name-only"]
        )
        if not success:
            return diff_stats
        
        modified_files = [f.strip() for f in stdout.split('\n') if f.strip()]
        
        # Get diff statistics for each modified file
        for file_path in modified_files:
            success, stdout, stderr = self.git.execute_command(
                path, 
                ["git", "diff", "--stat", file_path]
            )
            if success and stdout.strip():
                # Parse the stat line (last line contains the summary)
                lines = stdout.strip().split('\n')
                if lines:
                    stat_line = lines[-1]
                    # Extract added/removed lines from stat line
                    # Format: " 1 file changed, 2 insertions(+), 1 deletion(-)"
                    import re
                    match = re.search(r'(\d+) insertions?\(\+\), (\d+) deletions?\(-\)', stat_line)
                    if match:
                        added = match.group(1)
                        removed = match.group(2)
                        diff_stats[file_path] = f"+{added} -{removed}"
        
        # Also scan for new directories and files that aren't tracked by git
        new_items = self._scan_new_directories(path)
        for item_path in new_items:
            diff_stats[item_path] = "NEW_DIR"
        
        return diff_stats
    
    def _scan_new_directories(self, path: Path) -> List[str]:
        """Scan for new directories and files that aren't tracked by git."""
        new_items = []
        
        # Get list of all tracked files
        success, stdout, stderr = self.git.execute_command(
            path, 
            ["git", "ls-files"]
        )
        if not success:
            return new_items
        
        tracked_files = set(f.strip() for f in stdout.split('\n') if f.strip())
        
        # Walk through the repository directory
        for root, dirs, files in os.walk(path):
            # Skip .git directory
            if '.git' in root:
                continue
            
            # Get relative path from repo root
            rel_root = os.path.relpath(root, path)
            if rel_root == '.':
                rel_root = ''
            
            # Check files (we'll handle directories by their files)
            for file_name in files:
                if file_name.startswith('.'):
                    continue  # Skip hidden files
                
                file_path = os.path.join(rel_root, file_name) if rel_root else file_name
                if file_path not in tracked_files:
                    new_items.append(file_path)
        
        return new_items
    
    def bootstrap_foundry(self, dev_root: str) -> bool:
        """Run the foundry-bootstrap setup."""
        foundry_bootstrap_path = Path(dev_root) / "foundry" / "foundry-bootstrap"
        bootstrap_script = foundry_bootstrap_path / "bootstrap.sh"
        
        if not foundry_bootstrap_path.exists():
            logger.error("foundry-bootstrap repository not found")
            return False
        
        if not bootstrap_script.exists():
            logger.error("bootstrap.sh script not found in foundry-bootstrap")
            return False
        
        try:
            # Make the script executable
            bootstrap_script.chmod(0o755)
            
            # Run the bootstrap script
            import subprocess
            result = subprocess.run(
                [str(bootstrap_script)],
                cwd=foundry_bootstrap_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("Successfully ran foundry-bootstrap")
                return True
            else:
                logger.error(f"Bootstrap failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error running bootstrap: {e}")
            return False 