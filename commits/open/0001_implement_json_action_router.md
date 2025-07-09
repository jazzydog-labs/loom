# Implement JSON Action Router

Create a unified JSON-based interface for all Loom operations, providing a schema-driven approach to invoke any Loom functionality through JSON events/actions.

## Overview

The JSON Action Router will serve as a universal entry point for Loom, accepting JSON objects that describe actions to perform. This creates a decoupled, event-driven architecture where actions can originate from:
- CLI commands (translated to JSON)
- Direct JSON input via CLI
- HTTP API endpoints
- Message queues
- File watchers
- Other scripts/tools
- Future integrations

## Core Concepts

### Action Schema
Each action is a JSON object with:
- `action`: The operation to perform (e.g., "freeze.create", "bulk.execute", "stash.save")
- `version`: Schema version for forward compatibility
- `payload`: Action-specific parameters
- `metadata`: Optional tracking information (request_id, timestamp, source, etc.)

### Router Architecture
- **Action Registry**: Maps action names to handlers
- **Schema Validator**: Validates JSON against action schemas
- **Handler Interface**: Consistent interface for all action handlers
- **Response Format**: Standardized success/error responses

## Tasks:
- [ ] Create touchpoints/ directory structure
- [ ] Design base action schema
- [ ] Create action schemas for existing commands:
  - [ ] freeze.create / freeze.restore
  - [ ] bulk.execute
  - [ ] stash.save / stash.restore / stash.list
  - [ ] repo.status / repo.health
  - [ ] just.run
- [ ] Implement JsonActionRouter in app/
- [ ] Create ActionHandler base class
- [ ] Implement handlers for each action type
- [ ] Add JSON input mode to CLI (`loom json <action.json>` or `loom json -`)
- [ ] Create comprehensive test suite
- [ ] Document public API in touchpoints/README.md

## Directory Structure:
```
touchpoints/
├── README.md                    # Public API documentation
├── schemas/
│   ├── base.schema.json        # Base action schema
│   ├── freeze.schema.json      # Freeze-related actions
│   ├── bulk.schema.json        # Bulk execution actions
│   ├── stash.schema.json       # Stash management actions
│   ├── repo.schema.json        # Repository status actions
│   └── just.schema.json        # Just recipe actions
├── examples/
│   ├── freeze-create.json      # Example freeze creation
│   ├── bulk-execute.json       # Example bulk command
│   ├── stash-save.json         # Example stash operation
│   └── pipeline.json           # Example action pipeline
└── handlers/
    └── __init__.py             # Handler registry initialization

src/app/json_action_router.py   # Main router implementation
src/app/action_handlers/        # Individual action handlers
tests/app/test_json_router.py   # Router tests
```

## Example Actions:

### Freeze Create
```json
{
  "action": "freeze.create",
  "version": "1.0",
  "payload": {
    "repos": ["repo1", "repo2"],
    "name": "before-upgrade",
    "message": "Snapshot before system upgrade"
  },
  "metadata": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-09T10:30:00Z",
    "source": "cli"
  }
}
```

### Bulk Execute
```json
{
  "action": "bulk.execute",
  "version": "1.0",
  "payload": {
    "command": "git pull origin main",
    "repos": ["*"],
    "parallel": true,
    "continue_on_error": true
  }
}
```

### Action Pipeline
```json
{
  "action": "pipeline",
  "version": "1.0",
  "payload": {
    "actions": [
      {
        "action": "stash.save",
        "payload": {"repos": ["*"], "message": "Before update"}
      },
      {
        "action": "bulk.execute",
        "payload": {"command": "git pull", "repos": ["*"]}
      },
      {
        "action": "just.run",
        "payload": {"recipe": "test", "repos": ["*"]}
      }
    ],
    "stop_on_error": true
  }
}
```

## Benefits:
- **Unified Interface**: Single entry point for all Loom operations
- **Language Agnostic**: Any tool that can produce JSON can control Loom
- **Composability**: Actions can be combined into pipelines
- **Testability**: Easy to test with JSON fixtures
- **Extensibility**: New actions can be added without changing the router
- **Audit Trail**: All actions can be logged with metadata
- **Integration Ready**: Easy to expose via HTTP API, message queues, etc.

## Implementation Notes:
- Use JSON Schema for validation
- Actions should be idempotent where possible
- Include dry-run support in schema
- Support both sync and async execution modes
- Provide detailed error messages with action context
- Consider rate limiting and authentication hooks