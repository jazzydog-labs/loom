#!/usr/bin/env python3
"""Test script to verify loom setup."""

import sys
from pathlib import Path

# Add the loomlib directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "loomlib"))

def test_imports():
    """Test that all modules can be imported."""
    try:
        from config import ConfigManager
        from git import GitManager
        from repo_manager import RepoManager
        print("✅ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test configuration loading."""
    try:
        from config import ConfigManager
        config = ConfigManager()
        
        # Test loading defaults
        defaults = config.load_defaults()
        print(f"✅ Defaults loaded: {len(defaults)} keys")
        
        # Test loading repos
        repos = config.load_repos()
        print(f"✅ Repos loaded: {len(repos.get('repos', []))} repositories")
        
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_git():
    """Test git operations."""
    try:
        from git import GitManager
        git = GitManager()
        
        # Test git availability
        import subprocess
        result = subprocess.run(['git', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Git available: {result.stdout.strip()}")
        else:
            print("❌ Git not available")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Git test failed: {e}")
        return False

def test_repo_manager():
    """Test repository manager."""
    try:
        from config import ConfigManager
        from git import GitManager
        from repo_manager import RepoManager
        
        config = ConfigManager()
        git = GitManager()
        repo_manager = RepoManager(config, git)
        
        print("✅ RepoManager initialized successfully")
        return True
    except Exception as e:
        print(f"❌ RepoManager test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧵 Testing Loom Setup")
    print("=" * 30)
    
    tests = [
        ("Module Imports", test_imports),
        ("Configuration", test_config),
        ("Git Operations", test_git),
        ("Repository Manager", test_repo_manager),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Loom is ready to use.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the setup.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 