# Generic Locust Performance Testing Framework

Multi-agent framework for automated performance testing of web applications, microservices, and APIs.

## Overview

Engineers run 4 phased skills to performance test their services:
1. `/perf-analyze` - Analyze service, detect type and auth patterns
2. `/perf-prepare` - Configure load profile and credentials
3. `/perf-execute` - Generate and run Locust tests
4. `/perf-report` - Analyze results with Prometheus/New Relic data

## Quick Start

### Installation

```bash
cd ~/perf-framework/cli
pip install -e .
```

### Usage

#### Via Claude Code Skills

```
> /perf-analyze
Repo: ~/projects/orders-api
Hint: REST API
Endpoints: POST /api/v1/orders, GET /api/v1/orders/{id}

> /perf-prepare
[Provide JWT token, load targets, SLAs when prompted]

> /perf-execute
[Locust runs automatically]

> /perf-report
[HTML report generated]
```

#### Via CLI (Standalone)

```bash
perf-framework analyze ./my-api-repo --output test-plan.yaml
perf-framework execute --config config.json
perf-framework report --run-id 2026-11-14T15:30:00Z
```

## Architecture

**Tier 1**: Template fast-path for common service types (REST, GraphQL)
**Tier 2**: Reusable Python framework (Prometheus, New Relic, Locust clients)
**Tier 3**: Full agent intelligence for unusual services

## Supported Service Types

- REST APIs with JWT/API key authentication
- GraphQL APIs with Bearer tokens
- Web applications (Selenium-based)
- Internal microservices

## Requirements

- Python 3.9+
- Locust 2.x
- Prometheus/Grafana (for resource metrics)
- New Relic (for APM data)

## Project Structure

```
~/perf-framework/
├── cli/                     # Python framework
│   ├── perf_framework/      # Core modules
│   └── tests/               # Test suite
├── templates/               # Locust templates
│   ├── rest-api-jwt.py.j2
│   ├── rest-api-apikey.py.j2
│   └── graphql-bearer.py.j2
└── runs/                    # Test execution history
```

## Development

Run tests:
```bash
cd cli
pytest -v
```

Current test coverage: 27 passing tests across all modules.

## License

MIT
