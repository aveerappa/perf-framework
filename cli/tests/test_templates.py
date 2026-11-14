from pathlib import Path
from perf_framework.template_renderer import TemplateRenderer

def test_rest_api_jwt_template():
    """Test REST API JWT template renders valid Locust code."""
    templates_dir = Path.home() / "perf-framework/templates"
    renderer = TemplateRenderer(templates_dir)

    context = {
        "base_url": "https://api.example.com",
        "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "endpoints": [
            {
                "name": "create_order",
                "method": "POST",
                "path": "/api/v1/orders",
                "payload": {"product_id": 123, "quantity": 2}
            },
            {
                "name": "get_order",
                "method": "GET",
                "path": "/api/v1/orders/123",
                "payload": None
            }
        ]
    }

    code = renderer.render("rest-api-jwt.py.j2", context)

    # Verify valid Python syntax
    is_valid, error = renderer.validate_syntax(code)
    assert is_valid, f"Generated code has syntax error: {error}"

    # Verify key components present
    assert "from locust import HttpUser, task" in code
    assert 'host = "https://api.example.com"' in code
    assert '"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."' in code
    assert 'self.client.post' in code
    assert '"/api/v1/orders"' in code
    assert 'self.client.get' in code
    assert '"/api/v1/orders/123"' in code
    assert "'product_id': 123" in code
    assert "'quantity': 2" in code
