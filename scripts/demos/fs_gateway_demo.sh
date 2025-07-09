#!/bin/bash
# Demo script for FSGateway - safe file operations with permission handling

set -e

echo "=== 📁 Loom FSGateway Demo ==="
echo "Demonstrating safe file system operations with permission controls"
echo

# Check if we're in the loom directory
if [ ! -f "loom.py" ]; then
    echo "Error: Please run this demo from the loom directory"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ KILLER FEATURE: Never accidentally modify files outside your project!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Python code:"
echo "  fs = FSGateway(allowed_paths=['/safe/project/dir'])"
echo "  fs.write_text('/etc/passwd', 'pwned')  # FSPermissionError!"
echo "  fs.write_text('config.json', data)     # ✓ Safe!"
echo
echo "✨ Atomic writes prevent corruption"
echo "✨ Path validation prevents escaping sandboxes"
echo "✨ Read-only mode for audit operations"
echo "✨ Never lose data to incomplete writes again"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📁 FSGateway Overview"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FSGateway provides:"
echo "  • Safe file operations with path validation"
echo "  • Atomic writes to prevent corruption"
echo "  • Permission-based access control"
echo "  • JSON and binary file support"
echo "  • File metadata and hash operations"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Demonstrating All FSGateway Features"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Create a Python script to demonstrate FSGateway
cat > /tmp/fs_gateway_demo.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
import tempfile
import json
sys.path.insert(0, os.getcwd())

from src.infra.fs_gateway import FSGateway, FSPermissionError
from pathlib import Path

def print_section(title):
    """Print a section header."""
    print(f"\n{'─' * 70}")
    print(f"{title}")
    print('─' * 70)

def print_result(operation, success=True, result=None, error=None):
    """Print operation result."""
    status = "✅" if success else "❌"
    print(f"{status} {operation}")
    if result is not None:
        print(f"   → {result}")
    if error:
        print(f"   → Error: {error}")

def main():
    # Create a temporary working directory for the demo
    with tempfile.TemporaryDirectory(prefix='fsgateway_demo_') as temp_dir:
        temp_path = Path(temp_dir)
        print(f"Demo workspace: {temp_path}")
        
        print_section("1️⃣ BASIC FILE OPERATIONS")
        
        # Initialize FSGateway
        fs = FSGateway()
        print("Initialized FSGateway with default settings")
        
        # Write text file
        demo_file = temp_path / 'demo.txt'
        fs.write_text(demo_file, 'Hello, FSGateway!')
        print_result("write_text", result=f"Wrote to {demo_file.name}")
        
        # Read text file
        content = fs.read_text(demo_file)
        print_result("read_text", result=f"Read: '{content}'")
        
        # Check file exists
        exists = fs.exists(demo_file)
        print_result("exists", result=f"File exists: {exists}")
        
        print_section("2️⃣ ATOMIC OPERATIONS")
        
        # Demonstrate atomic vs non-atomic writes
        atomic_file = temp_path / 'atomic.txt'
        
        # Atomic write (default)
        fs.write_text(atomic_file, 'Atomic write prevents corruption!', atomic=True)
        print_result("atomic write", result="Safe write completed")
        
        # Write JSON atomically
        json_file = temp_path / 'config.json'
        config_data = {
            'version': '1.0',
            'features': ['atomic_writes', 'permission_control'],
            'settings': {'debug': True, 'max_size': 1024}
        }
        fs.write_json(json_file, config_data)
        print_result("write_json", result="JSON config written atomically")
        
        # Read JSON back
        loaded_config = fs.read_json(json_file)
        print_result("read_json", result=f"Loaded {len(loaded_config)} keys")
        
        print_section("3️⃣ DIRECTORY OPERATIONS")
        
        # Create directory structure
        nested_dir = temp_path / 'nested' / 'deep' / 'structure'
        fs.mkdir(nested_dir, parents=True)
        print_result("mkdir", result=f"Created {nested_dir.relative_to(temp_path)}")
        
        # List directory contents
        contents = fs.list_dir(temp_path)
        file_names = [p.name for p in contents]
        print_result("list_dir", result=f"Found: {', '.join(file_names)}")
        
        # List with pattern
        txt_files = fs.list_dir(temp_path, pattern='*.txt')
        txt_names = [p.name for p in txt_files]
        print_result("list_dir with pattern", result=f"*.txt files: {', '.join(txt_names)}")
        
        print_section("4️⃣ FILE METADATA AND HASHING")
        
        # Get file metadata
        metadata = fs.get_metadata(demo_file)
        print_result("get_metadata", result=f"Size: {metadata['size']} bytes, Mode: {metadata['permissions']}")
        
        # Compute file hash
        hash_value = fs.compute_hash(demo_file)
        print_result("compute_hash", result=f"SHA256: {hash_value[:16]}...")
        
        # Get file size
        size = fs.get_size(demo_file)
        print_result("get_size", result=f"{size} bytes")
        
        print_section("5️⃣ PERMISSION CONTROL")
        
        # Create restricted FSGateway
        allowed_subdir = temp_path / 'allowed'
        fs.mkdir(allowed_subdir)
        
        restricted_fs = FSGateway(allowed_paths=[allowed_subdir])
        print("Created FSGateway restricted to 'allowed' directory")
        
        # Allowed operation
        allowed_file = allowed_subdir / 'allowed.txt'
        restricted_fs.write_text(allowed_file, 'This is allowed!')
        print_result("restricted write (allowed)", result="Write succeeded")
        
        # Denied operation
        try:
            forbidden_file = temp_path / 'forbidden.txt'
            restricted_fs.write_text(forbidden_file, 'This should fail!')
            print_result("restricted write (forbidden)", success=False, error="Should have failed!")
        except FSPermissionError as e:
            print_result("restricted write (forbidden)", success=True, result="Correctly blocked")
        
        print_section("6️⃣ READ-ONLY MODE")
        
        # Create read-only FSGateway
        readonly_fs = FSGateway(read_only=True)
        print("Created read-only FSGateway")
        
        # Read operation should work
        content = readonly_fs.read_text(demo_file)
        print_result("readonly read", result=f"Read {len(content)} characters")
        
        # Write operation should fail
        try:
            readonly_fs.write_text(temp_path / 'readonly_test.txt', 'Should fail!')
            print_result("readonly write", success=False, error="Should have failed!")
        except FSPermissionError:
            print_result("readonly write", success=True, result="Correctly blocked write")
        
        print_section("7️⃣ ADVANCED FILE OPERATIONS")
        
        # Copy file
        source_file = temp_path / 'source.txt'
        dest_file = temp_path / 'destination.txt'
        fs.write_text(source_file, 'Copy me!')
        fs.copy(source_file, dest_file)
        print_result("copy", result=f"Copied {source_file.name} → {dest_file.name}")
        
        # Move file
        new_name = temp_path / 'moved.txt'
        fs.move(dest_file, new_name)
        print_result("move", result=f"Moved to {new_name.name}")
        
        # Binary operations
        binary_file = temp_path / 'binary.dat'
        binary_data = b'\x00\x01\x02\x03Hello\xff\xfe'
        fs.write_bytes(binary_file, binary_data)
        read_binary = fs.read_bytes(binary_file)
        print_result("binary operations", result=f"Wrote/read {len(binary_data)} bytes")
        
        print_section("8️⃣ UTILITY OPERATIONS")
        
        # Ensure parent directory
        deep_file = temp_path / 'very' / 'deep' / 'path' / 'file.txt'
        fs.ensure_parent_dir(deep_file)
        print_result("ensure_parent_dir", result=f"Created parents for {deep_file.name}")
        
        # Walk directory tree
        walk_count = 0
        for root, dirs, files in fs.walk(temp_path):
            walk_count += 1
        print_result("walk", result=f"Walked {walk_count} directories")
        
        # Temporary directory
        with fs.temp_dir(prefix='demo_temp_') as tmpdir:
            temp_test = Path(tmpdir) / 'temp_test.txt'
            fs.write_text(temp_test, 'Temporary file')
            print_result("temp_dir", result=f"Created temp dir with test file")
        # temp dir is automatically cleaned up
        
        print_section("9️⃣ ERROR HANDLING")
        
        # Try to read non-existent file
        try:
            fs.read_text(temp_path / 'nonexistent.txt')
            print_result("read nonexistent", success=False)
        except FileNotFoundError:
            print_result("read nonexistent", result="Correctly raised FileNotFoundError")
        
        # Try to delete directory with delete()
        try:
            fs.delete(temp_path)
            print_result("delete directory", success=False)
        except IsADirectoryError:
            print_result("delete directory", result="Correctly raised IsADirectoryError")
        
        print_section("🔟 CLEANUP")
        
        # Clean up demo files
        files_to_delete = [demo_file, atomic_file, json_file, source_file, new_name, binary_file]
        for file in files_to_delete:
            if fs.exists(file):
                fs.delete(file, missing_ok=True)
        
        print_result("cleanup", result=f"Cleaned up demo files")
        
        print(f"\n{'=' * 70}")
        print("✅ FSGateway Demo Complete!")
        print('=' * 70)
        print("\nFSGateway provides secure, reliable file operations with:")
        print("• Atomic writes to prevent data corruption")
        print("• Path validation for security")
        print("• Permission controls and read-only mode")
        print("• Comprehensive file operations")
        print("• JSON and binary file support")
        print("• Advanced features like hashing and metadata")
        print("\nPerfect for secure automation and data processing!")

if __name__ == '__main__':
    main()
EOF

# Run the Python demo
echo "Running FSGateway demonstration..."
echo
python3 /tmp/fs_gateway_demo.py

# Cleanup
rm -f /tmp/fs_gateway_demo.py

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Key Takeaways"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "• FSGateway prevents accidental writes outside allowed directories"
echo "• Atomic operations ensure data integrity during writes"
echo "• Read-only mode enables safe audit and analysis operations"
echo "• Comprehensive error handling with specific exception types"
echo "• High-level operations like JSON handling and directory walking"
echo
echo "FSGateway is the foundation for secure file operations in Loom!"