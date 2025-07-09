#!/usr/bin/env python3
"""Analyze common directories across repositories."""

import json
import subprocess
from collections import Counter
from pathlib import Path

def get_repo_directories():
    """Get directory listings from all repositories using loom exec."""
    # Run loom exec to get directories from all repos
    cmd = ["python3", "loom.py", "exec", 
           r'find . -type d -not -path "*/\.*" -maxdepth 2 | sed "s|^./||" | grep -v "^\.$"',
           "--no-summary"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse the output
    repo_dirs = {}
    current_repo = None
    in_table = False
    
    for line in result.stdout.splitlines():
        if "│" in line and not line.startswith("┃"):  # Data row
            parts = [p.strip() for p in line.split("│")]
            if len(parts) >= 5:  # Valid data row
                repo_name = parts[1]
                output = parts[4]
                if output and not output.startswith("No output"):
                    # Split directories by whitespace or newline
                    dirs = [d.strip() for d in output.split() if d.strip()]
                    repo_dirs[repo_name] = dirs
    
    return repo_dirs

def analyze_directories(repo_dirs):
    """Analyze common directories across repositories."""
    # Count directory occurrences
    dir_counter = Counter()
    repo_count = len(repo_dirs)
    
    for repo, dirs in repo_dirs.items():
        for d in dirs:
            if d:  # Skip empty strings
                dir_counter[d] += 1
    
    # Sort by frequency
    common_dirs = dir_counter.most_common()
    
    print("📊 Directory Analysis Report")
    print("=" * 60)
    print(f"Total repositories analyzed: {repo_count}")
    print()
    
    # Show directories present in multiple repos
    print("📁 Common Directories (present in 2+ repositories):")
    print("-" * 60)
    print(f"{'Count':>5}  {'Percentage':>10}  Directory")
    print("-" * 60)
    
    for dir_name, count in common_dirs:
        if count > 1:
            percentage = (count / repo_count) * 100
            print(f"{count:5d}  {percentage:9.1f}%  {dir_name}")
    
    print()
    
    # Show directories present in ALL repos
    universal_dirs = [d for d, c in common_dirs if c == repo_count]
    if universal_dirs:
        print("🌟 Universal Directories (present in ALL repositories):")
        print("-" * 60)
        for d in universal_dirs:
            print(f"  • {d}")
    else:
        print("ℹ️  No directories are present in all repositories")
    
    print()
    
    # Show unique directories per repo
    print("🔧 Unique Directories by Repository:")
    print("-" * 60)
    
    for repo, dirs in sorted(repo_dirs.items()):
        unique_dirs = [d for d in dirs if dir_counter[d] == 1]
        if unique_dirs:
            print(f"\n{repo}:")
            for d in sorted(unique_dirs)[:5]:  # Show max 5 unique dirs
                print(f"  • {d}")
            if len(unique_dirs) > 5:
                print(f"  ... and {len(unique_dirs) - 5} more")

if __name__ == "__main__":
    print("Analyzing directory structures across repositories...\n")
    repo_dirs = get_repo_directories()
    if repo_dirs:
        analyze_directories(repo_dirs)
    else:
        print("Error: Could not retrieve directory information")