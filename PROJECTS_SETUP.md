# Projects Folder Setup

**Date:** 2026-11-15

## Overview

The `projects/` folder contains performance test configurations for different services. This makes it easy to run tests with auto-discovery and selection.

## Structure

```
perf-framework/
├── projects/                          # Project configurations
│   ├── bcas-add-in-config.json       # BCAS Add-in API config
│   ├── bcas-add-in-test-plan.yaml    # Test plan
│   └── <your-service>-config.json    # Add more projects here
│
└── run_test.sh                        # Smart test runner
```

## Usage

### List Available Projects

```bash
./run_test.sh
```

**Output:**
```
📁 Available Projects:
======================================
  1. bcas-add-in-config.json - bcas-add-in

Usage:
  ./run_test.sh <config-file> [duration-seconds]
```

### Run Test (Default 1 minute)

```bash
./run_test.sh bcas-add-in-config.json
```

### Run Test (Custom Duration)

```bash
# 5 minutes
./run_test.sh bcas-add-in-config.json 300

# 10 minutes
./run_test.sh bcas-add-in-config.json 600
```

### Via Claude Code Skill

```bash
# Just the config name (auto-discovers from projects/)
/perf-execute bcas-add-in-config.json

# With duration
/perf-execute bcas-add-in-config.json 300
```

## Auto-Discovery

The test runner automatically:
1. **Finds config** in `projects/` directory
2. **Extracts service details** (name, base URL, namespace)
3. **Validates configuration** (JWT token, endpoints)
4. **Collects K8s metrics** (auto-detects namespace from service name)
5. **Generates unified report** (performance + K8s metrics)

## Adding New Projects

### 1. Create Configuration

Create `projects/<service-name>-config.json`:

```json
{
  "service_name": "my-api",
  "base_url": "https://my-api.qa.example.com",
  "credentials": {
    "jwt_token": "eyJhbGc..."
  },
  "endpoints": [
    {
      "method": "GET",
      "path": "/api/v1/health",
      "weight": 10,
      "requires_auth": false
    }
  ],
  "load_profile": {
    "users": 10,
    "spawn_rate": 10,
    "duration": 60
  },
  "sla": {
    "p95_ms": 500,
    "error_rate": 0.01
  }
}
```

### 2. Run Test

```bash
./run_test.sh my-api-config.json
```

That's it! The runner handles everything else.

## How It Works

### Smart Project Detection

```bash
# You provide just the filename
./run_test.sh bcas-add-in-config.json

# Script automatically looks in projects/
CONFIG_FILE="projects/bcas-add-in-config.json"

# Extracts metadata
SERVICE_NAME=$(jq -r '.service_name' "$CONFIG_FILE")    # bcas-add-in
BASE_URL=$(jq -r '.base_url' "$CONFIG_FILE")            # https://...
NAMESPACE=$(echo "$SERVICE_NAME" | tr '_' '-')          # bcas-add-in
```

### Auto-Calculated K8s Collection

```bash
# Duration determines sampling
DURATION=300  # 5 minutes
INTERVAL=5    # Every 5 seconds
SAMPLES=$((DURATION / INTERVAL))  # 60 samples

# Namespace from service name
kubectl top pods -n "$NAMESPACE" -l "app.kubernetes.io/name=$NAMESPACE"
```

## Project Templates

### REST API with JWT

```json
{
  "service_name": "orders-api",
  "base_url": "https://orders-api.qa.example.com",
  "credentials": {
    "jwt_token": "eyJhbGc..."
  },
  "endpoints": [
    {
      "method": "POST",
      "path": "/api/v1/orders",
      "weight": 5,
      "requires_auth": true,
      "payload": {"item": "widget", "quantity": 1}
    },
    {
      "method": "GET",
      "path": "/api/v1/orders/{id}",
      "weight": 10,
      "requires_auth": true,
      "path_params": {"id": "12345"}
    }
  ],
  "load_profile": {
    "users": 50,
    "spawn_rate": 10,
    "duration": 300
  },
  "sla": {
    "p50_ms": 200,
    "p95_ms": 500,
    "p99_ms": 1000,
    "error_rate": 0.01
  }
}
```

### GraphQL API

```json
{
  "service_name": "graphql-api",
  "base_url": "https://graphql-api.qa.example.com",
  "credentials": {
    "bearer_token": "abc123..."
  },
  "endpoints": [
    {
      "method": "POST",
      "path": "/graphql",
      "weight": 10,
      "requires_auth": true,
      "payload": {
        "query": "query { users { id name } }"
      }
    }
  ],
  "load_profile": {
    "users": 20,
    "spawn_rate": 5,
    "duration": 120
  }
}
```

## Benefits

### 1. Easy Project Management

```bash
# List all projects
ls -1 projects/*.json

# Quick test any project
./run_test.sh <project>.json
```

### 2. Auto-Discovery from Skills

When you run `/perf-execute bcas-add-in-config.json`, Claude Code automatically:
- Finds config in `projects/`
- Validates configuration
- Runs test with K8s metrics
- Generates unified report

### 3. Reusable Configurations

Keep all your service configs in one place:
```
projects/
├── bcas-add-in-config.json
├── orders-api-config.json
├── payments-api-config.json
└── users-api-config.json
```

### 4. Environment-Specific Configs

```
projects/
├── bcas-add-in-qa-config.json
├── bcas-add-in-staging-config.json
└── bcas-add-in-prod-config.json
```

## Quick Reference

### Run Test Commands

```bash
# List projects
./run_test.sh

# Default (1 min)
./run_test.sh bcas-add-in-config.json

# 5 minutes
./run_test.sh bcas-add-in-config.json 300

# 10 minutes
./run_test.sh bcas-add-in-config.json 600

# Via skill
/perf-execute bcas-add-in-config.json 300
```

### Update Configuration

```bash
# Edit existing project
vi projects/bcas-add-in-config.json

# Test changes immediately
./run_test.sh bcas-add-in-config.json
```

### Validate Before Running

```bash
python validate_config.py projects/bcas-add-in-config.json
```

## Migration from `examples/`

Already done! All files moved:
- ✅ `examples/` → `projects/`
- ✅ `README.md` updated
- ✅ Skills updated

## Next Steps

1. **Add your projects** to `projects/` folder
2. **Run tests** with `./run_test.sh <config>.json [duration]`
3. **View reports** automatically opened after test

Easy performance testing for all your services!

---

**Created:** 2026-11-15  
**Framework:** perf-framework v1.0
