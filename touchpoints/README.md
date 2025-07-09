# Loom Public API - Touchpoints

This directory defines the public interface for Loom, including all supported commands and JSON-based actions.

## Overview

Loom can be accessed through multiple interfaces:
1. **CLI Commands**: Direct command-line interface
2. **JSON Actions**: Schema-driven JSON objects that describe operations
3. **Python API**: Direct Python imports (for advanced usage)

## CLI Commands

### Repository Management
- `loom status [repos...]` - Show repository status
- `loom health [repos...]` - Check repository health

### Freeze Operations
- `loom freeze <name> [repos...]` - Create a snapshot
- `loom restore <name> [repos...]` - Restore from snapshot
- `loom list-freezes` - List available snapshots

### Bulk Operations
- `loom bulk <command> [repos...]` - Execute command across repos
- `loom just <recipe> [repos...]` - Run just recipes across repos

### Stash Management
- `loom stash [repos...]` - Stash changes
- `loom stash-restore [repos...]` - Restore stashed changes
- `loom stash-list [repos...]` - List stashes

## JSON Action Interface

All operations can also be invoked via JSON:

```bash
# From file
loom json action.json

# From stdin
echo '{"action": "repo.status", "payload": {"repos": ["*"]}}' | loom json -

# From CLI argument
loom json '{"action": "freeze.create", "payload": {"name": "backup"}}'
```

## Action Schemas

All JSON actions follow schemas defined in `schemas/`. Each action has:
- Defined input schema for validation
- Consistent error handling
- Standardized response format

See individual schema files for detailed specifications.

## Examples

The `examples/` directory contains sample JSON actions for common operations.

## Integration

The JSON interface makes Loom easy to integrate with:
- CI/CD pipelines
- Monitoring systems
- Custom scripts
- Web services
- Message queues

## Versioning

All JSON actions include a version field for backward compatibility. The current version is "1.0".