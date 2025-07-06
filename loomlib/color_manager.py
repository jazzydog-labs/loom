"""Color management for loom CLI."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ColorManager:
    """Manages color configuration for the loom CLI."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the color manager with configuration."""
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "config" / "colors.yaml")
        
        self.config_path = Path(config_path)
        self.colors = self._load_colors()
    
    def _load_colors(self) -> Dict[str, Any]:
        """Load colors from configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('colors', {})
        except (FileNotFoundError, yaml.YAMLError) as e:
            # Fallback to default colors if config file is missing or invalid
            return self._get_default_colors()
    
    def _get_default_colors(self) -> Dict[str, str]:
        # TODO: source this from a default colors.yaml file
        """Get default colors if config file is not available."""
        return {
            'repo_header_clean': '#B8860B',
            'repo_header_dirty': '#008B8B',
            'clean_sparkles': 'yellow',
            'error': 'red',
            'warning': 'yellow',
            'success': 'green',
            'git_added': 'green',
            'git_modified': 'yellow',
            'git_deleted': 'red',
            'git_renamed': 'magenta',
            'git_untracked': 'white',
            'git_ignored': 'dim',
            'separator': 'cyan',
            'header': 'bold cyan',
            'progress': 'cyan',
            'ahead': 'green',
            'behind': 'red'
        }
    
    def get_color(self, color_name: str, default: str = "white") -> str:
        """Get a color by name."""
        return self.colors.get(color_name, default)
    
    def format_text(self, text: str, color_name: str, style: str = "") -> str:
        """Format text with color and optional style."""
        color = self.get_color(color_name)
        if style:
            return f"[{style} {color}]{text}[/{style} {color}]"
        return f"[{color}]{text}[/{color}]"
    
    def format_bold(self, text: str, color_name: str) -> str:
        """Format text as bold with color."""
        return self.format_text(text, color_name, "bold")
    
    def format_header(self, text: str) -> str:
        """Format a header with the header color."""
        return self.format_bold(text, "header")
    
    def format_repo_header(self, text: str, is_clean: bool = False) -> str:
        """Format a repository header."""
        color_name = "repo_header_clean" if is_clean else "repo_header_dirty"
        return self.format_bold(text, color_name)
    
    def format_git_status(self, text: str, status_type: str) -> str:
        """Format git status text."""
        color_name = f"git_{status_type}"
        return self.format_text(text, color_name)
    
    # TODO: this is a bit of a hack, we should be able to specify ahead/behind colors in the colors.yaml file
    # TODO: can we use domain objects and each should have a canonical color/ representation?
    def format_ahead_behind(self, text: str, is_ahead: bool) -> str:
        """Format ahead/behind indicators."""
        color_name = "ahead" if is_ahead else "behind"
        return self.format_text(text, color_name) 