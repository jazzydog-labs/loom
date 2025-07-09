test:
	pytest -q

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
