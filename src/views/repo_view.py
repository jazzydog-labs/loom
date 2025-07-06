"""Repository view for CLI display."""

from typing import Dict, List, Any, Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns
from rich.box import ROUNDED
import json

from utils.repo_status_reader import RepoStatusReader
from loomlib.emojis import get_emoji_manager
from loomlib.color_manager import ColorManager


class RepoView:
    """Modular CLI view for displaying repository information."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the view with an optional console instance.
        
        Args:
            console: Rich console instance. If None, creates a new one.
        """
        self.console = console or Console()
        
        # Get emoji manager and build emoji configuration
        emoji_mgr = get_emoji_manager()
        self.symbols = {
            'folder': emoji_mgr.get('files', 'folder'),
            'dir_sep': emoji_mgr.get('ui', 'dir_sep'),
            'root': '.',
            'added': emoji_mgr.get('git', 'added'),
            'modified': emoji_mgr.get('git', 'modified'),
            'deleted': emoji_mgr.get('git', 'deleted'),
            'renamed': emoji_mgr.get('git', 'renamed'),
            'copied': emoji_mgr.get('git', 'copied'),
            'unmerged': emoji_mgr.get('git', 'unmerged'),
            'untracked': emoji_mgr.get('git', 'untracked'),
            'ignored': emoji_mgr.get('git', 'ignored'),
            'stash': emoji_mgr.get('git', 'staged'),
            'clean': emoji_mgr.get('git_workflow', 'clean'),
            'branch': emoji_mgr.get('git_workflow', 'branch'),
            'staged_edit': emoji_mgr.get('git_workflow', 'staged_edit'),
            'success': emoji_mgr.get('status', 'success'),
            'warning': emoji_mgr.get('status', 'warning'),
            'error': emoji_mgr.get('status', 'error'),
            'ahead': emoji_mgr.get('git_workflow', 'ahead'),
            'behind': emoji_mgr.get('git_workflow', 'behind'),
        }
        
        # Initialize color manager
        self.color_manager = ColorManager()
    
    @property
    def emojis(self):
        """Alias for symbols to match test expectations."""
        return self.symbols

    def display_summary(self, repo_name: str, summary: Dict[str, Any]) -> None:
        """Display a complete repository summary.
        
        Args:
            repo_name: Name of the repository
            summary: Summary dictionary from RepoStatusReader.summary()
        """
        print(f"DEBUG: summary = {summary}")
        repo_status = summary.get('repo_status', {})
        file_status = summary.get('file_status', {})
        file_counts = summary.get('file_counts', {})
        
        # Display header
        self._display_header(repo_name, repo_status)
        
        # Display file changes if any
        if any(count > 0 for count in file_counts.values()):
            self._display_file_changes(file_status, file_counts)
        else:
            self.console.print(f"  {self.symbols['clean']} Working directory is clean")
        
    
    def display_status_table(self, statuses: Dict[str, Dict[str, Any]]) -> None:
        """Display repository statuses in a table format.
        
        Args:
            statuses: Dictionary mapping repo names to their status information
        """
        table = Table(title="Repository Status", box=ROUNDED)
        table.add_column("Repository", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("Branch", style="green")
        table.add_column("Ahead/Behind", style="yellow")
        table.add_column("Path", style="dim")
        
        for name, status in statuses.items():
            status_color = self._get_status_color(status.get("status", "unknown"))
            ahead_behind = f"{status.get('ahead', 0)}/{status.get('behind', 0)}"
            
            table.add_row(
                name,
                f"[{status_color}]{status.get('status', 'unknown')}[/{status_color}]",
                status.get("branch", "N/A"),
                ahead_behind,
                status.get("path", "N/A")
            )
        
        self.console.print(table)
    
    def display_json(self, data: Dict[str, Any], pretty: bool = True) -> None:
        """Display data as formatted JSON.
        
        Args:
            data: Data to display
            pretty: Whether to format JSON with indentation
        """
        if pretty:
            json_str = json.dumps(data, indent=2)
        else:
            json_str = json.dumps(data)
        
        panel = Panel(json_str, title="JSON Output", border_style="blue")
        self.console.print(panel)
    
    def display_file_status(self, file_status: Dict[str, List[Dict[str, Any]]]) -> None:
        """Display file status information.
        
        Args:
            file_status: File status dictionary from RepoStatusReader.file_status()
        """
        # Group files by directory
        files_by_dir = self._group_files_by_directory(file_status)
        
        # Sort directories: base directory (.) first, then subdirectories alphabetically
        sorted_dirs = sorted(files_by_dir.keys(), key=lambda x: (x != "", x))
        
        for directory in sorted_dirs:
            files = files_by_dir[directory]
            
            if directory == "":
                # Base directory files - no folder icon, just files
                indent = "  "
            else:
                # Subdirectory - show folder icon
                self.console.print(f"  {self.symbols['folder']} {directory} {self.symbols['dir_sep']} ")
                indent = "    "
            
            # Debug: print files_by_dir for troubleshooting
            # print(f"DEBUG: files_by_dir = {files_by_dir}")
            
            # Group files on the same line
            file_line = []
            for emoji, filename in files:
                file_line.append(f"{emoji} {filename}")
            
            # Join files with spaces
            self.console.print(f"{indent}{' '.join(file_line)}")
    
    def display_repo_status(self, repo_status: Dict[str, Any]) -> None:
        """Display repository status information.
        
        Args:
            repo_status: Repository status dictionary from RepoStatusReader.repo_status()
        """
        if "error" in repo_status:
            self.console.print(f"  {self.symbols['error']} Error: {repo_status['error']}")
            return
        
        # Branch information
        branch = repo_status.get("branch", "unknown")
        upstream = repo_status.get("upstream_branch")
        
        if upstream:
            branch_text = f"{branch}...{upstream}"
        else:
            branch_text = branch
        
        # Ahead/behind information
        ahead = repo_status.get("ahead_count", 0)
        behind = repo_status.get("behind_count", 0)
        
        ahead_behind_text = ""
        if ahead > 0:
            ahead_text = f"{self.symbols['ahead']}{ahead}"
            ahead_behind_text += f" {self.color_manager.format_ahead_behind(ahead_text, True)}"
        if behind > 0:
            behind_text = f"{self.symbols['behind']}{behind}"
            ahead_behind_text += f" {self.color_manager.format_ahead_behind(behind_text, False)}"
        
        # Clean status
        is_clean = repo_status.get("is_clean", False)
        clean_icon = self.symbols['clean'] if is_clean else self.symbols['warning']
        
        # Last commit
        last_commit = repo_status.get("last_commit_message", "No commits")
        
        # Display
        self.console.print(f"  {self.symbols['branch']} {branch_text}{ahead_behind_text}")
        status_text = 'Clean' if is_clean else 'Dirty'
        status_color = self.color_manager.get_color("success") if is_clean else self.color_manager.get_color("warning")
        self.console.print(f"  {clean_icon} [{status_color}]{status_text}[/{status_color}]")
        self.console.print(f"  📝 {last_commit}")
    
    def _display_header(self, repo_name: str, repo_status: Dict[str, Any]) -> None:
        """Display repository header with branch information.
        
        Args:
            repo_name: Name of the repository
            repo_status: Repository status information
        """
        if "error" in repo_status:
            self.console.print(f"\n{self.color_manager.format_header(repo_name)}")
            self.console.print(f"  {self.symbols['error']} Error getting status")
            return
        
        branch = repo_status.get("branch", "unknown")
        upstream = repo_status.get("upstream_branch")
        is_clean = repo_status.get("is_clean", False)
        
        # Build header text
        if upstream:
            header = f"{repo_name} {self.symbols['branch']} {branch}...{upstream}"
        else:
            header = f"{repo_name} {self.symbols['branch']} {branch}"
        
        # Add ahead/behind info
        ahead = repo_status.get("ahead_count", 0)
        behind = repo_status.get("behind_count", 0)
        
        if ahead > 0:
            ahead_text = f"{self.symbols['ahead']}{ahead}"
            header += f" {self.color_manager.format_ahead_behind(ahead_text, True)}"
        if behind > 0:
            behind_text = f"{self.symbols['behind']}{behind}"
            header += f" {self.color_manager.format_ahead_behind(behind_text, False)}"
        
        # Display header with appropriate styling using color manager
        formatted_header = self.color_manager.format_repo_header(header, is_clean)
        if is_clean:
            clean_sparkles = self.color_manager.format_text(self.symbols['clean'] * 3, "clean_sparkles")
            self.console.print(f"{formatted_header} {clean_sparkles}")
        else:
            self.console.print(f"{formatted_header}")
    
    def _display_file_changes(self, file_status: Dict[str, List[Dict[str, Any]]], file_counts: Dict[str, int]) -> None:
        """Display file changes grouped by directory.
        
        Args:
            file_status: File status information
            file_counts: File count summary
        """
        # Group files by directory
        files_by_dir = self._group_files_by_directory(file_status)
        
        # Sort directories: base directory ("") first, then subdirectories alphabetically
        sorted_dirs = sorted(files_by_dir.keys(), key=lambda x: (x != "", x))
        
        for directory in sorted_dirs:
            files = files_by_dir[directory]
            
            if directory == "":
                # Base directory files - no folder icon, just files
                indent = "  "
            else:
                # Subdirectory - show folder icon
                print(f"DEBUG: directory = {directory}")
                self.console.print(f"  {self.symbols['folder']} {directory} {self.symbols['dir_sep']} ")
                indent = "    "
            
            # Debug: print files_by_dir for troubleshooting
            # print(f"DEBUG: files_by_dir = {files_by_dir}")
            
            # Group files on the same line
            file_line = []
            for emoji, filename in files:
                file_line.append(f"{emoji} {filename}")
            
            # Join files with spaces
            self.console.print(f"{indent}{' '.join(file_line)}")
    
    def _group_files_by_directory(self, file_status: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[tuple]]:
        """Group files by directory for display.
        
        Args:
            file_status: File status information
            
        Returns:
            Dictionary mapping directories to lists of (emoji, filename) tuples
        """
        files_by_dir = {}
        
        # Process each status type
        status_mapping = {
            "staged": self.symbols['staged_edit'],
            "modified": self.symbols['modified'],
            "untracked": self.symbols['untracked'],
            "deleted": self.symbols['deleted'],
            "renamed": self.symbols['renamed'],
            "unmerged": self.symbols['unmerged']
        }
        
        for status_type, emoji in status_mapping.items():
            for file_info in file_status.get(status_type, []):
                print(f"DEBUG: file_info = {file_info}")
                filename = file_info.get("path", "")
                
                # Extract directory and filename
                if '/' in filename:
                    dir_part, file_part = filename.rsplit('/', 1)
                    if dir_part not in files_by_dir:
                        files_by_dir[dir_part] = []
                    files_by_dir[dir_part].append((emoji, file_part))
                else:
                    # Use empty string for base directory files
                    if "" not in files_by_dir:
                        files_by_dir[""] = []
                    files_by_dir[""].append((emoji, filename))
        
        return files_by_dir
    
    def _get_status_color(self, status: str) -> str:
        """Get color for status display.
        
        Args:
            status: Status string
            
        Returns:
            Color name for rich formatting
        """
        color_map = {
            "clean": "green",
            "dirty": "red",
            "missing": "red",
            "not_git": "yellow",
            "error": "red"
        }
        return color_map.get(status, "white")
    
    def display_multiple_repos(self, repos_data: Dict[str, Dict[str, Any]]) -> None:
        """Display multiple repositories in a consolidated view.
        
        Args:
            repos_data: Dictionary mapping repo names to their summary data
        """
        for repo_name, summary in repos_data.items():
            self.display_summary(repo_name, summary)


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python repo_view.py <repo_path>")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    
    try:
        # Create reader and view
        reader = RepoStatusReader(repo_path)
        view = RepoView()
        
        # Get summary and display it
        summary = reader.get_summary_json()
        view.display_summary("test-repo", summary)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1) 