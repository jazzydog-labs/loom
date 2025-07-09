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
