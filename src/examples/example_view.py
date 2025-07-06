#!/usr/bin/env python3
"""Example script demonstrating the RepoView class with the loom repository."""

import sys
from pathlib import Path

# Type ignore comments for linter
from src.utils.repo_status_reader import RepoStatusReader  # type: ignore
from src.views.repo_view import RepoView  # type: ignore


def main():
    """Demonstrate the RepoView class with the loom repository."""
    
    # Get the current directory (loom repository)
    repo_path = Path.cwd()
    
    try:
        # Create reader and view
        reader = RepoStatusReader(str(repo_path))
        view = RepoView()
        
        # Get summary and display it
        summary = reader.get_summary_json()
        view.display_summary("loom", summary)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 