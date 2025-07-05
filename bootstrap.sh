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

# Now run loom init (we have Python and are bootstrapped)
echo "🚀 Running loom init..."
if command -v python3 &> /dev/null; then
    ./loom.py init --no-bootstrap
else
    echo "❌ Python 3 not found after bootstrap"
    exit 1
fi

echo ""
echo "🎉 Loom bootstrap completed!"
echo "You can now use loom commands:"
echo "  ./loom.py status  # Check repository status"
echo "  ./loom.py pull    # Pull latest changes"
echo "  ./loom.py exec -- ls -la  # Execute command in all repos" 