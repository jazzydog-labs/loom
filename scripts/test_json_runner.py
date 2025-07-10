#!/usr/bin/env python3
"""Run pytest and output results as JSON following the test-output schema."""
import json
import sys
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Dict, Any, List, Optional

try:
    import pytest
    HAS_PYTEST = True
    PYTEST_VERSION = pytest.__version__
except ImportError:
    HAS_PYTEST = False
    PYTEST_VERSION = "unknown"


def get_git_info() -> Dict[str, Any]:
    """Get current git repository information."""
    repo_info = {}
    
    try:
        # Get current commit
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        repo_info["commit"] = result.stdout.strip()
        
        # Get current branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True
        )
        repo_info["branch"] = result.stdout.strip()
        
        # Check if dirty
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        repo_info["dirty"] = bool(result.stdout.strip())
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Git not available or not a git repo
        pass
    
    # Get repo name from current directory
    repo_info["name"] = Path.cwd().name
    repo_info["path"] = str(Path.cwd())
    
    return repo_info


def parse_pytest_json(pytest_output: Dict[str, Any]) -> Dict[str, Any]:
    """Parse pytest JSON output and convert to our schema."""
    # Start with basic structure
    result = {
        "success": pytest_output.get("exitcode", 1) == 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration": pytest_output.get("duration", 0.0),
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.system(),
            "runner": "pytest",
            "runner_version": PYTEST_VERSION,
            "ci": os.environ.get("CI", "false").lower() == "true",
        },
        "repository": get_git_info(),
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0
        },
        "failures": [],
        "errors": [],
        "skipped": [],
        "warnings": [],
        "metadata": {
            "config_file": "pytest.ini",
            "test_paths": ["tests/"],
            "plugins": []
        }
    }
    
    # Add CI provider if in CI
    if result["environment"]["ci"]:
        ci_provider = (
            os.environ.get("GITHUB_ACTIONS", "") and "GitHub Actions" or
            os.environ.get("TRAVIS", "") and "Travis CI" or
            os.environ.get("CIRCLECI", "") and "CircleCI" or
            os.environ.get("GITLAB_CI", "") and "GitLab CI" or
            "unknown"
        )
        if ci_provider != "unknown":
            result["environment"]["ci_provider"] = ci_provider
    
    # Parse test results from pytest
    if "tests" in pytest_output:
        for test in pytest_output["tests"]:
            result["summary"]["total"] += 1
            
            outcome = test.get("outcome", "")
            if outcome == "passed":
                result["summary"]["passed"] += 1
            elif outcome == "failed":
                result["summary"]["failed"] += 1
                result["failures"].append(format_test_failure(test))
            elif outcome == "skipped":
                result["summary"]["skipped"] += 1
                result["skipped"].append(format_test_skip(test))
            elif outcome == "error":
                result["summary"]["errors"] += 1
                result["errors"].append(format_test_failure(test))
    
    # Parse warnings
    if "warnings" in pytest_output:
        for warning in pytest_output["warnings"]:
            result["warnings"].append(format_warning(warning))
    
    return result


def format_test_failure(test: Dict[str, Any]) -> Dict[str, Any]:
    """Format a test failure/error for output."""
    failure = {
        "test_id": test.get("nodeid", "unknown"),
        "message": "Test failed",
        "duration": test.get("duration", 0.0)
    }
    
    # Extract test name from nodeid
    if "nodeid" in test:
        parts = test["nodeid"].split("::")
        if len(parts) >= 2:
            failure["file"] = parts[0]
            failure["name"] = "::".join(parts[1:])
    
    # Get failure details
    if "call" in test and "longrepr" in test["call"]:
        longrepr = test["call"]["longrepr"]
        if isinstance(longrepr, str):
            failure["message"] = longrepr
            failure["traceback"] = longrepr
        elif isinstance(longrepr, dict):
            # Handle different pytest failure representations
            if "reprcrash" in longrepr:
                failure["message"] = longrepr["reprcrash"].get("message", "Test failed")
            if "reprtraceback" in longrepr:
                failure["traceback"] = str(longrepr["reprtraceback"])
    
    # Try to determine failure type
    if "AssertionError" in failure.get("message", ""):
        failure["type"] = "assertion"
    elif "Error" in failure.get("message", ""):
        failure["type"] = "error"
    else:
        failure["type"] = "failure"
    
    return failure


def format_test_skip(test: Dict[str, Any]) -> Dict[str, Any]:
    """Format a skipped test for output."""
    skip = {
        "test_id": test.get("nodeid", "unknown"),
        "reason": "Skipped"
    }
    
    # Extract test name
    if "nodeid" in test:
        parts = test["nodeid"].split("::")
        if len(parts) >= 2:
            skip["name"] = "::".join(parts[1:])
    
    # Get skip reason
    if "setup" in test and "longrepr" in test["setup"]:
        longrepr = test["setup"]["longrepr"]
        if isinstance(longrepr, tuple) and len(longrepr) >= 3:
            skip["reason"] = longrepr[2]
        elif isinstance(longrepr, str):
            skip["reason"] = longrepr
    
    return skip


def format_warning(warning: Dict[str, Any]) -> Dict[str, Any]:
    """Format a warning for output."""
    return {
        "category": warning.get("category", "Warning"),
        "message": warning.get("message", ""),
        "file": warning.get("filename", ""),
        "line": warning.get("lineno", 0)
    }


def run_pytest_json() -> Dict[str, Any]:
    """Run pytest with JSON output."""
    # Create a temporary file for JSON output
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json_output_file = f.name
    
    try:
        # Run pytest with JSON output
        cmd = [
            sys.executable, "-m", "pytest",
            "--json-report",
            f"--json-report-file={json_output_file}",
            "--json-report-omit=collectors",
            "-q"
        ]
        
        # Add coverage if pytest-cov is available
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            text=True
        )
        if "pytest-cov" in result.stdout:
            cmd.extend(["--cov=src", "--cov-report=json"])
        
        # Run tests
        subprocess.run(cmd, capture_output=True)
        
        # Read JSON output
        with open(json_output_file, 'r') as f:
            pytest_data = json.load(f)
        
        # Convert to our schema
        output = parse_pytest_json(pytest_data)
        
        # Add coverage if available
        if os.path.exists("coverage.json"):
            with open("coverage.json", 'r') as f:
                coverage_data = json.load(f)
                output["coverage"] = parse_coverage(coverage_data)
        
        return output
        
    finally:
        # Cleanup
        if os.path.exists(json_output_file):
            os.unlink(json_output_file)
        if os.path.exists("coverage.json"):
            os.unlink("coverage.json")


def parse_coverage(coverage_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse coverage.py JSON output."""
    coverage = {
        "percentage": coverage_data.get("totals", {}).get("percent_covered", 0),
        "lines": {
            "covered": coverage_data.get("totals", {}).get("covered_lines", 0),
            "total": coverage_data.get("totals", {}).get("num_statements", 0),
            "missing": coverage_data.get("totals", {}).get("missing_lines", 0)
        }
    }
    
    # Add file-level coverage
    coverage["files"] = []
    for file_path, file_data in coverage_data.get("files", {}).items():
        coverage["files"].append({
            "path": file_path,
            "percentage": file_data.get("summary", {}).get("percent_covered", 0),
            "lines_covered": file_data.get("summary", {}).get("covered_lines", 0),
            "lines_total": file_data.get("summary", {}).get("num_statements", 0)
        })
    
    return coverage


def run_pytest_simple() -> Dict[str, Any]:
    """Run pytest without JSON plugin and parse output."""
    # This is a fallback for when pytest-json-report is not available
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    output = {
        "success": result.returncode == 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration": 0.0,  # Can't get accurate duration without JSON
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.system(),
            "runner": "pytest",
            "runner_version": PYTEST_VERSION,
            "ci": os.environ.get("CI", "false").lower() == "true",
        },
        "repository": get_git_info(),
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0
        },
        "failures": [],
        "errors": [],
        "skipped": [],
        "warnings": [],
        "metadata": {
            "config_file": "pytest.ini",
            "test_paths": ["tests/"],
            "plugins": []
        }
    }
    
    # Parse summary line (e.g., "===== 10 passed, 2 failed in 5.32s =====")
    summary_match = re.search(
        r'=+ ([\d\w\s,]+) in ([\d.]+)s =+',
        result.stdout
    )
    if summary_match:
        summary_text = summary_match.group(1)
        output["duration"] = float(summary_match.group(2))
        
        # Parse individual counts
        for match in re.finditer(r'(\d+) (\w+)', summary_text):
            count, status = int(match.group(1)), match.group(2)
            if status == "passed":
                output["summary"]["passed"] = count
            elif status == "failed":
                output["summary"]["failed"] = count
            elif status == "skipped":
                output["summary"]["skipped"] = count
            elif status in ["error", "errors"]:
                output["summary"]["errors"] = count
        
        output["summary"]["total"] = sum([
            output["summary"]["passed"],
            output["summary"]["failed"],
            output["summary"]["skipped"],
            output["summary"]["errors"]
        ])
    
    # Try to parse failures from output
    if output["summary"]["failed"] > 0:
        failure_sections = re.findall(
            r'FAILED ([\w/:.]+) - (.+?)(?=\n(?:FAILED|PASSED|=))',
            result.stdout,
            re.DOTALL
        )
        for test_id, message in failure_sections:
            output["failures"].append({
                "test_id": test_id,
                "message": message.strip(),
                "type": "assertion" if "AssertionError" in message else "error"
            })
    
    return output


def main():
    """Main entry point."""
    if not HAS_PYTEST:
        output = {
            "success": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration": 0.0,
            "environment": {
                "python_version": platform.python_version(),
                "platform": platform.system(),
                "runner": "none",
                "runner_version": "none",
                "ci": os.environ.get("CI", "false").lower() == "true",
            },
            "repository": get_git_info(),
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0
            },
            "failures": [{
                "test_id": "setup",
                "message": "pytest is not installed",
                "type": "error"
            }],
            "errors": [],
            "skipped": [],
            "warnings": [],
            "metadata": {}
        }
        print(json.dumps(output, indent=2))
        sys.exit(1)
    
    # Check if pytest-json-report is available
    result = subprocess.run(
        [sys.executable, "-m", "pip", "show", "pytest-json-report"],
        capture_output=True
    )
    
    if result.returncode == 0:
        output = run_pytest_json()
    else:
        output = run_pytest_simple()
    
    # Output JSON
    print(json.dumps(output, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if output["success"] else 1)


if __name__ == "__main__":
    main()