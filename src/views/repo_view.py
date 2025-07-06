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
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

from ..utils.repo_status_reader import RepoStatusReader
from ..utils.emojis import get_emoji_manager
from ..utils.color_manager import ColorManager


class BufferedRepoView:
    """Buffered version of RepoView that captures output instead of printing directly."""
    
    def __init__(self):
        """Initialize buffered view with string buffer."""
        self.buffer = io.StringIO()
        self.console = Console(file=self.buffer, width=120)
        
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
    
    def get_output(self) -> str:
        """Get the buffered output as a string."""
        return self.buffer.getvalue()
    
    def display_summary(self, repo_name: str, summary: Dict[str, Any]) -> None:
        """Display a complete repository summary to buffer."""
        repo_status = summary.get('repo_status', {})
        file_status = summary.get('file_status', {})
        file_counts = summary.get('file_counts', {})
        
        # Display header
        self._display_header(repo_name, repo_status)
        
        # Display file changes if any
        if any(count > 0 for count in file_counts.values()):
            self._display_file_changes(file_status, file_counts)
        
        # Add spacing after each repo
        self.console.print()
    
    def _display_header(self, repo_name: str, repo_status: Dict[str, Any]) -> None:
        """Display repository header with branch information."""
        if "error" in repo_status:
            self.console.print(f"\n{self.color_manager.format_header(repo_name)}")
            self.console.print(f"  {self.symbols['error']} Error getting status")
            return
        
        branch = repo_status.get("branch", "unknown")
        upstream = repo_status.get("upstream_branch")
        remote_name = repo_status.get("remote_name")
        is_clean = repo_status.get("is_clean", False)
        
        # Build header text with remote information
        header = f"{repo_name} {self.symbols['branch']} {branch}"
        
        # Add upstream/remote info with arrow notation
        if upstream:
            if remote_name:
                # Show just the branch part after the remote name for cleaner display
                upstream_branch_only = upstream.split('/')[-1] if '/' in upstream else upstream
                if upstream_branch_only == branch:
                    # Same branch name, just show remote
                    header += f" → {remote_name}"
                else:
                    # Different branch name, show full upstream
                    header += f" → {upstream}"
            else:
                header += f" → {upstream}"
        
        # Add ahead/behind info
        ahead = repo_status.get("ahead_count", 0)
        behind = repo_status.get("behind_count", 0)
        
        status_indicators = []
        if ahead > 0:
            ahead_text = f"{self.symbols['ahead']}{ahead}"
            status_indicators.append(self.color_manager.format_ahead_behind(ahead_text, True))
        if behind > 0:
            behind_text = f"{self.symbols['behind']}{behind}"
            status_indicators.append(self.color_manager.format_ahead_behind(behind_text, False))
        
        if status_indicators:
            header += f" {' '.join(status_indicators)}"
        
        # Display header with appropriate styling using color manager
        formatted_header = self.color_manager.format_repo_header(header, is_clean)
        if is_clean:
            clean_sparkles = self.color_manager.format_text(self.symbols['clean'] * 3, "clean_sparkles")
            # Print header line with sparkles
            self.console.print(f"{formatted_header} {clean_sparkles}")
        else:
            self.console.print(f"{formatted_header}")
    
    def _display_file_changes(self, file_status: Dict[str, List[Dict[str, Any]]], file_counts: Dict[str, int]) -> None:
        """Display file changes grouped by directory."""
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
                self.console.print(f"  {self.symbols['folder']} {directory} {self.symbols['dir_sep']} ")
                indent = "    "
            
            # Group files on the same line
            file_line = []
            for emoji, filename in files:
                file_line.append(f"{emoji} {filename}")
            
            # Join files with spaces
            self.console.print(f"{indent}{' '.join(file_line)}")
    
    def _group_files_by_directory(self, file_status: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[tuple]]:
        """Group files by directory for display."""
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
    
    # Remove property decorator since we're setting self.symbols directly

    def display_summary(self, repo_name: str, summary: Dict[str, Any]) -> None:
        """Display a complete repository summary.
        
        Args:
            repo_name: Name of the repository
            summary: Summary dictionary from RepoStatusReader.get_summary_json()
        """
        repo_status = summary.get('repo_status', {})
        file_status = summary.get('file_status', {})
        file_counts = summary.get('file_counts', {})
        
        # Display header
        self._display_header(repo_name, repo_status)
        
        # Display file changes if any
        if any(count > 0 for count in file_counts.values()):
            self._display_file_changes(file_status, file_counts)
        
    def display_multiple_repos_parallel(self, repos_data: Dict[str, Dict[str, Any]], max_workers: int = 4) -> None:
        """Display multiple repositories using parallel processing with buffered output.
        
        Args:
            repos_data: Dictionary mapping repo names to their summary data
            max_workers: Maximum number of worker threads
        """
        def process_repo(repo_name: str, summary: Dict[str, Any]) -> tuple[str, str]:
            """Process a single repository and return its buffered output."""
            buffered_view = BufferedRepoView()
            buffered_view.display_summary(repo_name, summary)
            return repo_name, buffered_view.get_output()
        
        # Process all repositories in parallel
        buffered_outputs = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_repo = {
                executor.submit(process_repo, repo_name, summary): repo_name
                for repo_name, summary in repos_data.items()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_repo):
                repo_name = future_to_repo[future]
                try:
                    _, output = future.result()
                    buffered_outputs[repo_name] = output
                except Exception as e:
                    # Handle errors gracefully
                    error_output = f"\n{repo_name}\n  ❌ Error processing repository: {e}\n"
                    buffered_outputs[repo_name] = error_output
        
        # Display all results in a consistent order
        for repo_name in sorted(buffered_outputs.keys()):
            self.console.print(buffered_outputs[repo_name], end="")
    
    async def display_multiple_repos_async(self, repos_data: Dict[str, Dict[str, Any]], max_concurrent: int = 4) -> None:
        """Display multiple repositories using async processing with buffered output.
        
        Args:
            repos_data: Dictionary mapping repo names to their summary data
            max_concurrent: Maximum number of concurrent tasks
        """
        async def process_repo_async(repo_name: str, summary: Dict[str, Any]) -> tuple[str, str]:
            """Process a single repository asynchronously."""
            # Run the blocking operation in a thread pool
            loop = asyncio.get_event_loop()
            buffered_view = BufferedRepoView()
            
            def sync_process():
                buffered_view.display_summary(repo_name, summary)
                return buffered_view.get_output()
            
            output = await loop.run_in_executor(None, sync_process)
            return repo_name, output
        
        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_process(repo_name: str, summary: Dict[str, Any]) -> tuple[str, str]:
            async with semaphore:
                return await process_repo_async(repo_name, summary)
        
        # Process all repositories concurrently
        tasks = [
            bounded_process(repo_name, summary)
            for repo_name, summary in repos_data.items()
        ]
        
        # Collect results
        buffered_outputs = {}
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            repo_names = list(repos_data.keys())
            
            for i, result in enumerate(results):
                repo_name = repo_names[i]
                if isinstance(result, Exception):
                    error_output = f"\n{repo_name}\n  ❌ Error processing repository: {result}\n"
                    buffered_outputs[repo_name] = error_output
                else:
                    # Result should be a tuple (repo_name, output)
                    if isinstance(result, tuple) and len(result) == 2:
                        _, output = result
                        buffered_outputs[repo_name] = output
                    else:
                        error_output = f"\n{repo_name}\n  ❌ Unexpected result format: {result}\n"
                        buffered_outputs[repo_name] = error_output
        except Exception as e:
            self.console.print(f"❌ Error in async processing: {e}")
            return
        
        # Display all results in a consistent order
        for repo_name in sorted(buffered_outputs.keys()):
            self.console.print(buffered_outputs[repo_name], end="")
    
    def display_multiple_repos_batched(self, repos_data: Dict[str, Dict[str, Any]], batch_size: int = 10, max_workers: int = 4) -> None:
        """Display multiple repositories using batched parallel processing.
        
        This is useful for very large numbers of repositories to avoid overwhelming the system.
        
        Args:
            repos_data: Dictionary mapping repo names to their summary data
            batch_size: Number of repositories to process in each batch
            max_workers: Maximum number of worker threads per batch
        """
        def process_batch(batch_repos: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
            """Process a batch of repositories."""
            def process_repo(repo_name: str, summary: Dict[str, Any]) -> tuple[str, str]:
                buffered_view = BufferedRepoView()
                buffered_view.display_summary(repo_name, summary)
                return repo_name, buffered_view.get_output()
            
            batch_outputs = {}
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_repo = {
                    executor.submit(process_repo, repo_name, summary): repo_name
                    for repo_name, summary in batch_repos.items()
                }
                
                for future in as_completed(future_to_repo):
                    repo_name = future_to_repo[future]
                    try:
                        _, output = future.result()
                        batch_outputs[repo_name] = output
                    except Exception as e:
                        error_output = f"\n{repo_name}\n  ❌ Error processing repository: {e}\n"
                        batch_outputs[repo_name] = error_output
            
            return batch_outputs
        
        # Split repositories into batches
        repo_items = list(repos_data.items())
        all_outputs = {}
        
        for i in range(0, len(repo_items), batch_size):
            batch = dict(repo_items[i:i + batch_size])
            batch_outputs = process_batch(batch)
            all_outputs.update(batch_outputs)
            
            # Optional: Add progress indication
            processed = min(i + batch_size, len(repo_items))
            self.console.print(f"📊 Processed {processed}/{len(repo_items)} repositories...", style="dim")
        
        # Display all results in a consistent order
        for repo_name in sorted(all_outputs.keys()):
            self.console.print(all_outputs[repo_name], end="")

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
        remote_name = repo_status.get("remote_name")
        is_clean = repo_status.get("is_clean", False)
        
        # Build header text with remote information
        header = f"{repo_name} {self.symbols['branch']} {branch}"
        
        # Add upstream/remote info with arrow notation
        if upstream:
            if remote_name:
                # Show just the branch part after the remote name for cleaner display
                upstream_branch_only = upstream.split('/')[-1] if '/' in upstream else upstream
                if upstream_branch_only == branch:
                    # Same branch name, just show remote
                    header += f" → {remote_name}"
                else:
                    # Different branch name, show full upstream
                    header += f" → {upstream}"
            else:
                header += f" → {upstream}"
        
        # Add ahead/behind info
        ahead = repo_status.get("ahead_count", 0)
        behind = repo_status.get("behind_count", 0)
        
        status_indicators = []
        if ahead > 0:
            ahead_text = f"{self.symbols['ahead']}{ahead}"
            status_indicators.append(self.color_manager.format_ahead_behind(ahead_text, True))
        if behind > 0:
            behind_text = f"{self.symbols['behind']}{behind}"
            status_indicators.append(self.color_manager.format_ahead_behind(behind_text, False))
        
        if status_indicators:
            header += f" {' '.join(status_indicators)}"
        
        # Display header with appropriate styling using color manager
        formatted_header = self.color_manager.format_repo_header(header, is_clean)
        if is_clean:
            clean_sparkles = self.color_manager.format_text(self.symbols['clean'] * 3, "clean_sparkles")
            # Print header line with sparkles
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
                self.console.print(f"  {self.symbols['folder']} {directory} {self.symbols['dir_sep']} ")
                indent = "    "
            
            
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