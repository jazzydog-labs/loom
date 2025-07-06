#!/usr/bin/env python3
"""Test runner for the loom project."""

import sys
import unittest
from pathlib import Path

def run_tests():
    """Run all tests in the project."""
    # Add the src directory to the path
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path))
    
    # Also add the project root to the path for imports
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = str(Path(__file__).parent / "tests")
    suite = loader.discover(start_dir, pattern="test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    print("🧪 Running Loom Tests")
    print("=" * 50)
    
    success = run_tests()
    sys.exit(0 if success else 1) 