"""Configuration management for loom."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages loom configuration including user config and repo definitions."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(__file__).parent.parent / "config"
        self.defaults_file = self.config_dir / "defaults.yaml"
        self.repos_file = Path(__file__).parent.parent / "repos.yaml"
        self.user_config_file = Path(__file__).parent.parent / ".loomrc"
        self._repos = None
        self._user_config = None
        self._defaults = None
    
    def load_defaults(self) -> Dict[str, Any]:
        """Load default configuration."""
        if self._defaults is None:
            if self.defaults_file.exists():
                with open(self.defaults_file, 'r') as f:
                    self._defaults = yaml.safe_load(f)
            else:
                self._defaults = {}
        return self._defaults
    
    def load_repos(self) -> Dict[str, Any]:
        """Load repository definitions."""
        if self._repos is None:
            if self.repos_file.exists():
                with open(self.repos_file, 'r') as f:
                    self._repos = yaml.safe_load(f)
            else:
                self._repos = {"repos": []}
        return self._repos
    
    def load_user_config(self, prompt_if_missing=True) -> Dict[str, Any]:
        """Load user-specific configuration."""
        if self._user_config is None:
            if self.user_config_file.exists():
                with open(self.user_config_file, 'r') as f:
                    self._user_config = yaml.safe_load(f) or {}
            elif prompt_if_missing:
                print("Loom setup: Please configure your development environment.")
                dev_root = input("Enter your development root directory (e.g. ~/dev/jazzydog-labs): ").strip()
                foundry_dir = input("Enter your foundry directory name (default: foundry): ").strip() or "foundry"
                self._user_config = {"dev_root": dev_root, "foundry_dir": foundry_dir}
                with open(self.user_config_file, 'w') as f:
                    yaml.dump(self._user_config, f)
            else:
                self._user_config = {}
        return self._user_config
    
    def get_dev_root(self) -> Optional[str]:
        """Get the development root directory."""
        user_config = self.load_user_config()
        return user_config.get('dev_root')
    
    def get_foundry_dir(self) -> Optional[str]:
        """Get the foundry directory name."""
        user_config = self.load_user_config()
        return user_config.get('foundry_dir', 'foundry')
    
    def set_user_config(self, dev_root: str, foundry_dir: str) -> None:
        """Set the user configuration."""
        self._user_config = {"dev_root": dev_root, "foundry_dir": foundry_dir}
        with open(self.user_config_file, 'w') as f:
            yaml.dump(self._user_config, f)
    
    def get_repo_paths(self, dev_root: str, foundry_dir: str) -> Dict[str, str]:
        """Get repository paths with resolved dev_root and foundry_dir."""
        repos_config = self.load_repos()
        repo_paths = {}
        
        for repo in repos_config.get('repos', []):
            name = repo['name']
            path = repo['path'].replace('$DEV_ROOT', dev_root).replace('$FOUNDRY_DIR', foundry_dir)
            repo_paths[name] = path
        
        return repo_paths
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback chain: user -> defaults."""
        user_config = self.load_user_config()
        if key in user_config:
            return user_config[key]
        
        defaults = self.load_defaults()
        return defaults.get('defaults', {}).get(key, default) 