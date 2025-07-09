#!/bin/bash
# Demo script for 'loom do' command - running tasks with error filtering

set -e

echo "=== 🧪 Loom 'do' Command Demo ==="
echo "Running tasks across repositories with intelligent error filtering"
echo

# Check if we're in the loom directory
if [ ! -f "loom.py" ]; then
    echo "Error: Please run this demo from the loom directory"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Checking which repositories have a 'just test' command"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "First, let's see which repos have a justfile with a test recipe..."
echo
python3 loom.py exec 'test -f justfile && grep -q "^test:" justfile && echo "✓ Has test recipe" || echo "✗ No test recipe"'

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 Running tests in all repositories (errors only)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Running 'just test' and filtering for errors/failures..."
echo
python3 loom.py do test || true

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Demonstrating error detection with a failing command"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Let's run a command that will have some failures to show error filtering..."
echo
# Create a temporary justfile that has a recipe that fails in some cases
TEMP_JUST=$(mktemp)
cat > "$TEMP_JUST" << 'EOF'
check-python:
	@python3 -c "import sys; print('Python:', sys.version.split()[0]); import this_module_does_not_exist" || echo "ERROR: Missing module!"
EOF

echo "Testing with a recipe that checks for a non-existent Python module..."
python3 loom.py exec "cp $TEMP_JUST justfile.tmp && just -f justfile.tmp check-python && rm -f justfile.tmp" --repos loom,forge,crucible --no-summary || true
rm -f "$TEMP_JUST"

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Running with verbose mode to see all output"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Same test command but with --verbose to see everything..."
echo
python3 loom.py do test --repos loom --verbose

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 Common tasks you can run with 'loom do'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Examples of useful commands:"
echo "  • loom do test         - Run tests in all repos, show only failures"
echo "  • loom do lint         - Run linters, show only issues"
echo "  • loom do build        - Build all projects, show only errors"
echo "  • loom do check        - Run checks, show only problems"
echo "  • loom do fmt          - Format code, show only errors"
echo
echo "Add --verbose to see all output, or --repos to target specific repos"

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Demo Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "The 'loom do' command helps you:"
echo "• Run common tasks across all repositories in parallel"
echo "• Automatically filter output to show only errors and failures"
echo "• Save time by focusing on what needs attention"
echo "• Use --verbose when you need to see all output"
echo
echo "Perfect for CI/CD workflows and daily development tasks!"