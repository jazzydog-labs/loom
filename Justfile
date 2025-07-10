# List all available recipes (default command)
default:
	@just --list

# Run tests
test:
	pytest -q

test-silent:
	@pytest --cov=src --cov-report=term-missing -q --tb=no --no-header 2>&1 | \
		awk '/passed|failed|error/ {test_line=$0} /TOTAL/ {total_line=$0} END {if (test_line && total_line) {split(total_line, arr, " "); printf "%s | Coverage: %s\n", test_line, arr[4]} else if (test_line) print test_line; else print "no test output"}'

# Run all demo scripts
demo:
	#!/usr/bin/env bash
	echo "🎭 Running all Loom demos..."
	echo
	
	# Run each demo script
	for demo in scripts/demos/*.sh; do
		if [ -x "$demo" ]; then
			echo "────────────────────────────────────────────────────────────────"
			echo "Running: $(basename "$demo")"
			echo "────────────────────────────────────────────────────────────────"
			"$demo"
			echo
		fi
	done
	
	echo "🎉 All demos complete!"

# Demo: Bulk command execution across multiple repositories
demo-bulk-exec:
	@echo "🚀 Running BulkExecSvc demo - Execute commands across multiple repos"
	@bash scripts/demos/bulk_exec_demo.sh

# Demo: Freeze snapshots for repository state management
demo-freeze:
	@echo "❄️ Running FreezeSvc demo - Create and restore repository snapshots"
	@bash scripts/demos/freeze_svc_demo.sh

# Demo: Robust Git command execution with retry logic
demo-git-gateway:
	@echo "🔧 Running GitGateway demo - Robust Git operations with retries"
	@bash scripts/demos/git_gateway_demo.sh

# Demo: Run just recipes across multiple repositories
demo-just:
	@echo "📦 Running Just command demo - Execute just recipes across repos"
	@bash scripts/demos/just_command_demo.sh

# Demo: Repository health monitoring and reporting
demo-health:
	@echo "🏥 Running Repository Health Check demo - Monitor repo status"
	@bash scripts/demos/repo_health_check.sh

# Demo: Coordinated stash management across repositories
demo-stash:
	@echo "📚 Running StashCoordinator demo - Manage stashes across repos"
	@bash scripts/demos/stash_coordinator_demo.sh

# Demo: Safe file operations with permission handling
demo-fs:
	@echo "📁 Running FSGateway demo - Safe file operations with permissions"
	@bash scripts/demos/fs_gateway_demo.sh

# Demo: Secure shell command execution with concurrency control
demo-shell:
	@echo "⚡ Running ShellGateway demo - Secure shell execution with concurrency"
	@bash scripts/demos/shell_gateway_demo.sh

# Demo: JSON Action Router for unified Loom interface
demo-json:
	@echo "🎯 Running JSON Action Router demo - Unified JSON interface"
	@bash scripts/demos/json_action_router_demo.sh
