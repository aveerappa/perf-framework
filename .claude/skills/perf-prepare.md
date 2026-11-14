---
name: perf-prepare
description: Use when configuring performance test parameters after service analysis - sets up load profile (users, spawn rate, duration), credentials (JWT tokens, API keys), base URL, and validates configuration. Triggers on "configure load test", "set up test parameters", "add credentials", or after /perf-analyze completes.
---

# Performance Test Preparation

Configure load testing parameters, credentials, and validate the test setup before execution.

## When to Use

- After `/perf-analyze` has created a test plan
- User wants to configure load testing parameters
- Need to gather credentials for authenticated endpoints
- Setting up test duration and user counts

## Prerequisites

- Test plan file exists (from `/perf-analyze`)
- Service type and endpoints identified
- Authentication method known

## Core Workflow

### 1. Load Test Plan

```python
import yaml
from pathlib import Path

# Read test plan from /perf-analyze
with open('test-plan.yaml') as f:
    plan = yaml.safe_load(f)

service_type = plan['service_type']
auth_type = plan['auth_type']
endpoints = plan['endpoints']
```

### 2. Gather Load Parameters

Ask user for:

**Required:**
- **Base URL**: Target service URL (e.g., `https://api.example.com`)
- **Number of users**: Concurrent virtual users (e.g., 100)
- **Spawn rate**: Users per second (e.g., 10)
- **Duration**: Test duration in seconds (e.g., 300 for 5 minutes)

**Optional:**
- **Target RPS**: Requests per second goal
- **SLA threshold**: Response time requirement (e.g., p95 < 500ms)

### 3. Gather Authentication Credentials

Based on `auth_type` from test plan:

**JWT Authentication:**
```
Ask: "Provide JWT token for authentication"
Store: jwt_token in config
```

**API Key Authentication:**
```
Ask: "Provide API key"
Ask: "Header name (default: X-API-Key)"
Store: api_key and header_name in config
```

**Bearer Token:**
```
Ask: "Provide Bearer token"
Store: bearer_token in config
```

**OAuth:**
```
Ask: "Provide client_id and client_secret"
Ask: "Token endpoint URL"
Store: OAuth config
```

### 4. Build Configuration

Create complete config file:

```json
{
  "service_type": "rest-api",
  "auth_type": "jwt",
  "base_url": "https://api.example.com",
  "credentials": {
    "jwt_token": "eyJhbGc..."
  },
  "load_profile": {
    "users": 100,
    "spawn_rate": 10,
    "duration": 300
  },
  "endpoints": [
    {
      "path": "/api/v1/orders",
      "method": "POST",
      "requires_auth": true,
      "payload": {
        "item": "widget",
        "quantity": 1
      }
    }
  ],
  "sla": {
    "p95_ms": 500,
    "error_rate": 0.01
  }
}
```

### 5. Validate Configuration

Check:
- [ ] Base URL is reachable (optional ping test)
- [ ] Credentials are non-empty if auth required
- [ ] Users > 0, spawn_rate > 0, duration > 0
- [ ] All required endpoints have payloads if POST/PUT/PATCH

### 6. Add Request Payloads

For POST/PUT/PATCH endpoints, ask user for example payloads:

```
Endpoint: POST /api/v1/orders
Ask: "Provide example JSON payload for this endpoint"
User provides:
{
  "item": "widget",
  "quantity": 1,
  "customer_id": "cust_123"
}
```

Store in config under each endpoint.

## Configuration Structure

### Minimal Example
```json
{
  "base_url": "https://api.example.com",
  "load_profile": {
    "users": 50,
    "spawn_rate": 5,
    "duration": 180
  }
}
```

### Full Example with Auth
```json
{
  "service_type": "rest-api",
  "auth_type": "jwt",
  "base_url": "https://api.staging.company.com",
  "credentials": {
    "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  },
  "load_profile": {
    "users": 200,
    "spawn_rate": 20,
    "duration": 600,
    "target_rps": 1000
  },
  "endpoints": [
    {
      "path": "/api/v1/orders",
      "method": "POST",
      "requires_auth": true,
      "weight": 3,
      "payload": {
        "item": "widget",
        "quantity": 1
      }
    },
    {
      "path": "/api/v1/orders/{id}",
      "method": "GET",
      "requires_auth": true,
      "weight": 7
    }
  ],
  "sla": {
    "p50_ms": 200,
    "p95_ms": 500,
    "p99_ms": 1000,
    "error_rate": 0.01,
    "success_rate": 0.99
  }
}
```

## Load Profile Guidance

### Recommended Starting Points

| Scenario | Users | Spawn Rate | Duration |
|----------|-------|------------|----------|
| Smoke test | 10 | 1 | 60s |
| Light load | 50 | 5 | 300s |
| Normal load | 100 | 10 | 600s |
| Stress test | 500+ | 50 | 1800s |

### SLA Thresholds

Typical web API targets:
- p50 < 100ms
- p95 < 500ms  
- p99 < 1000ms
- Error rate < 1%

## Common Scenarios

### Scenario: REST API with JWT
```
User: Configure load test for orders API
Load test plan: test-plan.yaml exists

Actions:
1. Read test plan (service_type: rest-api, auth: jwt)
2. Ask: "Base URL?" → https://api.staging.company.com
3. Ask: "JWT token?" → eyJhbGc...
4. Ask: "Number of users?" → 100
5. Ask: "Spawn rate?" → 10  
6. Ask: "Duration (seconds)?" → 300
7. Ask for POST /orders payload → {"item": "widget", "qty": 1}
8. Save to config.json
9. Show summary and validation results
```

### Scenario: API Key Authentication
```
User: Set up perf test config
Test plan: auth_type is "apikey"

Actions:
1. Ask: "Base URL?" → https://internal-api.company.com
2. Ask: "API key?" → sk_live_abc123
3. Ask: "Header name? (default: X-API-Key)" → X-Internal-API-Key
4. Continue with load profile questions
5. Save config with api_key credentials
```

## Validation Checklist

Before saving config:

- [ ] Base URL starts with http:// or https://
- [ ] Auth credentials provided if auth_type != "none"
- [ ] All numeric values > 0
- [ ] POST/PUT/PATCH endpoints have payloads
- [ ] Endpoint weights sum to reasonable distribution
- [ ] SLA thresholds are realistic

## Output

Save configuration to `config.json` (or user-specified path):

```bash
# Via CLI
perf-framework prepare --plan test-plan.yaml --output config.json

# Via skill
# Create config.json in current directory
```

## Next Steps

After preparation completes:
1. Review config.json
2. Run `/perf-execute` to generate and run Locust tests
3. Optionally do a smoke test first (10 users, 60s)

## References

- Template renderer: `cli/perf_framework/template_renderer.py`
- Templates: `templates/` directory
- Locust configuration: https://docs.locust.io/en/stable/configuration.html
