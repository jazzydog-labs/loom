"""
Emoji utility module for loom.
Loads emojis from config/emojis.yaml and provides easy access to them.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional


class EmojiManager:
    """Manages emoji access from the configuration file."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the emoji manager.
        
        Args:
            config_path: Path to the emoji config file. If None, uses default location.
        """
        if config_path is None:
            # Default to config/emojis.yaml relative to this module
            module_dir = Path(__file__).parent.parent
            config_path = str(module_dir / "config" / "emojis.yaml")
        
        self.config_path = Path(config_path)
        self._emojis = None
    
    def _load_emojis(self) -> Dict[str, Any]:
        """Load emojis from the configuration file."""
        if self._emojis is None:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Emoji config file not found: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._emojis = yaml.safe_load(f)
        
        return self._emojis
    
    def get(self, category: str, key: str) -> str:
        """Get an emoji by category and key.
        
        Args:
            category: The emoji category (e.g., 'status', 'git', 'files')
            key: The specific emoji key within the category
            
        Returns:
            The emoji string
            
        Raises:
            KeyError: If category or key doesn't exist
        """
        emojis = self._load_emojis()
        return emojis[category][key]
    
    def get_status(self, key: str) -> str:
        """Get a status emoji."""
        return self.get('status', key)
    
    def get_git(self, key: str) -> str:
        """Get a git status emoji."""
        return self.get('git', key)
    
    def get_files(self, key: str) -> str:
        """Get a file/directory emoji."""
        return self.get('files', key)
    
    def get_process(self, key: str) -> str:
        """Get a process emoji."""
        return self.get('process', key)
    
    def get_development(self, key: str) -> str:
        """Get a development emoji."""
        return self.get('development', key)
    
    def get_ui(self, key: str) -> str:
        """Get a UI emoji."""
        return self.get('ui', key)
    
    def get_special(self, key: str) -> str:
        """Get a special purpose emoji."""
        return self.get('special', key)
    
    def all(self) -> Dict[str, Any]:
        """Get all emojis."""
        return self._load_emojis()


# Global emoji manager instance
_emoji_manager = None


def get_emoji_manager() -> EmojiManager:
    """Get the global emoji manager instance."""
    global _emoji_manager
    if _emoji_manager is None:
        _emoji_manager = EmojiManager()
    return _emoji_manager


# Convenience functions for common emojis
def success() -> str:
    """Get success emoji."""
    return get_emoji_manager().get_status('success')


def error() -> str:
    """Get error emoji."""
    return get_emoji_manager().get_status('error')


def warning() -> str:
    """Get warning emoji."""
    return get_emoji_manager().get_status('warning')


def info() -> str:
    """Get info emoji."""
    return get_emoji_manager().get_status('info')


def folder() -> str:
    """Get folder emoji."""
    return get_emoji_manager().get_files('folder')


def file() -> str:
    """Get file emoji."""
    return get_emoji_manager().get_files('file')


def modified() -> str:
    """Get modified emoji."""
    return get_emoji_manager().get_git('modified')


def deleted() -> str:
    """Get deleted emoji."""
    return get_emoji_manager().get_git('deleted')


def added() -> str:
    """Get added emoji."""
    return get_emoji_manager().get_git('added')


def unmerged() -> str:
    """Get unmerged emoji."""
    return get_emoji_manager().get_git('unmerged')


def loom() -> str:
    """Get loom emoji."""
    return get_emoji_manager().get_special('loom')


def foundry() -> str:
    """Get foundry emoji."""
    return get_emoji_manager().get_special('foundry')


def bootstrap() -> str:
    """Get bootstrap emoji."""
    return get_emoji_manager().get_special('bootstrap')


def setup() -> str:
    """Get setup emoji."""
    return get_emoji_manager().get_special('setup')


def init() -> str:
    """Get init emoji."""
    return get_emoji_manager().get_special('init')


def tool() -> str:
    """Get tool emoji."""
    return get_emoji_manager().get_development('tool')


def test() -> str:
    """Get test emoji."""
    return get_emoji_manager().get_development('test')


def build() -> str:
    """Get build emoji."""
    return get_emoji_manager().get_development('build')


def deploy() -> str:
    """Get deploy emoji."""
    return get_emoji_manager().get_development('deploy')


def arrow_right() -> str:
    """Get right arrow emoji."""
    return get_emoji_manager().get_ui('arrow_right')


def arrow_left() -> str:
    """Get left arrow emoji."""
    return get_emoji_manager().get_ui('arrow_left')


def checkmark() -> str:
    """Get checkmark emoji."""
    return get_emoji_manager().get_ui('checkmark')


def cross() -> str:
    """Get cross emoji."""
    return get_emoji_manager().get_ui('cross') 