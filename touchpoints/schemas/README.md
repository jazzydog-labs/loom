# Loom Schemas

This directory contains JSON schemas for standardization across repositories.

## Available Schemas

### base.schema.json
Base schema for all Loom JSON actions. Defines the common structure with action, version, payload, and metadata fields.

### freeze.schema.json
Schema for freeze-related actions (create, restore, list, delete).

### test-output.schema.json
**Standardized test output schema for use across all repositories.**

The test output schema provides a consistent format for test results, making it easy to:
- Compare test results across different repositories
- Track test metrics over time
- Integrate with CI/CD pipelines
- Generate test reports and dashboards

## Using the Test Output Schema

### In Your Repository

1. Copy the `test-output.schema.json` to your repository's schema directory
2. Create a test runner script that outputs JSON following this schema
3. Add a `test-json` recipe to your justfile:

```makefile
# Run tests and output results as JSON
test-json:
    @python scripts/test_json_runner.py
```

### Example Output

```json
{
  "success": true,
  "summary": {
    "total": 100,
    "passed": 98,
    "failed": 2,
    "skipped": 0,
    "errors": 0
  },
  "coverage": {
    "percentage": 95.5,
    "lines": {
      "covered": 1200,
      "total": 1256,
      "missing": 56
    }
  },
  "duration": 12.5,
  "timestamp": "2024-01-09T10:30:00Z",
  "environment": {
    "python_version": "3.11.0",
    "platform": "Linux",
    "runner": "pytest",
    "ci": true,
    "ci_provider": "GitHub Actions"
  }
}
```

### Integration Examples

#### CI/CD Pipeline
```yaml
- name: Run Tests
  run: just test-json > test-results.json
  
- name: Check Test Success
  run: |
    if ! jq -e '.success' test-results.json; then
      echo "Tests failed!"
      exit 1
    fi
```

#### Monitoring Dashboard
```python
import json
import requests

# Collect test results from multiple repos
results = []
for repo in repositories:
    response = requests.get(f"{repo}/test-results.json")
    results.append(json.loads(response.text))

# Generate metrics
total_tests = sum(r["summary"]["total"] for r in results)
average_coverage = sum(r["coverage"]["percentage"] for r in results) / len(results)
```

## Schema Validation

To validate your test output against the schema:

```python
import json
import jsonschema

# Load schema and output
with open("test-output.schema.json") as f:
    schema = json.load(f)
    
with open("test-results.json") as f:
    output = json.load(f)

# Validate
jsonschema.validate(output, schema)
```

## Benefits

- **Consistency**: Same format across all repositories
- **Automation**: Easy to parse and process programmatically
- **Visibility**: Clear view of test health and coverage
- **Integration**: Works with any test runner that can output JSON
- **Evolution**: Schema versioning allows gradual improvements