"""Repository management and orchestration for loom."""

import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

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