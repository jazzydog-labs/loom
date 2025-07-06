# RepoStatusReader

A read-only Git repository status reader that provides JSON-serializable status information suitable for CQRS queries and multi-repo wrapper projects.

## Overview

The `RepoStatusReader` class provides structured, read-only access to Git repository status information. It's designed to be lightweight, fast, and produce consistent JSON output that can be easily consumed by downstream systems, dashboards, or APIs.

## Features

- **Read-only operations**: No mutations to the repository
- **JSON-serializable output**: All methods return dictionaries that can be easily serialized
- **Comprehensive status**: File status, repository status, and consolidated summaries
- **CQRS-friendly**: Designed for read-side queries in CQRS patterns
- **Lightweight**: Uses standard Git plumbing commands
- **Error handling**: Graceful handling of Git errors and edge cases

## Usage

### Basic Usage

```python
from utils.repo_status_reader import RepoStatusReader

# Initialize with repository path
reader = RepoStatusReader("/path/to/git/repo")

# Get file status
file_status = reader.file_status()

# Get repository status
repo_status = reader.repo_status()

# Get complete summary
summary = reader.summary()
```

### Integration with Loom

```python
from utils.repo_status_reader import RepoStatusReader
from loomlib.config import ConfigManager
from loomlib.git import GitManager
from loomlib.repo_manager import RepoManager

# Initialize loom components
config_manager = ConfigManager()
git_manager = GitManager()
repo_manager = RepoManager(config_manager, git_manager)

# Get repositories from config
repos_config = config_manager.load_repos()
repos = repos_config.get('repos', [])

# Use RepoStatusReader for each repository
for repo in repos:
    try:
        reader = RepoStatusReader(repo['path'])
        summary = reader.summary()
        
        # Process the structured data
        if not summary['repo_status']['is_clean']:
            print(f"Repository {repo['name']} has changes")
            
    except Exception as e:
        print(f"Error reading {repo['name']}: {e}")
```

## API Reference

### Constructor

```python
RepoStatusReader(repo_root: str)
```

- `repo_root`: Path to the Git repository root directory

### Methods

#### `file_status() -> Dict[str, List[Dict[str, Any]]]`

Returns staged, modified, and untracked files with their paths.

**Returns:**
```json
{
  "staged": [
    {"path": "src/main.py", "status": "modified"},
    {"path": "new_file.txt", "status": "added"}
  ],
  "modified": [
    {"path": "README.md", "status": "modified"}
  ],
  "untracked": [
    {"path": "temp.log", "status": "untracked"}
  ],
  "deleted": [
    {"path": "old_file.txt", "status": "deleted"}
  ],
  "renamed": [
    {
      "path": "new_name.py",
      "status": "renamed",
      "original_path": "old_name.py"
    }
  ],
  "unmerged": []
}
```

#### `repo_status() -> Dict[str, Any]`

Returns current branch, clean/dirty flag, last commit info, and ahead/behind counts.

**Returns:**
```json
{
  "branch": "main",
  "is_clean": false,
  "last_commit_sha": "a1b2c3d4e5f6789012345678901234567890abcd",
  "last_commit_message": "feat: add new feature",
  "ahead_count": 2,
  "behind_count": 0,
  "upstream_branch": "origin/main"
}
```

#### `summary() -> Dict[str, Any]`

Returns consolidated snapshot combining file and repository status.

**Returns:**
```json
{
  "repository_path": "/path/to/repo",
  "file_status": { /* file_status() output */ },
  "file_counts": {
    "staged": 2,
    "modified": 2,
    "untracked": 2,
    "deleted": 1,
    "renamed": 1,
    "unmerged": 0
  },
  "repo_status": { /* repo_status() output */ },
  "timestamp": null
}
```

## CQRS Usage Examples

### Query Handler Pattern

```python
def get_repo_summary_query(repo_path: str) -> dict:
    """CQRS query to get repository summary."""
    reader = RepoStatusReader(repo_path)
    return reader.summary()

def get_dirty_repos_query(repos: list) -> list:
    """CQRS query to find all dirty repositories."""
    dirty_repos = []
    for repo in repos:
        try:
            reader = RepoStatusReader(repo['path'])
            summary = reader.summary()
            if not summary['repo_status']['is_clean']:
                dirty_repos.append({
                    'name': repo['name'],
                    'path': repo['path'],
                    'status': summary['repo_status'],
                    'file_counts': summary['file_counts']
                })
        except Exception:
            continue
    return dirty_repos
```

### Dashboard Integration

```python
def get_dashboard_data(repos: list) -> dict:
    """Get data for a repository dashboard."""
    dashboard_data = {
        'total_repos': len(repos),
        'clean_repos': 0,
        'dirty_repos': 0,
        'total_changes': 0,
        'repos_with_upstream_changes': 0
    }
    
    for repo in repos:
        try:
            reader = RepoStatusReader(repo['path'])
            summary = reader.summary()
            
            if summary['repo_status']['is_clean']:
                dashboard_data['clean_repos'] += 1
            else:
                dashboard_data['dirty_repos'] += 1
                dashboard_data['total_changes'] += sum(summary['file_counts'].values())
            
            if summary['repo_status']['ahead_count'] > 0 or summary['repo_status']['behind_count'] > 0:
                dashboard_data['repos_with_upstream_changes'] += 1
                
        except Exception:
            continue
    
    return dashboard_data
```

## Testing

Run the test script to see the JSON structure and test with a real repository:

```bash
# Show example JSON structure
python src/utils/test_repo_status_reader.py --example

# Test with a real repository
python src/utils/test_repo_status_reader.py /path/to/git/repo

# Run integration example
python src/utils/integration_example.py
```

## Error Handling

The class handles various error conditions gracefully:

- **Repository not found**: Raises `ValueError`
- **Not a Git repository**: Raises `ValueError`
- **Git command failures**: Returns empty results or error indicators
- **Timeout**: Handles command timeouts gracefully

## Dependencies

- Python 3.7+
- Standard library only (no external dependencies)
- Git command-line tools must be available in PATH

## Design Principles

1. **Read-only**: No mutations to the repository
2. **JSON-serializable**: All output is ready for serialization
3. **CQRS-friendly**: Designed for read-side queries
4. **Lightweight**: Uses Git plumbing commands efficiently
5. **Consistent**: Predictable output structure
6. **Error-resilient**: Graceful handling of edge cases 
