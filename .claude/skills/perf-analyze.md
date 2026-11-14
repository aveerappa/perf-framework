---
name: perf-analyze
description: Use when user wants to analyze a service repository for performance testing - detects service type (REST API, GraphQL, web app), finds OpenAPI specs, identifies endpoints, and detects authentication patterns (JWT, API key, OAuth). Triggers on requests to "analyze service", "performance test setup", "detect API type", or "find endpoints".
---

# Performance Test Analysis

Analyze a service repository to detect its type, endpoints, and authentication requirements for performance testing.

## When to Use

- User wants to set up performance testing for a service
- Need to understand service structure before load testing
- Detecting API endpoints and authentication methods
- Preparing for Locust test generation

## Core Workflow

### 1. Determine Target Repository

Ask user for:
- Repository path (defaults to current directory if they're in a service repo)
- Any hints about service type (REST, GraphQL, web app)
- Known endpoints if OpenAPI spec isn't available

### 2. Run Analysis

Use the ServiceAnalyzer to detect:

```python
from perf_framework.analyzer import ServiceAnalyzer
from pathlib import Path

analyzer = ServiceAnalyzer()
repo_path = Path(user_provided_path)

# Detect service type
service_type = analyzer.detect_service_type(repo_path)

# Find OpenAPI spec if REST API
openapi_spec = analyzer.find_openapi_spec(repo_path)

# Parse endpoints
if openapi_spec:
    endpoints = analyzer.parse_openapi_endpoints(openapi_spec)
else:
    # Ask user to provide endpoints manually

# Detect authentication
auth_type = analyzer.detect_auth_type(repo_path)
```

### 3. Present Findings

Show user:
- **Service type**: REST API, GraphQL, web app, or unknown
- **Authentication**: JWT, API key, OAuth, basic, or none
- **Endpoints found**: List paths and methods
- **OpenAPI spec location** (if found)

### 4. Save Test Plan

Create YAML output file with structure:

```yaml
service_type: rest-api
auth_type: jwt
base_url: https://api.example.com
endpoints:
  - path: /api/v1/orders
    method: POST
    requires_auth: true
  - path: /api/v1/orders/{id}
    method: GET
    requires_auth: true
openapi_spec: ./openapi.yaml
```

## What Analysis Detects

| Detection | Method |
|-----------|--------|
| REST API | Finds OpenAPI/Swagger spec files |
| GraphQL | Finds .graphql schema files |
| Web app | Finds HTML files |
| JWT auth | Searches for `jwt.decode`/`jwt.encode` in Python files |
| API key auth | Searches for `X-API-Key` or `api_key` patterns |

## Common Scenarios

### Scenario: REST API with OpenAPI
```
User: Analyze my orders API for performance testing
Path: ~/projects/orders-api

Actions:
1. Find openapi.yaml in repo
2. Parse 15 endpoints from spec
3. Detect JWT authentication from auth middleware
4. Generate test-plan.yaml
5. Show summary: "Found REST API with JWT auth, 15 endpoints"
```

### Scenario: No OpenAPI Spec
```
User: Set up perf test for internal service
Path: ~/services/billing

Actions:
1. Detect service type: unknown (no OpenAPI)
2. Ask: "What endpoints should I test? (e.g., POST /api/charge, GET /api/invoices)"
3. User provides endpoint list
4. Detect auth: API key found in middleware
5. Generate test plan with user-provided endpoints
```

### Scenario: GraphQL API
```
User: Analyze GraphQL service
Path: ~/graph-api

Actions:
1. Find schema.graphql
2. Detect GraphQL queries and mutations
3. Detect Bearer token auth
4. Generate test plan for GraphQL
5. Recommend graphql-bearer template
```

## Output Format

Always create a test plan file that can be used by `/perf-prepare`:

```bash
# Via CLI
perf-framework analyze ~/projects/orders-api --output test-plan.yaml

# Via skill
# Create test-plan.yaml in current directory
```

## Edge Cases

**No recognizable patterns found:**
- Ask user to describe service manually
- Request endpoint list directly
- Confirm authentication method

**Multiple service types detected:**
- Report all findings
- Ask user which to focus on for testing

**Mixed authentication:**
- List all auth types found
- Ask which endpoints use which auth

## Next Steps

After analysis completes, suggest:
1. Review the test-plan.yaml
2. Run `/perf-prepare` to configure load profile and credentials
3. Mention which template will be used (rest-api-jwt, rest-api-apikey, graphql-bearer)

## References

- ServiceAnalyzer: `cli/perf_framework/analyzer.py`
- Templates: `templates/` directory
- OpenAPI detection: `find_openapi_spec()` method
