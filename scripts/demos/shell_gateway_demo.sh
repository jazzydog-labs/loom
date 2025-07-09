#!/bin/bash
# Demo script for ShellGateway - secure shell command execution with concurrency control

set -e

echo "=== ⚡ Loom ShellGateway Demo ==="
echo "Demonstrating secure shell command execution with concurrency control"
echo

# Check if we're in the loom directory
if [ ! -f "loom.py" ]; then
    echo "Error: Please run this demo from the loom directory"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ KILLER FEATURE: Run shell commands safely with automatic security!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Python code:"
echo "  shell = ShellGateway(mode=ShellMode.SAFE)"
echo "  result = shell.execute('rm -rf /')  # ShellSecurityError!"
echo "  result = shell.execute('ls -la')    # ✓ Safe!"
echo
echo "✨ Automatic security validation prevents dangerous commands"
echo "✨ Concurrency control prevents resource exhaustion"
echo "✨ Timeout protection prevents hanging processes"
echo "✨ Pipeline support for complex operations"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ ShellGateway Overview"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ShellGateway provides:"
echo "  • Secure shell command execution with validation"
echo "  • Concurrency control to prevent resource exhaustion"
echo "  • Timeout management and process cleanup"
echo "  • Multiple execution modes (safe, restricted, permissive)"
echo "  • Pipeline support for complex operations"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Demonstrating All ShellGateway Features"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Create a Python script to demonstrate ShellGateway
cat > /tmp/shell_gateway_demo.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
import tempfile
import time
sys.path.insert(0, os.getcwd())

from src.infra.shell_gateway import (
    ShellGateway, ShellMode, ShellResult,
    ShellSecurityError, ShellTimeoutError, ShellPermissionError
)
from pathlib import Path

def print_section(title):
    """Print a section header."""
    print(f"\n{'─' * 70}")
    print(f"{title}")
    print('─' * 70)

def print_result(operation, result=None, error=None):
    """Print operation result."""
    if result and isinstance(result, ShellResult):
        status = "✅" if result.success else "❌"
        print(f"{status} {operation}")
        if result.stdout:
            output = result.stdout.strip()
            if output:
                # Show first line of output
                first_line = output.split('\n')[0]
                print(f"   → {first_line}")
        if result.stderr and not result.success:
            print(f"   → Error: {result.stderr.strip()}")
        print(f"   → Duration: {result.duration:.3f}s")
    elif error:
        print(f"❌ {operation}")
        print(f"   → Error: {error}")
    else:
        print(f"✅ {operation}")

def main():
    print_section("1️⃣ BASIC COMMAND EXECUTION")
    
    # Initialize ShellGateway
    shell = ShellGateway(max_concurrent=5, default_timeout=10.0)
    print("Initialized ShellGateway with max_concurrent=5, timeout=10s")
    
    # Execute basic commands
    result = shell.execute("echo 'Hello, ShellGateway!'")
    print_result("Basic command execution", result)
    
    result = shell.execute("pwd")
    print_result("Get current directory", result)
    
    result = shell.execute("date")
    print_result("Get current date", result)
    
    print_section("2️⃣ SECURITY VALIDATION")
    
    # Test security validation
    print("Testing security validation in safe mode...")
    
    # This should work (safe command)
    result = shell.execute("ls -la")
    print_result("Safe command (ls)", result)
    
    # This should fail (dangerous command)
    try:
        result = shell.execute("rm -rf /tmp/test")
        print_result("Dangerous command (rm)", result)
    except ShellSecurityError as e:
        print_result("Dangerous command (rm)", error=f"Blocked: {e}")
    
    # Test dangerous patterns
    try:
        result = shell.execute("echo $(whoami)")
        print_result("Dangerous pattern (command substitution)", result)
    except ShellSecurityError as e:
        print_result("Dangerous pattern (command substitution)", error=f"Blocked: {e}")
    
    print_section("3️⃣ EXECUTION MODES")
    
    # Safe mode
    safe_shell = ShellGateway(mode=ShellMode.SAFE)
    print("Safe mode: Only allows predefined safe commands")
    
    result = safe_shell.execute("echo safe")
    print_result("Safe mode - allowed command", result)
    
    try:
        result = safe_shell.execute("custom_command")
        print_result("Safe mode - unknown command", result)
    except ShellSecurityError as e:
        print_result("Safe mode - unknown command", error=f"Blocked: {e}")
    
    # Restricted mode
    restricted_shell = ShellGateway(mode=ShellMode.RESTRICTED)
    print("\nRestricted mode: Allows more commands but blocks dangerous patterns")
    
    result = restricted_shell.execute("echo restricted")
    print_result("Restricted mode - basic command", result)
    
    # Permissive mode  
    permissive_shell = ShellGateway(mode=ShellMode.PERMISSIVE)
    print("\nPermissive mode: Allows most commands with basic safety checks")
    
    result = permissive_shell.execute("echo permissive")
    print_result("Permissive mode - basic command", result)
    
    print_section("4️⃣ CONCURRENT EXECUTION")
    
    # Execute multiple commands concurrently
    commands = [
        "echo 'Command 1'",
        "echo 'Command 2'", 
        "echo 'Command 3'",
        "echo 'Command 4'"
    ]
    
    start_time = time.time()
    results = shell.execute_many(commands)
    duration = time.time() - start_time
    
    print(f"Executed {len(commands)} commands concurrently in {duration:.3f}s")
    for i, result in enumerate(results, 1):
        print_result(f"Concurrent command {i}", result)
    
    print_section("5️⃣ PIPELINE EXECUTION")
    
    # Execute pipeline
    pipeline_commands = [
        "echo 'hello world test'",
        "grep hello", 
        "wc -w"
    ]
    
    result = shell.execute_pipeline(pipeline_commands)
    print_result("Pipeline execution", result)
    
    print_section("6️⃣ TIMEOUT HANDLING")
    
    # Test timeout
    print("Testing timeout handling...")
    
    try:
        result = shell.execute("sleep 5", timeout=0.1, check_security=False)
        print_result("Timeout test", result)
    except ShellTimeoutError as e:
        print_result("Timeout test", error=f"Timed out: {e}")
    
    print_section("7️⃣ WORKING DIRECTORY CONTROL")
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test file
        test_file = temp_path / 'test.txt'
        test_file.write_text('Hello from temp directory!')
        
        # Execute command in specific directory
        result = shell.execute("ls -la", cwd=temp_dir)
        print_result("Command in specific directory", result)
        
        result = shell.execute("cat test.txt", cwd=temp_dir)
        print_result("Read file in directory", result)
    
    print_section("8️⃣ ENVIRONMENT VARIABLES")
    
    # Execute with custom environment
    result = shell.execute("echo $CUSTOM_VAR", env={'CUSTOM_VAR': 'custom_value'})
    print_result("Command with environment variable", result)
    
    print_section("9️⃣ INPUT DATA")
    
    # Execute with input data
    result = shell.execute("cat", input_data="Hello from input!")
    print_result("Command with input data", result)
    
    print_section("🔟 CONVENIENCE METHODS")
    
    # Test convenience methods
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        (temp_path / 'file1.txt').write_text('content1')
        (temp_path / 'file2.txt').write_text('content2')
        
        # ls convenience method
        result = shell.ls(temp_path)
        print_result("ls convenience method", result)
        
        # cat convenience method
        result = shell.cat(temp_path / 'file1.txt')
        print_result("cat convenience method", result)
        
        # grep convenience method
        result = shell.grep('content1', temp_path / 'file1.txt')
        print_result("grep convenience method", result)
        
        # find convenience method
        result = shell.find(temp_path, '*.txt')
        print_result("find convenience method", result)
    
    print_section("1️⃣1️⃣ PATH RESTRICTIONS")
    
    # Test path restrictions
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        allowed_dir = temp_path / 'allowed'
        allowed_dir.mkdir()
        
        # Create restricted shell
        restricted_shell = ShellGateway(allowed_paths=[allowed_dir])
        
        # This should work
        result = restricted_shell.execute("pwd", cwd=allowed_dir)
        print_result("Restricted path - allowed directory", result)
        
        # This should fail
        try:
            result = restricted_shell.execute("pwd", cwd=temp_path)
            print_result("Restricted path - forbidden directory", result)
        except ShellPermissionError as e:
            print_result("Restricted path - forbidden directory", error=f"Blocked: {e}")
    
    print_section("1️⃣2️⃣ PROCESS MANAGEMENT")
    
    # Show process management
    print(f"Active processes: {shell.get_active_count()}")
    
    # Kill all processes (should be 0 since commands finish quickly)
    killed = shell.kill_all()
    print(f"Killed {killed} processes")
    
    print_section("1️⃣3️⃣ CONTEXT MANAGER")
    
    # Demonstrate context manager usage
    with ShellGateway(max_concurrent=3) as ctx_shell:
        result = ctx_shell.execute("echo 'Context manager test'")
        print_result("Context manager usage", result)
    
    print("Context manager automatically cleaned up resources")
    
    print_section("1️⃣4️⃣ ADVANCED FEATURES")
    
    # Custom command lists
    custom_shell = ShellGateway(
        allowed_commands=['custom_tool'],
        blocked_commands=['python']
    )
    
    print("Custom shell with allowed_commands=['custom_tool'] and blocked_commands=['python']")
    
    # Test blocked command
    try:
        result = custom_shell.execute("python --version")
        print_result("Blocked command test", result)
    except ShellSecurityError as e:
        print_result("Blocked command test", error=f"Blocked: {e}")
    
    # Cleanup
    shell.shutdown()
    
    print(f"\n{'=' * 70}")
    print("✅ ShellGateway Demo Complete!")
    print('=' * 70)
    print("\nShellGateway provides secure, controlled shell execution with:")
    print("• Automatic security validation prevents dangerous commands")
    print("• Concurrency control prevents resource exhaustion")
    print("• Timeout protection prevents hanging processes")
    print("• Multiple execution modes for different security levels")
    print("• Pipeline support for complex operations")
    print("• Path restrictions for sandboxed execution")
    print("• Process management and cleanup")
    print("\nPerfect for secure automation and CI/CD pipelines!")

if __name__ == '__main__':
    main()
EOF

# Run the Python demo
echo "Running ShellGateway demonstration..."
echo
python3 /tmp/shell_gateway_demo.py

# Cleanup
rm -f /tmp/shell_gateway_demo.py

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Key Takeaways"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "• ShellGateway prevents execution of dangerous commands automatically"
echo "• Concurrency control prevents system resource exhaustion"
echo "• Timeout protection prevents hanging processes"
echo "• Multiple security modes for different environments"
echo "• Pipeline support enables complex command chains"
echo "• Path restrictions provide sandboxed execution"
echo
echo "ShellGateway is the secure foundation for shell operations in Loom!"