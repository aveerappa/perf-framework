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

### 5. Pre-Validate API Endpoints

**CRITICAL:** Always validate APIs before creating final config.

```python
import requests
from datetime import datetime
import jwt

def pre_validate_apis(config):
    """
    Validate API endpoints and credentials before test execution.
    Catches configuration issues early.
    """
    
    issues = []
    base_url = config['base_url']
    
    # 1. Check JWT Token Expiration
    if 'jwt_token' in config.get('credentials', {}):
        token = config['credentials']['jwt_token']
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            exp = decoded.get('exp')
            if exp:
                exp_time = datetime.fromtimestamp(exp)
                now = datetime.now()
                if now.timestamp() > exp:
                    issues.append(f"❌ JWT token EXPIRED at {exp_time}")
                else:
                    time_left = (exp_time - now).total_seconds() / 60
                    if time_left < 5:
                        issues.append(f"⚠️ JWT token expires in {time_left:.0f} minutes")
                    else:
                        print(f"✓ JWT token valid for {time_left:.0f} minutes")
        except Exception as e:
            issues.append(f"⚠️ Could not decode JWT token: {e}")
    
    # 2. Test Base URL Reachability
    try:
        resp = requests.get(f"{base_url}/api/health", timeout=5)
        if resp.status_code == 200:
            print(f"✓ Health endpoint responding: {resp.status_code}")
        else:
            # Try with /v1 prefix
            resp2 = requests.get(f"{base_url}/api/v1/health", timeout=5)
            if resp2.status_code == 200:
                print(f"✓ Health endpoint (v1) responding: {resp2.status_code}")
            else:
                issues.append(f"⚠️ Health endpoint returned {resp.status_code}")
    except requests.RequestException as e:
        issues.append(f"❌ Cannot reach {base_url}: {e}")
    
    # 3. Test Authentication
    if 'credentials' in config:
        creds = config['credentials']
        headers = {}
        
        if 'jwt_token' in creds:
            headers['Authorization'] = f"Bearer {creds['jwt_token']}"
        elif 'api_key' in creds:
            key_header = creds.get('header_name', 'X-API-Key')
            headers[key_header] = creds['api_key']
        
        if headers:
            # Test authenticated endpoint
            test_endpoint = f"{base_url}/api/v1/me"
            try:
                resp = requests.get(test_endpoint, headers=headers, timeout=5)
                if resp.status_code == 200:
                    print(f"✓ Authentication working: {resp.status_code}")
                elif resp.status_code == 401:
                    issues.append(f"❌ Authentication failed (401) - check token validity")
                else:
                    issues.append(f"⚠️ Auth endpoint returned {resp.status_code}")
            except requests.RequestException as e:
                issues.append(f"⚠️ Could not test authentication: {e}")
    
    # 4. Sample Critical Endpoints
    print("\n🔍 Sampling critical endpoints...")
    for endpoint in config.get('endpoints', [])[:3]:  # Test first 3
        path = endpoint['path']
        method = endpoint['method']
        
        # Replace path params with test values
        if '{' in path and 'path_params' in endpoint:
            for param, value in endpoint['path_params'].items():
                path = path.replace(f'{{{param}}}', str(value))
        
        url = f"{base_url}{path}"
        
        try:
            if method == 'GET':
                resp = requests.get(url, headers=headers, timeout=5)
            elif method == 'POST':
                payload = endpoint.get('payload', {})
                resp = requests.post(url, json=payload, headers=headers, timeout=5)
            
            if 200 <= resp.status_code < 300:
                print(f"  ✓ {method} {path}: {resp.status_code}")
            elif resp.status_code == 401:
                issues.append(f"  ❌ {method} {path}: 401 Unauthorized")
            elif resp.status_code == 404:
                issues.append(f"  ⚠️ {method} {path}: 404 Not Found - check path")
            elif resp.status_code == 502:
                issues.append(f"  ❌ {method} {path}: 502 Bad Gateway - backend issue")
            else:
                issues.append(f"  ⚠️ {method} {path}: {resp.status_code}")
        except requests.RequestException as e:
            issues.append(f"  ❌ {method} {path}: {e}")
    
    return issues
```

**Run validation:**

```python
# After building config
print("\n" + "="*60)
print("🔍 PRE-VALIDATION: Testing API endpoints...")
print("="*60)

issues = pre_validate_apis(config)

if issues:
    print("\n⚠️ VALIDATION ISSUES FOUND:")
    for issue in issues:
        print(f"  {issue}")
    
    print("\n❌ Please fix issues before proceeding to /perf-execute")
    print("Validation report saved to: validation_report.txt")
    
    # Save validation report
    with open('validation_report.txt', 'w') as f:
        f.write("API Pre-Validation Report\n")
        f.write("="*60 + "\n")
        for issue in issues:
            f.write(f"{issue}\n")
else:
    print("\n✅ All validations passed!")
    print("Ready to proceed with /perf-execute")
```

**What Gets Validated:**

1. **JWT Token Expiration**
   - Decodes token to check `exp` timestamp
   - Warns if < 5 minutes remaining
   - Blocks if already expired

2. **Base URL Reachability**
   - Tests health endpoint
   - Tries both `/api/health` and `/api/v1/health`
   - Verifies service is up

3. **Authentication Works**
   - Makes test request to `/me` or similar
   - Confirms token/key is valid
   - Identifies 401 errors early

4. **Sample Endpoint Testing**
   - Tests first 3 endpoints from config
   - Identifies 404 (wrong path), 502 (backend down)
   - Catches payload issues

5. **Path Consistency**
   - Checks for `/api/v1/` vs `/api/` inconsistencies
   - Validates JWKS and well-known paths

### 6. Validate Configuration

Check:
- [ ] Base URL is reachable (required via pre-validation)
- [ ] Credentials are non-empty if auth required
- [ ] JWT token is not expired (required via pre-validation)
- [ ] Users > 0, spawn_rate > 0, duration > 0
- [ ] All required endpoints have payloads if POST/PUT/PATCH
- [ ] Critical endpoints return 2xx status codes (via pre-validation)

### 7. Add Request Payloads

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
