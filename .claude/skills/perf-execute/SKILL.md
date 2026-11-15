---
name: perf-execute
description: Use when ready to generate Locust test files and execute load tests - renders templates based on service type, runs Locust with configured parameters, and monitors test execution. Triggers on "run load test", "execute performance test", "start Locust", or after /perf-prepare completes.
---

# Performance Test Execution

Generate Locust test files from templates and execute load tests with real-time monitoring.

## When to Use

- After `/perf-prepare` has created config.json
- User wants to run the performance test
- Ready to execute load testing
- Need to generate Locust test files

## Prerequisites

- Configuration file exists in `projects/` directory (from `/perf-prepare` or manually created)
- Locust is installed (`pip install locust`)
- Service is accessible at base_url
- Credentials are valid

## Project Selection Workflow

**IMPORTANT:** When user invokes `/perf-execute` without arguments or with unclear arguments:

1. **List Available Projects** from `projects/` directory
2. **Show project details** (service name, base URL)
3. **Ask user to select** which project to run
4. **Ask for duration** (default: 60 seconds)
5. **DO NOT run all projects** - only run the selected one

### Step 1: Discover Projects

```bash
# List all project configs
ls -1 projects/*.json

# For each project, extract metadata
for config in projects/*.json; do
    SERVICE_NAME=$(jq -r '.service_name' "$config")
    BASE_URL=$(jq -r '.base_url' "$config")
    echo "$(basename $config): $SERVICE_NAME ($BASE_URL)"
done
```

### Step 2: Present Options to User

Use AskUserQuestion to present available projects:

```
Question: "Which project would you like to test?"

Options:
1. bcas-add-in-config.json - BCAS Add-in API
2. orders-api-config.json - Orders API
3. payments-api-config.json - Payments API

Then ask:
"How long should the test run?"
- 1 minute (60s) [Default]
- 5 minutes (300s)
- 10 minutes (600s)
- Custom (specify seconds)
```

### Step 3: Execute Selected Project

```bash
./run_test.sh <selected-config>.json <duration>
```

**Example Flow:**

```
User: /perf-execute

Claude: Discovers 3 projects in projects/ folder, then asks:

"📁 Available Projects:
1. bcas-add-in-config.json - BCAS Add-in API (https://bcas-add-in.qa-ue2.bcas.cudaops.com)
2. orders-api-config.json - Orders API (https://orders-api.qa.example.com)
3. payments-api-config.json - Payments API (https://payments-api.qa.example.com)

Which project would you like to test?"

User: Select option 1 (bcas-add-in)

Claude: "How long should the test run?"

User: Select "5 minutes (300s)"

Claude: Runs ./run_test.sh bcas-add-in-config.json 300
```

### When Argument Provided

If user provides config name directly: `/perf-execute bcas-add-in-config.json`
- Skip project selection
- Ask for duration only (or use default 60s)
- Run immediately after confirmation

## Core Workflow

### 1. Project Discovery and Selection

**ALWAYS do this first unless user provided explicit config name:**

```bash
# Discover projects
PROJECTS=$(ls -1 projects/*.json 2>/dev/null)

if [ -z "$PROJECTS" ]; then
    echo "❌ No projects found in projects/ folder"
    echo "Add a config file to projects/ first"
    exit 1
fi

# Build project list with metadata
for config in projects/*.json; do
    NAME=$(basename "$config")
    SERVICE=$(jq -r '.service_name' "$config")
    URL=$(jq -r '.base_url' "$config")
    echo "$NAME: $SERVICE ($URL)"
done
```

**Then use AskUserQuestion** with the discovered projects.

### 2. Pre-Flight Validation ✨

**CRITICAL:** Always validate configuration before executing tests

### 1. Pre-Flight Validation ✨ NEW

**CRITICAL:** Always validate configuration before executing tests.

```bash
# Run validation script
python validate_config.py config.json

# Check exit code
if [ $? -ne 0 ]; then
    echo "❌ Validation failed. Fix issues before running test."
    exit 1
fi
```

**What gets validated:**
- ✅ JWT token not expired (>5 min remaining)
- ✅ Base URL reachable (health check)
- ✅ Authentication working (no 401s)
- ✅ Critical endpoints responding (sample 5 endpoints)
- ✅ Configuration values valid (users > 0, duration > 0)

**Example validation output:**
```
🔍 API Configuration Validator
======================================================================

1️⃣  Checking JWT Token...
   ✅ JWT token valid for 25 minutes

2️⃣  Checking Base URL Reachability...
   ✅ Health endpoint reachable: /api/v1/health

3️⃣  Checking Authentication...
   ✅ Authentication working: /api/v1/me

4️⃣  Sampling Critical Endpoints...
   ✓ GET /api/v1/health → 200
   ✓ POST /api/v1/orders → 201

5️⃣  Checking Configuration Values...
   ✓ Users: 100
   ✓ Duration: 300s

======================================================================
✅ VALIDATION PASSED
Configuration is ready for performance testing.
======================================================================
```

**If validation fails:**
- Show clear error messages
- Provide fix recommendations
- DO NOT proceed to test execution
- Ask user to fix issues and re-validate

**Common issues caught:**
- 🔴 Expired JWT tokens (prevents 60%+ auth failures)
- 🔴 Wrong API paths (prevents 404 errors)
- 🔴 Backend services down (prevents 502 errors)
- 🔴 Invalid payloads (prevents 400 errors)

### 2. Load Configuration

```python
import json
from pathlib import Path

# Only load config after validation passes
with open('config.json') as f:
    config = json.load(f)

service_type = config['service_type']
auth_type = config['auth_type']
base_url = config['base_url']
load_profile = config['load_profile']
```

### 3. Select Template

Based on service_type and auth_type:

| Service Type | Auth Type | Template |
|--------------|-----------|----------|
| rest-api | jwt | `templates/rest-api-jwt.py.j2` |
| rest-api | apikey | `templates/rest-api-apikey.py.j2` |
| graphql | bearer | `templates/graphql-bearer.py.j2` |
| Custom | * | Generate from base template |

### 4. Render Locust File

```python
from perf_framework.template_renderer import TemplateRenderer

renderer = TemplateRenderer()
template_path = f"templates/{service_type}-{auth_type}.py.j2"

# Render with config variables
locustfile_content = renderer.render(template_path, {
    'base_url': config['base_url'],
    'jwt_token': config['credentials'].get('jwt_token'),
    'api_key': config['credentials'].get('api_key'),
    'endpoints': config['endpoints']
})

# Save to locustfile.py
with open('locustfile.py', 'w') as f:
    f.write(locustfile_content)
```

### 5. Prepare Test Directory

Create directory structure:

```bash
runs/
  2026-11-14T15:30:00Z/
    locustfile.py        # Generated test
    config.json          # Configuration copy
    results/
      stats.csv          # Will be created by Locust
      failures.csv
      exceptions.csv
```

### 6. Execute Locust

Run with parameters from load_profile:

```python
from perf_framework.locust_runner import LocustRunner

runner = LocustRunner()

# Run Locust with config
result = runner.run(
    locustfile='locustfile.py',
    host=config['base_url'],
    users=config['load_profile']['users'],
    spawn_rate=config['load_profile']['spawn_rate'],
    run_time=f"{config['load_profile']['duration']}s",
    headless=True
)
```

**Command executed:**
```bash
locust -f locustfile.py \
  --host https://api.example.com \
  --users 100 \
  --spawn-rate 10 \
  --run-time 300s \
  --headless \
  --csv results/stats
```

### 7. Monitor Execution with Live Progress

**IMPORTANT:** When running tests in background, use the Monitor tool to show real-time progress.

#### Option A: Live Stats Every 60s (Recommended)

```python
# Start test in background
output_file = f'/tmp/test_{run_id}.log'
Bash({
    'command': f'./run_test.sh {config_file} {duration} > {output_file} 2>&1',
    'run_in_background': True,
    'description': f'Run {duration}s performance test'
})

# One stats line every 60s (third arg overrides the interval)
Monitor({
    'command': f'./monitor_progress.sh {output_file} {duration} 60',
    'description': f'Performance test ({duration}s)',
    'timeout_ms': duration * 1000 + 240000
})
```

**What user sees (one line per minute):**
```
📊 Performance test started — live update every 60s (planned 300s)
⏱️  60s/300s  users=100  rps=36  fail/s=0  p50=3400ms  p95=4500ms  total=2100 req (0 failed)
⏱️  120s/300s  users=100  rps=37  fail/s=0  p50=3400ms  p95=4600ms  total=4300 req (0 failed)
⏱️  180s/300s  users=100  rps=35  fail/s=2  p50=3500ms  p95=4800ms  total=6400 req (12 failed) ⚠️ errors
...
✅ Test complete in 318s
   final: users=100  rps=36  fail/s=0  p50=3400ms  p95=4500ms  total=10900 req (12 failed)
   open runs/2026-11-14T19-52-34Z/PERFORMANCE_REPORT.html
```

**Relay each line to the user as it arrives.** Flags appear when `fail/s > 0` or `p50 > 5s` — if either persists for 2+ updates, tell the user the backend is saturating or auth is failing and offer to stop the test.

Stats come from the latest `Aggregated` row of `<run_dir>/results/stats_stats_history.csv`; the script finds the run dir from the `Run directory:` line in the log.

#### Option B: Monitor Locust Stats CSV

```python
Monitor({
    'command': f'''
        # Wait for stats file to be created
        while [ ! -f "{run_dir}/results/stats_stats_history.csv" ]; do
            sleep 1
        done

        # Stream stats updates
        tail -f "{run_dir}/results/stats_stats_history.csv" | while IFS=',' read -r ts name typ reqs fails med avg min max p50 p66 p75 p80 p90 p95 p98 p99 p999 p9999 p100 rps fps; do
            if [ "$name" = "Aggregated" ]; then
                printf "\\r📊 RPS: %-6s | p50: %-6s | p95: %-6s | Errors: %-5s" \\
                    "$rps" "${{p50}}ms" "${{p95}}ms" "$fails"
            fi
        done
    ''',
    'description': 'Live Locust statistics',
    'timeout_ms': duration * 1000 + 60000
})
```

### 8. Collect Results

When test completes:
```bash
runs/2026-11-14T15:30:00Z/results/
  stats.csv              # Request statistics
  stats_history.csv      # Timeline data
  failures.csv           # Failed requests
  exceptions.csv         # Exceptions log
```

## Dry Run Mode

For validation without actual load:

```bash
# Via CLI
perf-framework execute --config config.json --dry-run

# Shows what would be executed:
# - Template selected
# - Locustfile.py content preview
# - Locust command that would run
# - Does NOT actually run Locust
```

## Generated Locustfile Structure

Example for REST API with JWT:

```python
from locust import HttpUser, task
import json


class APIUser(HttpUser):
    host = "https://api.example.com"

    def on_start(self):
        """Set up authentication headers."""
        self.headers = {
            "Authorization": "Bearer eyJhbGc...",
            "Content-Type": "application/json"
        }

    @task(3)
    def create_order(self):
        """POST /api/v1/orders"""
        payload = {
            "item": "widget",
            "quantity": 1
        }
        self.client.post(
            "/api/v1/orders",
            headers=self.headers,
            json=payload
        )

    @task(7)
    def get_order(self):
        """GET /api/v1/orders/{id}"""
        self.client.get(
            "/api/v1/orders/123",
            headers=self.headers
        )
```

## Common Scenarios

### Scenario 1: No Arguments - Interactive Selection
```
User: /perf-execute

Actions:
1. Discover projects in projects/ folder
2. Extract metadata (service_name, base_url) for each
3. Present AskUserQuestion with project options:
   - bcas-add-in-config.json - BCAS Add-in API
   - orders-api-config.json - Orders API
4. User selects: bcas-add-in-config.json
5. Ask for duration:
   - 1 minute (60s) [Default]
   - 5 minutes (300s)
   - 10 minutes (600s)
   - Custom
6. User selects: 5 minutes
7. Run: ./run_test.sh bcas-add-in-config.json 300
8. Collect K8s metrics automatically
9. Generate unified report
10. Open PERFORMANCE_REPORT.html
```

### Scenario 2: With Config Name
```
User: /perf-execute bcas-add-in-config.json

Actions:
1. Find config in projects/ folder
2. Ask for duration (or use default 60s)
3. Run: ./run_test.sh bcas-add-in-config.json 60
4. Collect K8s metrics
5. Generate report
```

### Scenario 3: With Config and Duration
```
User: /perf-execute bcas-add-in-config.json 300

Actions:
1. Find projects/bcas-add-in-config.json
2. Validate configuration
3. Run: ./run_test.sh bcas-add-in-config.json 300
4. Auto-collect K8s metrics (60 samples over 5 min)
5. Generate unified report with performance + K8s metrics
6. Open report automatically
```

### Scenario 4: Multiple Projects Available
```
User: /perf-execute

Projects found:
- bcas-add-in-config.json
- orders-api-config.json
- payments-api-config.json
- users-api-config.json

Actions:
1. Use AskUserQuestion to show all 4 projects with descriptions
2. User selects one (NOT all - never run multiple)
3. Ask duration
4. Run selected project only
```

## Error Handling

### Connection Errors
```
Error: Failed to connect to https://api.example.com
Actions:
- Verify base_url is correct
- Check service is running
- Test connectivity: curl https://api.example.com
```

### Authentication Errors
```
Error: 401 Unauthorized on all requests
Actions:
- Verify credentials in config.json
- Check token hasn't expired
- Test single request: curl -H "Authorization: Bearer ..."
```

### High Error Rate During Test
```
Warning: Error rate > 5% (current: 12%)
Actions:
- Pause test and investigate
- Reduce load (fewer users or lower spawn rate)
- Check service logs for issues
```

## Execution Checklist

Before running:

- [ ] config.json exists and is valid
- [ ] Locust is installed
- [ ] Service is accessible
- [ ] Credentials are current (not expired)
- [ ] Enough time allocated for test
- [ ] Monitoring ready (Prometheus/New Relic if used)

During test:

- [ ] Monitor RPS and latency
- [ ] Watch error rate
- [ ] Check service health
- [ ] Verify user ramp-up is smooth

After test:

- [ ] Results saved to runs/ directory
- [ ] CSV files generated
- [ ] No critical errors in exceptions.csv
- [ ] Ready for `/perf-report`

## Output Structure

```
runs/2026-11-14T15:30:00Z/
├── locustfile.py           # Generated test file
├── config.json             # Configuration used
└── results/
    ├── stats.csv           # Per-endpoint statistics
    ├── stats_history.csv   # Timeline data
    ├── failures.csv        # Failed requests
    └── exceptions.csv      # Exception details
```

## Next Steps

After execution completes:
1. Review results in runs/*/results/
2. Run `/perf-report` to generate HTML report with charts
3. Analyze against SLA thresholds
4. Check Prometheus/New Relic for backend metrics

## References

- LocustRunner: `cli/perf_framework/locust_runner.py`
- TemplateRenderer: `cli/perf_framework/template_renderer.py`
- Templates: `templates/` directory
- Locust docs: https://docs.locust.io/
