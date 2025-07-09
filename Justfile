test:
	pytest -q

# Run demo scripts
demo script="":
	#!/usr/bin/env bash
	if [ -z "{{script}}" ]; then
		echo "Available demos:"
		echo "  - bulk_exec: Demonstrate parallel command execution"
		echo ""
		echo "Usage: just demo <demo_name>"
		echo "Example: just demo bulk_exec"
	else
		case "{{script}}" in
			"bulk_exec")
				./scripts/demos/bulk_exec_demo.sh
				;;
			*)
				echo "Unknown demo: {{script}}"
				echo "Run 'just demo' to see available demos"
				exit 1
				;;
		esac
	fi
