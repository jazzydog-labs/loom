#!/bin/bash
# Demo script for BulkExecSvc - parallel command execution across repositories

set -e

echo "=== Loom BulkExecSvc Demo ==="
echo "This demo shows how to execute commands across multiple repositories in parallel."
echo

# Check if we're in the loom directory
if [ ! -f "loom.py" ]; then
    echo "Error: Please run this demo from the loom directory"
    exit 1
fi

echo "1. First, let's see all available repositories:"
echo "   $ python3 loom.py details"
echo
read -p "Press Enter to continue..."
python3 loom.py details | head -20
echo "..."
echo

echo "2. Let's check the current branch in all repositories:"
echo "   $ python3 loom.py exec 'git branch --show-current'"
echo
read -p "Press Enter to continue..."
python3 loom.py exec 'git branch --show-current'
echo

echo "3. Now let's check disk usage in each repository:"
echo "   $ python3 loom.py exec 'du -sh .'"
echo
read -p "Press Enter to continue..."
python3 loom.py exec 'du -sh .'
echo

echo "4. Let's run a command on specific repositories only:"
echo "   $ python3 loom.py exec 'git log --oneline -3' --repos loom,forge,crucible"
echo
read -p "Press Enter to continue..."
python3 loom.py exec 'git log --oneline -3' --repos loom,forge,crucible
echo

echo "5. We can also run commands with fewer workers for resource-intensive operations:"
echo "   $ python3 loom.py exec 'find . -name "*.py" | wc -l' --workers 4"
echo
read -p "Press Enter to continue..."
python3 loom.py exec 'find . -name "*.py" | wc -l' --workers 4
echo

echo "6. Let's see what happens when a command fails in some repos:"
echo "   $ python3 loom.py exec 'test -f README.md && echo "Has README" || exit 1'"
echo
read -p "Press Enter to continue..."
python3 loom.py exec 'test -f README.md && echo "Has README" || exit 1' || true
echo

echo "7. You can disable the summary for more compact output:"
echo "   $ python3 loom.py exec 'pwd' --no-summary"
echo
read -p "Press Enter to continue..."
python3 loom.py exec 'pwd' --no-summary
echo

echo "=== Demo Complete ==="
echo
echo "The BulkExecSvc allows you to:"
echo "- Execute any shell command across all repositories in parallel"
echo "- Target specific repositories with --repos"
echo "- Control parallelism with --workers"
echo "- See detailed results and summary statistics"
echo "- Handle failures gracefully"
echo
echo "This is useful for:"
echo "- Checking status across repos (git status, git branch)"
echo "- Running builds or tests in parallel"
echo "- Gathering information (disk usage, file counts)"
echo "- Performing bulk operations (git pull, npm install)"