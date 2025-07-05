#!/usr/bin/env python3
"""Loom - The central orchestrator for the foundry ecosystem."""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import and run the main application
from main import main

if __name__ == "__main__":
    main() 