"""Repository management and orchestration for loom."""

import shutil
from pathlib import Path
from typing import Dict, Optional
import logging
import subprocess

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
    
    def bootstrap_foundry(self, dev_root: str) -> bool:
        """Run the foundry-bootstrap script if available."""
        foundry_dir = self.config.get_foundry_dir() or "foundry"
        script = Path(dev_root) / foundry_dir / "foundry-bootstrap" / "bootstrap.sh"
        if not script.exists():
            return False
        try:
            subprocess.run(["bash", str(script)], check=True)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Bootstrap failed: %s", exc)
            return False
