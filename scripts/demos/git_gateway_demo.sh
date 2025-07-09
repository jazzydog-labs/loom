#!/bin/bash
# Demo script for GitGateway - robust Git command execution with retries

set -e

echo "=== 🔧 Loom GitGateway Demo ==="
echo "Demonstrating robust Git command execution with proper error handling"
echo

# Check if we're in the loom directory
if [ ! -f "loom.py" ]; then
    echo "Error: Please run this demo from the loom directory"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ KILLER FEATURE: Never lose work to Git lock errors again!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Quick killer feature demo
cat > /tmp/git_gateway_killer.py << 'EOF'
#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.getcwd())
from src.infra.git_gateway import GitGateway

# GitGateway automatically retries on lock errors - no more failed CI builds!
gateway = GitGateway()
result = gateway.push('.')  # Retries 3x if another process has the lock
print(f"✅ Push {'succeeded' if result['success'] else 'failed'} - handled lock errors automatically!")
EOF

echo "Python code:"
echo "  gateway = GitGateway()"
echo "  result = gateway.push('.')  # Auto-retries on lock errors!"
echo
echo "No more:"
echo "  ❌ 'fatal: Unable to create .git/index.lock'"
echo "  ❌ 'Another git process seems to be running'"
echo "  ❌ Failed CI builds due to transient Git errors"
echo

rm -f /tmp/git_gateway_killer.py

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 GitGateway Overview"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "GitGateway provides:"
echo "  • Robust subprocess handling for Git commands"
echo "  • Automatic retry logic for transient failures"
echo "  • Proper error handling and timeout support"
echo "  • Convenience methods for common Git operations"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Demonstrating All GitGateway Methods"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Create a Python script to demonstrate GitGateway
cat > /tmp/git_gateway_demo.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.getcwd())

from src.infra.git_gateway import GitGateway, GitCommandError
from pathlib import Path
import json

def print_result(method_name, result):
    """Pretty print the result of a GitGateway method."""
    print(f"\n📌 {method_name}:")
    if result.get('success'):
        print(f"   ✅ Success")
        if result.get('stdout'):
            output = result['stdout'].strip()
            if output:
                # Limit output to first 3 lines for brevity
                lines = output.split('\n')[:3]
                for line in lines:
                    print(f"   → {line}")
                if len(output.split('\n')) > 3:
                    print(f"   → ... ({len(output.split('\n')) - 3} more lines)")
    else:
        print(f"   ❌ Failed: {result.get('stderr', 'Unknown error')}")

def main():
    # Initialize GitGateway
    gateway = GitGateway(retry_count=3, retry_delay=1.0)
    print("Initialized GitGateway with retry_count=3, retry_delay=1.0")
    
    # Working directory for demos
    cwd = Path.cwd()
    
    print("\n" + "─" * 70)
    print("1️⃣ STATUS - Check repository status")
    print("─" * 70)
    
    # Get status
    result = gateway.status(cwd)
    print_result("gateway.status(cwd)", result)
    
    # Get status non-porcelain (human readable)
    result = gateway.status(cwd, porcelain=False)
    print_result("gateway.status(cwd, porcelain=False)", result)
    
    print("\n" + "─" * 70)
    print("2️⃣ BRANCH - List branches")
    print("─" * 70)
    
    # List local branches
    result = gateway.branch(cwd)
    print_result("gateway.branch(cwd)", result)
    
    # List all branches (including remote)
    result = gateway.branch(cwd, all_branches=True)
    print_result("gateway.branch(cwd, all_branches=True)", result)
    
    print("\n" + "─" * 70)
    print("3️⃣ LOG - View commit history")
    print("─" * 70)
    
    # Get recent commits (oneline)
    result = gateway.log(cwd, oneline=True, limit=5)
    print_result("gateway.log(cwd, oneline=True, limit=5)", result)
    
    # Get commits with date filter
    result = gateway.log(cwd, since="1.week.ago", limit=3)
    print_result("gateway.log(cwd, since='1.week.ago', limit=3)", result)
    
    print("\n" + "─" * 70)
    print("4️⃣ DIFF - Show changes")
    print("─" * 70)
    
    # Show unstaged changes (file names only)
    result = gateway.diff(cwd, name_only=True)
    print_result("gateway.diff(cwd, name_only=True)", result)
    
    # Show staged changes
    result = gateway.diff(cwd, cached=True, name_only=True)
    print_result("gateway.diff(cwd, cached=True, name_only=True)", result)
    
    print("\n" + "─" * 70)
    print("5️⃣ REMOTE - Show remote repositories")
    print("─" * 70)
    
    # List remotes
    result = gateway.remote(cwd)
    print_result("gateway.remote(cwd)", result)
    
    # List remotes with URLs
    result = gateway.remote(cwd, verbose=True)
    print_result("gateway.remote(cwd, verbose=True)", result)
    
    print("\n" + "─" * 70)
    print("6️⃣ STASH - Stash operations")
    print("─" * 70)
    
    # List stashes
    result = gateway.stash(cwd, command="list")
    print_result("gateway.stash(cwd, command='list')", result)
    
    print("\n" + "─" * 70)
    print("7️⃣ DIRECT COMMAND - Run arbitrary git commands")
    print("─" * 70)
    
    # Show git version
    result = gateway.run(['--version'])
    print_result("gateway.run(['--version'])", result)
    
    # Show current branch using symbolic-ref
    result = gateway.run(['symbolic-ref', '--short', 'HEAD'], cwd=cwd, check=False)
    print_result("gateway.run(['symbolic-ref', '--short', 'HEAD'])", result)
    
    print("\n" + "─" * 70)
    print("8️⃣ ERROR HANDLING - Demonstrate error handling")
    print("─" * 70)
    
    # Try to checkout non-existent branch (will fail)
    try:
        result = gateway.checkout('non-existent-branch-xyz', cwd)
        print_result("gateway.checkout('non-existent-branch-xyz')", result)
    except GitCommandError as e:
        print(f"\n📌 gateway.checkout('non-existent-branch-xyz'):")
        print(f"   ❌ GitCommandError raised (as expected)")
        print(f"   → Error: {e.stderr.strip()}")
        print(f"   → Return code: {e.return_code}")
    
    # Demonstrate check=False with run method
    result = gateway.run(['checkout', 'non-existent-branch-xyz'], cwd=cwd, check=False)
    print_result("gateway.run(['checkout', 'non-existent-branch-xyz'], check=False)", result)
    print(f"   → With check=False, no exception raised")
    print(f"   → Return code: {result['return_code']}")
    
    print("\n" + "─" * 70)
    print("9️⃣ RETRY LOGIC - Simulating retry behavior")
    print("─" * 70)
    
    print("\nGitGateway automatically retries on these errors:")
    print("  • 'Unable to create .git/index.lock'")
    print("  • 'Cannot lock ref'")
    print("  • 'Resource temporarily unavailable'")
    print("  • 'Another git process seems to be running'")
    
    print("\nRetry configuration:")
    print(f"  • Retry count: {gateway.retry_count}")
    print(f"  • Retry delay: {gateway.retry_delay}s")
    print("  • Exponential backoff between retries")
    
    print("\n" + "─" * 70)
    print("🔟 WRITE OPERATIONS (Not executed in demo)")
    print("─" * 70)
    
    print("\nThese methods modify the repository and are not executed in the demo:")
    print("\n📍 Add files to staging:")
    print("   gateway.add(['file1.py', '*.txt'], cwd)")
    
    print("\n📍 Commit changes:")
    print("   gateway.commit('feat: add new feature', cwd)")
    print("   gateway.commit('fix: bug', cwd, amend=True, no_edit=True)")
    
    print("\n📍 Push changes:")
    print("   gateway.push(cwd)  # Push to origin/current-branch")
    print("   gateway.push(cwd, branch='main', force=True)")
    
    print("\n📍 Pull changes:")
    print("   gateway.pull(cwd)  # Pull from origin/current-branch")
    print("   gateway.pull(cwd, branch='main', rebase=True)")
    
    print("\n📍 Clone repository:")
    print("   gateway.clone('https://github.com/user/repo.git', '/path/to/dest')")
    print("   gateway.clone(url, dest, depth=1, timeout=300)")
    
    print("\n" + "─" * 70)
    print("1️⃣1️⃣ ADVANCED FEATURES")
    print("─" * 70)
    
    # Show timeout capability
    print("\n📍 Timeout support:")
    print("   gateway.clone(url, dest, timeout=300)  # 5 minute timeout")
    
    # Show environment variable support
    print("\n📍 Environment variables:")
    print("   gateway.run(['commit'], env={'GIT_AUTHOR_NAME': 'Bot'})")
    
    # Show input data support
    print("\n📍 Input data (for patches, etc):")
    print("   gateway.run(['apply', '-'], input_data=patch_content)")
    
    # Show Path object support
    print("\n📍 Path object support:")
    print("   gateway.status(Path.home() / 'projects' / 'repo')")
    
    print("\n" + "=" * 70)
    print("✅ GitGateway Demo Complete!")
    print("=" * 70)

if __name__ == '__main__':
    main()
EOF

# Run the Python demo
echo "Running GitGateway demonstration..."
echo
python3 /tmp/git_gateway_demo.py

# Cleanup
rm -f /tmp/git_gateway_demo.py

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Key Takeaways"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "• GitGateway provides a unified interface for all Git operations"
echo "• Automatic retry logic handles transient failures gracefully"
echo "• Convenience methods simplify common Git tasks"
echo "• Robust error handling with detailed error information"
echo "• Full control over subprocess execution (timeouts, env vars, etc)"
echo
echo "GitGateway is the foundation for reliable Git automation in Loom!"