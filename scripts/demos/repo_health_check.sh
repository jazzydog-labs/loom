#!/bin/bash
# Demo script for repository health checks using BulkExecSvc

set -e

echo "=== 🏥 Repository Health Check Demo ==="
echo "Analyzing repository health metrics across the foundry"
echo

# Check if we're in the loom directory
if [ ! -f "loom.py" ]; then
    echo "Error: Please run this demo from the loom directory"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ KILLER FEATURE: Instant health check across all repos!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Command:"
echo "  loom exec '<health-check-command>' --workers 8"
echo
echo "✨ Security scanning across all repos"
echo "✨ Code quality metrics in seconds"
echo "✨ Dependency analysis at scale"
echo "✨ Identify issues before they become problems"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔒 Security: Checking for exposed secrets patterns"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 loom.py exec 'grep -r "password\|secret\|api_key\|token" --include="*.py" --include="*.js" --include="*.env*" . 2>/dev/null | grep -v ".git" | wc -l | xargs -I {} echo "{} potential secret references"' --workers 4

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Code Quality: Large files check (>500 lines)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 loom.py exec 'find . -name "*.py" -type f -exec wc -l {} \; 2>/dev/null | awk "\$1 > 500" | wc -l | xargs -I {} echo "{} files over 500 lines"'

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 Testing: Test file presence"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 loom.py exec 'test -d tests && echo "✓ Has tests directory" || test -d test && echo "✓ Has test directory" || echo "⚠️  No test directory found"'

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Dependencies: Package files check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 loom.py exec 'ls -1 | grep -E "requirements|package|Cargo.toml|go.mod|pom.xml|build.gradle|pyproject.toml" | tr "\n" ", " | sed "s/,$//" | xargs -I {} echo "Found: {}"' --no-summary

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 Documentation: Core docs presence"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 loom.py exec 'echo -n "Docs: "; ls -1 | grep -E "README|LICENSE|CONTRIBUTING|CHANGELOG" | wc -l | xargs -I {} echo "{} core files"' --no-summary

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚨 Git: Uncommitted changes check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 loom.py exec 'git status --porcelain 2>/dev/null | wc -l | xargs -I {} test {} -eq 0 && echo "✓ Clean working tree" || echo "⚠️  {} uncommitted changes"'

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏷️  Git: Remote tracking status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 loom.py exec 'git remote -v 2>/dev/null | grep -q "origin" && echo "✓ Has origin remote" || echo "✗ No origin remote"'

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📏 Repository Age (days since first commit)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 loom.py exec 'git log --reverse --format="%at" 2>/dev/null | head -1 | xargs -I {} test -n {} && echo $(( ($(date +%s) - {}) / 86400 )) "days old" || echo "No commits yet"' --no-summary

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Health Check Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "This health check demo showcases:"
echo "• Security scanning for potential exposed secrets"
echo "• Code quality metrics (file sizes)"
echo "• Test infrastructure presence"
echo "• Dependency management files"
echo "• Documentation completeness"
echo "• Git repository health"
echo
echo "Use these checks to maintain consistent standards across all repositories!"