#!/usr/bin/env python3
"""
Example demonstrating parallel buffered view generation for multiple repositories.

This example shows three different approaches for generating views in parallel:
1. ThreadPoolExecutor with buffered output
2. Asyncio with buffered output
3. Batched processing for large numbers of repositories

Usage:
    cd loom
    python -m src.examples.example_parallel_views
"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, Any

# Use relative imports from src/examples
from src.views.repo_view import RepoView
from src.utils.repo_status_reader import RepoStatusReader
from src.core.repo_manager import RepoManager
from src.core.config import ConfigManager
from src.core.git import GitManager


def create_sample_repos_data() -> Dict[str, Dict[str, Any]]:
    """Create sample repository data for demonstration."""
    return {
        "loom": {
            "repo_status": {
                "branch": "main",
                "is_clean": True,
                "last_commit_sha": "abc123",
                "last_commit_message": "Add parallel view generation",
                "ahead_count": 0,
                "behind_count": 0,
                "upstream_branch": "origin/main"
            },
            "file_status": {
                "staged": [],
                "modified": [],
                "untracked": [],
                "deleted": [],
                "renamed": [],
                "unmerged": []
            },
            "file_counts": {
                "staged": 0,
                "modified": 0,
                "untracked": 0,
                "deleted": 0,
                "renamed": 0,
                "unmerged": 0
            }
        },
        "foundry": {
            "repo_status": {
                "branch": "feature/parallel-views",
                "is_clean": False,
                "last_commit_sha": "def456",
                "last_commit_message": "Work in progress",
                "ahead_count": 2,
                "behind_count": 1,
                "upstream_branch": "origin/main"
            },
            "file_status": {
                "staged": [{"path": "src/views/repo_view.py", "status": "modified"}],
                "modified": [{"path": "README.md", "status": "modified"}],
                "untracked": [{"path": "example_parallel_views.py", "status": "untracked"}],
                "deleted": [],
                "renamed": [],
                "unmerged": []
            },
            "file_counts": {
                "staged": 1,
                "modified": 1,
                "untracked": 1,
                "deleted": 0,
                "renamed": 0,
                "unmerged": 0
            }
        },
        "panorama": {
            "repo_status": {
                "branch": "develop",
                "is_clean": True,
                "last_commit_sha": "ghi789",
                "last_commit_message": "Update documentation",
                "ahead_count": 0,
                "behind_count": 0,
                "upstream_branch": "origin/develop"
            },
            "file_status": {
                "staged": [],
                "modified": [],
                "untracked": [],
                "deleted": [],
                "renamed": [],
                "unmerged": []
            },
            "file_counts": {
                "staged": 0,
                "modified": 0,
                "untracked": 0,
                "deleted": 0,
                "renamed": 0,
                "unmerged": 0
            }
        }
    }


def get_real_repos_data() -> Dict[str, Dict[str, Any]]:
    """Get real repository data from the configured repositories."""
    try:
        config_manager = ConfigManager()
        git_manager = GitManager()
        repo_manager = RepoManager(config_manager, git_manager)
        
        # Get all configured repositories
        repo_paths = repo_manager.get_repo_paths()
        repos_data = {}
        
        for repo_name, repo_path in repo_paths.items():
            try:
                reader = RepoStatusReader(repo_path)
                summary = reader.get_summary_json()
                repos_data[repo_name] = summary
            except Exception as e:
                # Create error summary for repositories that can't be read
                repos_data[repo_name] = {
                    "repo_status": {"error": f"Failed to read repository: {e}"},
                    "file_status": {},
                    "file_counts": {}
                }
        
        return repos_data
    except Exception as e:
        print(f"⚠️  Could not load real repository data: {e}")
        print("📝 Using sample data instead...")
        return create_sample_repos_data()


def demonstrate_parallel_views():
    """Demonstrate different parallel view generation methods."""
    print("🚀 Parallel Repository View Generation Demo")
    print("=" * 50)
    
    # Get repository data
    repos_data = get_real_repos_data()
    print(f"📊 Processing {len(repos_data)} repositories...")
    
    # Create view instance
    view = RepoView()
    
    # Method 1: ThreadPoolExecutor with buffered output
    print("\n1️⃣ ThreadPoolExecutor Method (Recommended)")
    print("-" * 40)
    import time
    start_time = time.time()
    
    view.display_multiple_repos_parallel(repos_data, max_workers=4)
    
    parallel_time = time.time() - start_time
    print(f"⏱️  Parallel processing time: {parallel_time:.2f} seconds")
    
    # Method 2: Sequential processing (for comparison)
    print("\n2️⃣ Sequential Method (For Comparison)")
    print("-" * 40)
    start_time = time.time()
    
    for repo_name, summary in repos_data.items():
        view.display_summary(repo_name, summary)
    
    sequential_time = time.time() - start_time
    print(f"⏱️  Sequential processing time: {sequential_time:.2f} seconds")
    
    # Show performance improvement
    if sequential_time > 0:
        speedup = sequential_time / parallel_time
        print(f"🏆 Speedup: {speedup:.1f}x faster with parallel processing")
    
    # Method 3: Batched processing (for large numbers of repos)
    print("\n3️⃣ Batched Processing Method")
    print("-" * 40)
    start_time = time.time()
    
    view.display_multiple_repos_batched(repos_data, batch_size=2, max_workers=2)
    
    batched_time = time.time() - start_time
    print(f"⏱️  Batched processing time: {batched_time:.2f} seconds")


async def demonstrate_async_views():
    """Demonstrate async view generation."""
    print("\n4️⃣ Async Processing Method")
    print("-" * 40)
    
    repos_data = get_real_repos_data()
    view = RepoView()
    
    import time
    start_time = time.time()
    
    await view.display_multiple_repos_async(repos_data, max_concurrent=4)
    
    async_time = time.time() - start_time
    print(f"⏱️  Async processing time: {async_time:.2f} seconds")


def main():
    """Main demonstration function."""
    try:
        # Demonstrate synchronous parallel methods
        demonstrate_parallel_views()
        
        # Demonstrate async method
        print("\n" + "=" * 50)
        asyncio.run(demonstrate_async_views())
        
        print("\n✅ All demonstrations completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 