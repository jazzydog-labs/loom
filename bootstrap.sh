#!/bin/bash

# Loom bootstrap script
# This script sets up loom and runs foundry-bootstrap

set -e

echo "🧵 Loom - Foundry Ecosystem Bootstrap"
echo "======================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if already bootstrapped
if [ -f ".loomrc" ]; then
    if grep -q "bootstrap-succeeded: true" .loomrc; then
        echo "✅ Already bootstrapped, skipping bootstrap step"
        BOOTSTRAP_COMPLETED=true
    else
        BOOTSTRAP_COMPLETED=false
    fi
else
    BOOTSTRAP_COMPLETED=false
fi

if [ "$BOOTSTRAP_COMPLETED" = false ]; then
    echo "🎯 Setting up foundry-bootstrap..."
    
    # Create tmp directory and clone foundry-bootstrap
    TMP_DIR="./tmp"
    mkdir -p "$TMP_DIR"
    cd "$TMP_DIR"
    
    if [ ! -d "foundry-bootstrap" ]; then
        echo "📥 Cloning foundry-bootstrap..."
        git clone https://github.com/jazzydog-labs/foundry-bootstrap.git
    fi
    
    cd foundry-bootstrap
    
    if [ -f "bootstrap.sh" ]; then
        echo "🔧 Running foundry-bootstrap.sh..."
        chmod +x bootstrap.sh
        ./bootstrap.sh
        BOOTSTRAP_EXIT_CODE=$?
        cd "$SCRIPT_DIR"
        if [ $BOOTSTRAP_EXIT_CODE -eq 0 ]; then
            echo "✅ Bootstrap completed successfully"
            # Write bootstrap success to .loomrc
            if [ -f ".loomrc" ]; then
                echo "bootstrap-succeeded: true" >> .loomrc
            else
                echo "bootstrap-succeeded: true" > .loomrc
            fi
        else
            echo "❌ foundry-bootstrap failed (exit code $BOOTSTRAP_EXIT_CODE). Not marking as succeeded."
            rm -rf "$TMP_DIR"
            exit 1
        fi
    else
        echo "❌ bootstrap.sh not found in foundry-bootstrap"
        cd "$SCRIPT_DIR"
        rm -rf "$TMP_DIR"
        exit 1
    fi
    
    # Clean up tmp directory
    cd "$SCRIPT_DIR"
    rm -rf "$TMP_DIR"
    echo "🧹 Cleaned up temporary files"
fi

# Create loom shim in ~/.local/bin
echo "🔗 Creating loom shim..."
mkdir -p ~/.local/bin

# Create the shim script
cat > ~/.local/bin/loom << 'EOF'
#!/bin/bash

# Loom shim - dispatches to the actual loom.py script
# This allows running 'loom' from anywhere

# Try to find loom.py in common locations
LOOM_PY=""

# First, try the current directory (if we're in a loom repo)
if [ -f "./loom.py" ]; then
    LOOM_PY="./loom.py"
# Then try ~/dev/jazzydog-labs/foundry/loom/loom.py (typical location)
elif [ -f "$HOME/dev/jazzydog-labs/foundry/loom/loom.py" ]; then
    LOOM_PY="$HOME/dev/jazzydog-labs/foundry/loom/loom.py"
# Then try to find it in PATH or common locations
else
    # Look for loom.py in common development directories
    for dir in "$HOME/dev" "$HOME/Development" "$HOME/projects" "$HOME/code"; do
        if [ -d "$dir" ]; then
            found=$(find "$dir" -name "loom.py" -type f 2>/dev/null | head -1)
            if [ -n "$found" ]; then
                LOOM_PY="$found"
                break
            fi
        fi
    done
fi

# If we still can't find it, try to find it in any subdirectory of common paths
if [ -z "$LOOM_PY" ]; then
    for dir in "$HOME/dev" "$HOME/Development" "$HOME/projects" "$HOME/code"; do
        if [ -d "$dir" ]; then
            found=$(find "$dir" -path "*/loom/loom.py" -type f 2>/dev/null | head -1)
            if [ -n "$found" ]; then
                LOOM_PY="$found"
                break
            fi
        fi
    done
fi

# If we found loom.py, execute it with all arguments
if [ -n "$LOOM_PY" ]; then
    # Change to the directory containing loom.py to ensure relative paths work
    cd "$(dirname "$LOOM_PY")"
    exec "$LOOM_PY" "$@"
else
    echo "❌ Error: Could not find loom.py"
    echo "Please ensure loom is installed and loom.py is accessible."
    echo "Common locations:"
    echo "  - ~/dev/jazzydog-labs/foundry/loom/loom.py"
    echo "  - Current directory (./loom.py)"
    echo "  - Any subdirectory named 'loom' containing loom.py"
    exit 1
fi
EOF

chmod +x ~/.local/bin/loom
echo "✅ Loom shim created at ~/.local/bin/loom"

# Now run loom init (we have Python and are bootstrapped)
echo "🚀 Running loom init..."
if command -v python3 &> /dev/null; then
    ./loom.py init --no-bootstrap
else
    echo "❌ Python 3 not found after bootstrap"
    exit 1
fi

echo ""
echo "✨ Loom bootstrap completed!"
echo "You can now use loom commands:"
echo "  loom status  # Check repository status"
echo "  loom pull    # Pull latest changes"
echo "  loom exec -- ls -la  # Execute command in all repos"
echo ""
echo "Note: If 'loom' command is not found, you may need to add ~/.local/bin to your PATH:"
echo "  export PATH="\$HOME/.local/bin:\$PATH""
echo "  # Add this to your ~/.bashrc, ~/.zshrc, or ~/.profile"
