#!/bin/bash
# Demo script for JSON Action Router - unified JSON interface for all Loom operations

set -e

echo "=== 🎯 Loom JSON Action Router Demo ==="
echo "Demonstrating unified JSON interface for all Loom operations"
echo

# Check if we're in the loom directory
if [ ! -f "loom.py" ]; then
    echo "Error: Please run this demo from the loom directory"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 KILLER FEATURE: Control Loom with JSON from anywhere!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Shell command:"
echo '  echo '"'"'{"action": "repo.status", "version": "1.0"}'"'"' | loom json -'
echo
echo "✨ Any tool that produces JSON can control Loom"
echo "✨ Language-agnostic integration"
echo "✨ Composable action pipelines"
echo "✨ Schema validation for reliability"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 JSON Action Router Overview"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "The JSON Action Router provides:"
echo "  • Unified interface for all Loom operations"
echo "  • JSON schema validation"
echo "  • Action composition and pipelines"
echo "  • Metadata tracking and audit trails"
echo "  • Easy integration with CI/CD and automation"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Available Actions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Listing all available actions..."
python3 -m src.main json
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣ REPOSITORY STATUS (Direct JSON)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Getting repository status via JSON..."
echo 'Command: loom json '"'"'{"action": "repo.status", "version": "1.0", "payload": {"repos": ["loom"]}}'"'"
echo
python3 -m src.main json '{"action": "repo.status", "version": "1.0", "payload": {"repos": ["loom"]}}'
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣ FREEZE CREATE (From File)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Creating freeze using example JSON file..."
echo "File content:"
cat touchpoints/examples/freeze-create.json | head -10
echo "..."
echo
echo "Command: loom json touchpoints/examples/freeze-create.json"
echo "(Skipping actual execution to avoid creating freeze)"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣ BULK EXECUTE (Via stdin)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Executing command across repos via stdin..."
cat > /tmp/bulk_action.json << 'EOF'
{
  "action": "bulk.execute",
  "version": "1.0",
  "payload": {
    "command": "echo 'Hello from JSON Action Router'",
    "repos": ["loom"],
    "parallel": false
  },
  "metadata": {
    "source": "demo",
    "dry_run": false
  }
}
EOF

echo "Command: cat /tmp/bulk_action.json | loom json -"
cat /tmp/bulk_action.json | python3 -m src.main json -
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣ REPOSITORY HEALTH CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Checking repository health..."
python3 -m src.main json '{
  "action": "repo.health",
  "version": "1.0",
  "payload": {
    "repos": ["loom"],
    "checks": ["uncommitted_changes", "untracked_files"]
  }
}'
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣ DRY RUN MODE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Testing dry run mode (no changes made)..."
python3 -m src.main json '{
  "action": "freeze.create",
  "version": "1.0",
  "payload": {
    "name": "test-dry-run",
    "repos": ["*"]
  },
  "metadata": {
    "dry_run": true
  }
}'
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣ ACTION PIPELINE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Creating a pipeline of actions..."
cat > /tmp/pipeline.json << 'EOF'
{
  "action": "pipeline",
  "version": "1.0",
  "payload": {
    "actions": [
      {
        "action": "repo.status",
        "version": "1.0",
        "payload": {"repos": ["loom"]}
      },
      {
        "action": "repo.health",
        "version": "1.0",
        "payload": {"repos": ["loom"]}
      }
    ],
    "stop_on_error": true
  },
  "metadata": {
    "source": "demo",
    "correlation_id": "demo-pipeline-001"
  }
}
EOF

echo "Executing pipeline..."
cat /tmp/pipeline.json | python3 -m src.main json -
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7️⃣ ERROR HANDLING"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Testing error handling with invalid action..."
python3 -m src.main json '{"action": "invalid.action", "version": "1.0"}' || true
echo
echo "Testing with invalid JSON..."
echo "Command: loom json 'invalid json'"
python3 -m src.main json 'invalid json' 2>&1 || true
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8️⃣ INTEGRATION EXAMPLES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Example: CI/CD Integration"
echo "  curl -X POST https://ci.example.com/webhook \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"action\": \"freeze.create\", \"payload\": {\"name\": \"pre-deploy\"}}'"
echo
echo "Example: Python Script Integration"
cat << 'PYTHON'
import json
import subprocess

action = {
    "action": "bulk.execute",
    "version": "1.0",
    "payload": {
        "command": "git status",
        "repos": ["*"]
    }
}

result = subprocess.run(
    ["loom", "json", "-"],
    input=json.dumps(action),
    capture_output=True,
    text=True
)
response = json.loads(result.stdout)
PYTHON
echo
echo "Example: Monitoring System"
echo '  watch -n 60 '"'"'echo {"action":"repo.health","version":"1.0"} | loom json -'"'"
echo

# Cleanup
rm -f /tmp/bulk_action.json /tmp/pipeline.json

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Key Takeaways"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "• JSON Action Router provides a unified interface for all Loom operations"
echo "• Actions can be executed from files, stdin, or direct JSON strings"
echo "• Schema validation ensures reliable operation"
echo "• Pipelines enable complex workflows"
echo "• Metadata tracking provides audit trails"
echo "• Language-agnostic integration via JSON"
echo
echo "The JSON Action Router makes Loom a universal orchestration platform!"