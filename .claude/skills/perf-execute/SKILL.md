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
- **AWS SSO setup**: Set `AWS_ENV_FILE` environment variable pointing to your aws-env.sh script, or configure a common location (see AWS SSO Configuration below)

## Project Selection Workflow

**IMPORTANT:** When user invokes `/perf-execute` without arguments or with unclear arguments:

1. **List Available Projects** from `projects/` directory
2. **Show project details** (service name, base URL)
3. **Ask user to select** which project to run
4. **Ask for the full load profile** (users, spawn_rate, duration, target_rps) — ALWAYS, every run
5. **Write the answers into the config** and run `./preflight.sh` in the FOREGROUND
6. **DO NOT run all projects** - only run the selected one

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
```

Then ask for the **full load profile** in ONE AskUserQuestion call with four questions. Read the current values from the config first:

```bash
jq -r '.load_profile | "\(.users) \(.spawn_rate) \(.duration) \(.target_rps)"' projects/<config>.json
```

| Header | Question | First option | Alternatives |
|--------|----------|--------------|--------------|
| `Users` | How many concurrent users? | `<current> (current)` | 50 / 200 / 500 |
| `Spawn rate` | Users spawned per second? | `<current> (current)` | 10 / 25 / 100 |
| `Duration` | Test duration in seconds? | `<current>s (current)` | 60s / 300s / 600s |
| `Target RPS` | Target requests per second? | `<current> (current)` | 100 / 250 / 1000 |

Drop any alternative equal to the current value. `target_rps` is informational only — Locust does not consume it; it is recorded in the config and shown in the report.

### Step 3: Persist the Load Profile

Write the answers back so they become the next run's defaults:

```bash
jq --argjson u "$USERS" --argjson s "$SPAWN" --argjson d "$DURATION" --argjson r "$TARGET_RPS" \
   '.load_profile = {users:$u, spawn_rate:$s, duration:$d, target_rps:$r}' \
   projects/<config>.json > /tmp/cfg.json && mv /tmp/cfg.json projects/<config>.json
```

### Step 4: AWS SSO Configuration

**IMPORTANT:** Before running pre-flight, ensure AWS SSO is configured:

```bash
# Option 1: Set AWS_ENV_FILE environment variable (recommended for portability)
export AWS_ENV_FILE="$HOME/path/to/your/aws-env.sh"

# Option 2: Use common location that preflight.sh checks:
#   - ~/.aws/aws-env.sh
#   - ~/.config/aws/aws-env.sh
#   - $HOME/Documents/Work/workspace/aws-sso-setup/aws-env.sh (legacy default)
```

If `AWS_ENV_FILE` is not set, `preflight.sh` will search these locations in order and use the first one found.

### Step 5: Pre-flight in the Foreground

Run with a plain (NOT background) Bash call and `timeout: 180000` — `aws-qa-login` may open a browser and wait for the user:

```bash
./preflight.sh projects/<config>.json
```

| Exit | Meaning | Action |
|------|---------|--------|
| 0 | All checks passed | Continue to Step 5 |
| 2 | Usage / config file not found | Fix the path; stop |
| 10 | Barracuda VPN not connected | Tell user to connect Barracuda VPN Client; stop |
| 11 | AWS QA SSO login failed or cancelled | Tell user to run `aws-qa-login` manually; stop |
| 12 | kubectl cannot list pods in the namespace | Show output; stop |
| other | `validate_config.py` failed (expired JWT, 401s, bad endpoints) | Show output; stop |

Never start the test on a non-zero exit.

### Step 6: Execute Selected Project

```bash
./run_test.sh <selected-config>.json $DURATION
```

Launch in the background and monitor exactly as in Core Workflow §7. `run_test.sh` re-runs `preflight.sh` as its own step 1; by then the SSO session is fresh, so it is non-interactive.

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

Claude: Asks four questions — Users [100 (current) / 50 / 200 / 500],
        Spawn rate [50 (current) / 10 / 25 / 100],
        Duration [900s (current) / 60s / 300s / 600s],
        Target RPS [500 (current) / 100 / 250 / 1000]

User: 100 users, 50/s, 300s, 500 rps

Claude: Writes load_profile into projects/bcas-add-in-config.json
Claude: Runs ./preflight.sh projects/bcas-add-in-config.json   (foreground; browser may open for SSO)
        → ✅ PRE-FLIGHT PASSED
Claude: Runs ./run_test.sh bcas-add-in-config.json 300          (background + Monitor)
```

### When Argument Provided

If user provides config name directly: `/perf-execute bcas-add-in-config.json`
- Skip project selection
- STILL ask the full load profile (Step 2) and persist it (Step 3)
- STILL run `./preflight.sh` in the foreground (Step 4) — never skip it
- Run after preflight exits 0

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

### 2. Pre-Flight Checks (environment + config)

**CRITICAL:** Always run pre-flight in the FOREGROUND before executing tests. It may open a browser for AWS SSO login, which would hang invisibly inside a background job.

```bash
./preflight.sh projects/<config>.json    # plain Bash call, timeout 180000
```

| Exit | Meaning | Action |
|------|---------|--------|
| 0 | All checks passed | Continue |
| 2 | Usage / config file not found | Fix the path; stop |
| 10 | Barracuda VPN not connected | Tell user to connect Barracuda VPN Client; stop |
| 11 | AWS QA SSO login failed or cancelled | Tell user to run `aws-qa-login` manually; stop |
| 12 | kubectl cannot list pods in the namespace | Show output; stop |
| other | `validate_config.py` failed | Show output; stop |

**What gets checked, in order (each is a precondition for the next):**
1. **Barracuda VPN** — client process running AND a `utun` interface holding a `10.x` address
2. **AWS QA SSO** — runs the user's `aws-qa-login` zsh function (sourced from the aws-env.sh file found via `AWS_ENV_FILE` env var or standard locations); opens a browser login only if the session is expired, then refreshes kubeconfig for `bcas-qa-ue2-default-cluster`
3. **kubectl pod access** — `kubectl get pods -n <namespace>` must list ≥1 pod (namespace = `service_name` with `_`→`-`)
4. **Configuration** — existing `validate_config.py`:
   - ✅ JWT token not expired (>5 min remaining)
   - ✅ Base URL reachable (health check)
   - ✅ Authentication working (no 401s)
   - ✅ Critical endpoints responding (sample 5 endpoints)
   - ✅ Configuration values valid (users > 0, duration > 0)

**Example output:**
```
🛫 Pre-flight Checks
======================================================================
Config: projects/bcas-add-in-config.json
======================================================================

1️⃣  Checking Barracuda VPN...
   ✅ VPN connected (utun4: 10.39.244.233)

2️⃣  Checking AWS QA SSO session...
   SSO session is still valid for profile 'qa'
   Updating kubeconfig...
   ✅ AWS qa profile active

3️⃣  Checking kubectl access to namespace bcas-add-in...
   ✅ 2 pod(s) found in bcas-add-in

4️⃣  Validating configuration...
🔍 API Configuration Validator
   ... (JWT, base URL, auth, endpoints, config values) ...
✅ VALIDATION PASSED

======================================================================
✅ PRE-FLIGHT PASSED
======================================================================
```

**If pre-flight fails:**
- Show the output as-is (it names the failing check and the fix)
- DO NOT proceed to test execution
- Ask user to fix the issue and re-run

**Common issues caught:**
- 🔴 VPN disconnected (prevents kubectl/metrics failures)
- 🔴 Expired AWS SSO session (prevents silently empty K8s metrics)
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
5. Ask load profile (users, spawn_rate, duration, target_rps) — current config values first
6. User answers: 100 users, 50/s, 300s, 500 rps
7. Write load_profile to projects/bcas-add-in-config.json
8. Run ./preflight.sh projects/bcas-add-in-config.json in foreground; stop on non-zero
9. Run: ./run_test.sh bcas-add-in-config.json 300
10. Collect K8s metrics automatically
11. Generate unified report
12. Open PERFORMANCE_REPORT.html
```

### Scenario 2: With Config Name
```
User: /perf-execute bcas-add-in-config.json

Actions:
1. Find config in projects/ folder
2. Ask load profile (users, spawn_rate, duration, target_rps)
3. Write load_profile to config
4. Run ./preflight.sh in foreground; stop on non-zero
5. Run: ./run_test.sh bcas-add-in-config.json <duration>
6. Collect K8s metrics
7. Generate report
```

### Scenario 3: With Config and Duration
```
User: /perf-execute bcas-add-in-config.json 300

Actions:
1. Find projects/bcas-add-in-config.json
2. Ask load profile with duration pre-selected to 300s (users, spawn_rate, target_rps still asked)
3. Write load_profile to config
4. Run ./preflight.sh in foreground; stop on non-zero
5. Run: ./run_test.sh bcas-add-in-config.json 300
6. Auto-collect K8s metrics (60 samples over 5 min)
7. Generate unified report with performance + K8s metrics
8. Open report automatically
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
3. Ask load profile (users, spawn_rate, duration, target_rps)
4. Write load_profile to config, run ./preflight.sh in foreground
5. Run selected project only
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

## AWS SSO Configuration (Generic Setup)

To make `preflight.sh` work on any computer, configure your AWS SSO environment file location:

### Option 1: Environment Variable (Recommended)

```bash
# In your ~/.zshrc or ~/.bashrc
export AWS_ENV_FILE="$HOME/your-custom-path/aws-env.sh"
```

### Option 2: Standard Locations

Place your `aws-env.sh` in one of these locations (checked in order):
1. `~/.aws/aws-env.sh`
2. `~/.config/aws/aws-env.sh`
3. `$HOME/Documents/Work/workspace/aws-sso-setup/aws-env.sh` (legacy)

`preflight.sh` will automatically find the first existing file.

### What aws-env.sh Should Contain

Your `aws-env.sh` should define the `aws-qa-login` function that:
- Authenticates with AWS SSO
- Updates kubeconfig for your EKS cluster
- Returns 0 on success, non-zero on failure

## Execution Checklist

Before running:

- [ ] config.json exists and is valid
- [ ] Barracuda VPN connected
- [ ] AWS qa SSO session active (aws-qa-login)
- [ ] kubectl can list pods in the target namespace
- [ ] Load profile confirmed for this run
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
