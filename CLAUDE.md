# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Setup
```bash
pip install -r requirements.txt
python3 loom.py init --dev-root ~/dev  # Initialize foundry ecosystem
```

### Testing
```bash
just test  # Run all tests
pytest tests/path/to/specific_test.py  # Run specific test
pytest -v  # Run tests with verbose output
```

### Running Commands
The main entry point is `loom.py` which wraps `src/main.py`. All commands are available via:
```bash
python3 loom.py <command>
```

Key commands:
- `init` - Clone all repositories and set up foundry ecosystem
- `status` - Show aggregated repository status
- `details` - Show detailed git status for all repositories
- `sync` - Sync clean repositories (git pull in parallel)
- `todos` - Display pending TODOs across repositories
- `go <repo>` - Navigate to a specific repository

## Architecture Overview

This is a CLI tool for orchestrating multiple Git repositories in a "foundry" ecosystem. The codebase follows Domain-Driven Design (DDD) with a layered architecture:

### Core Domain Model
- **Foundry**: Aggregate root managing multiple repositories as a cohesive unit
- **Repo**: Domain entity representing a Git repository with status tracking
- **FreezeSnapshot**: Immutable value object capturing point-in-time state of all repos

### Layer Structure
```
src/
├── cli/          # Typer CLI commands (thin layer)
├── app/          # Application layer (LoomController)
├── services/     # Application services (orchestration logic)
├── domain/       # Core business entities and logic
├── infra/        # Infrastructure gateways and adapters
├── events/       # Event bus for decoupled communication
├── plugins/      # Plugin registry for extensibility
└── utils/        # Shared utilities (worker pool, etc.)
```

### Key Design Patterns
- **Controller Pattern**: `LoomController` handles all CLI commands
- **Repository Pattern**: Domain entities encapsulate business logic
- **Gateway Pattern**: Infrastructure gateways abstract external dependencies
- **Worker Pool**: Parallel execution for multi-repo operations
- **Event-Driven**: Domain events enable decoupled components

### Important Implementation Notes
1. The project is actively being refactored to full DDD architecture - many services in `src/services/` are still TODO placeholders
2. Git operations use GitPython library with lazy loading for performance
3. Parallel operations use `utils.worker_pool.map_parallel` for concurrent execution
4. Configuration files are in `config/` directory (repos.yaml, defaults.yaml)
5. User overrides can be placed in `~/.loomrc`

### Testing Approach
- Framework: pytest
- Test structure mirrors source under `tests/`
- Currently limited coverage - many tests are skeleton placeholders
- Run specific test files to avoid running incomplete tests

### Commit Workflow
When working on tasks from `commits/open/`:
1. Complete the implementation as described in the commit file
2. Update the commit file to mark all tasks as completed and add "Status: COMPLETED ✓"
3. Move the commit file from `commits/open/` to `commits/closed/` as part of your changes
4. Include this file move in your git commit along with the implementation

When implementing new features:
1. Follow the existing DDD structure
2. Use the worker pool for any parallel operations
3. Emit appropriate domain events for state changes
4. Add unit tests following the existing test structure pattern

## Demos
- When adding any feature, please demo that feature in a `scripts/demos/*` script, and make sure that if you're creating a new demo script we are also adding it to `just demo`

### Good Citizen Principle
Be a good citizen and fix failing tests, even if they're not your responsibility! If you encounter failing tests while working on a feature:
1. Investigate the root cause
2. Fix the test if it's a simple issue
3. Ensure all tests pass before committing
4. Include the fix in your commit with a note about being a good citizen

## Demo Guidelines

When creating demos, ALWAYS start with a "killer feature" that is:
- **Concise**: Show the most impressive capability in 2-3 lines of code
- **Attention-grabbing**: Demonstrate immediate value
- **To the point**: No setup, just the wow factor
- **Practical**: Show why users should care

Example format:
```python
def demo_killer_feature():
    """The ONE thing that makes this feature amazing."""
    print("=== KILLER FEATURE: Transform any idea into 10 refined versions in seconds ===")
    idea = Idea.create("Basic concept", score=5.0)
    best_version = idea.auto_refine(iterations=10).get_best_version()
    print(f"Original score: 5.0 → Best score: {best_version.score} (+{best_version.score - 5.0} improvement!)")
```

Then proceed with the detailed demo sections.