from pathlib import Path
from perf_framework.analyzer import ServiceAnalyzer
import tempfile
import json
import yaml

def test_find_openapi_spec():
    """Test finding OpenAPI specification file in repo."""
    analyzer = ServiceAnalyzer()

    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        spec_path = repo / "openapi.yaml"
        spec_path.write_text("""
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /api/orders:
    post:
      security:
        - bearerAuth: []
""")

        found = analyzer.find_openapi_spec(repo)
        assert found == spec_path

def test_parse_openapi_endpoints():
    """Test parsing endpoints from OpenAPI spec."""
    analyzer = ServiceAnalyzer()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
openapi: 3.0.0
paths:
  /api/orders:
    post:
      security:
        - bearerAuth: []
  /api/orders/{id}:
    get: {}
""")
        spec_path = Path(f.name)

    try:
        endpoints = analyzer.parse_openapi_endpoints(spec_path)

        assert len(endpoints) == 2
        assert {"path": "/api/orders", "method": "POST", "requires_auth": True} in endpoints
        assert {"path": "/api/orders/{id}", "method": "GET", "requires_auth": False} in endpoints
    finally:
        spec_path.unlink()

def test_detect_auth_type_jwt():
    """Test detecting JWT authentication pattern in codebase."""
    analyzer = ServiceAnalyzer()

    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        middleware = repo / "auth.py"
        middleware.write_text("""
def verify_jwt_token(token):
    decoded = jwt.decode(token, SECRET_KEY)
    return decoded
""")

        auth_type = analyzer.detect_auth_type(repo)
        assert auth_type == "jwt"

def test_detect_service_type_rest_api():
    """Test detecting REST API service type from OpenAPI spec presence."""
    analyzer = ServiceAnalyzer()

    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / "openapi.yaml").write_text("openapi: 3.0.0")

        service_type = analyzer.detect_service_type(repo)
        assert service_type == "rest-api"
