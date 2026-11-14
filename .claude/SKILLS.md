# Performance Testing Skills

These skills enable automated performance testing workflows in Claude Code.

## Available Skills

### `/perf-analyze`
Analyze a service repository to detect type, endpoints, and authentication.

**When to use:** Starting a new performance test for a service

**Output:** `test-plan.yaml` with detected service configuration

**Example:**
```
> /perf-analyze
Repo path: ~/projects/orders-api
Hint: REST API

[Detects OpenAPI spec, JWT auth, extracts endpoints]
[Creates test-plan.yaml]
```

---

### `/perf-prepare`
Configure load testing parameters and credentials.

**When to use:** After `/perf-analyze`, before running tests

**Output:** `config.json` with complete test configuration

**Example:**
```
> /perf-prepare
Base URL: https://api.staging.company.com
JWT token: eyJhbGc...
Users: 100
Spawn rate: 10/s
Duration: 300s

[Creates config.json with load profile and credentials]
```

---

### `/perf-execute`
Generate Locust test files and run load tests.

**When to use:** After `/perf-prepare`, ready to run the test

**Output:** 
- Generated `locustfile.py`
- Test results in `runs/{timestamp}/results/`

**Example:**
```
> /perf-execute
[Renders template: rest-api-jwt.py.j2]
[Runs: locust --users 100 --run-time 300s]
[Monitors: RPS, latency, errors]
[Saves results to runs/2026-11-14T15:30:00Z/]
```

---

### `/perf-report`
Generate HTML report with charts and analysis.

**When to use:** After `/perf-execute` completes

**Output:** Interactive HTML report with Plotly charts

**Example:**
```
> /perf-report
Run ID: 2026-11-14T15:30:00Z

[Analyzes stats.csv and history]
[Fetches Prometheus/New Relic metrics]
[Generates charts: latency, RPS, errors]
[Evaluates SLA compliance]
[Saves report.html]

✅ Test PASSED
p95: 345ms < 500ms threshold
Errors: 0.3% < 1% threshold
```

## Complete Workflow

```
1. /perf-analyze
   ↓ Creates test-plan.yaml

2. /perf-prepare  
   ↓ Creates config.json

3. /perf-execute
   ↓ Creates locustfile.py
   ↓ Runs Locust
   ↓ Saves results/

4. /perf-report
   ↓ Generates report.html
   ↓ Shows SLA compliance
```

## Standalone CLI Alternative

Skills can also be invoked via CLI:

```bash
# Same workflow without Claude Code
perf-framework analyze ./my-api --output test-plan.yaml
perf-framework prepare --plan test-plan.yaml
perf-framework execute --config config.json
perf-framework report --run-id 2026-11-14T15:30:00Z
```

## Skill Locations

```
.claude/skills/
├── perf-analyze.md    # Service analysis
├── perf-prepare.md    # Configuration
├── perf-execute.md    # Test execution
└── perf-report.md     # Result reporting
```

## Backend Metrics Integration

Skills support optional integration with:
- **Prometheus**: CPU, memory, request duration
- **New Relic**: APM data, transaction traces

Configure in `/perf-report` when available.
