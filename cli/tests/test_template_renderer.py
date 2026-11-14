from pathlib import Path
from perf_framework.template_renderer import TemplateRenderer
import pytest
import tempfile

def test_render_simple_template():
    """Test rendering Jinja2 template with context variables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        templates_dir = Path(tmpdir)
        template_file = templates_dir / "test.py.j2"
        template_file.write_text("""
def test_function():
    url = "{{ base_url }}"
    token = "{{ auth_token }}"
    return url, token
""")

        renderer = TemplateRenderer(templates_dir)
        result = renderer.render("test.py.j2", {
            "base_url": "https://api.example.com",
            "auth_token": "Bearer abc123"
        })

        assert 'url = "https://api.example.com"' in result
        assert 'token = "Bearer abc123"' in result

def test_validate_syntax_valid_python():
    """Test syntax validation accepts valid Python code."""
    renderer = TemplateRenderer(Path("/tmp"))
    code = """
def my_function():
    x = 1 + 2
    return x
"""
    is_valid, error = renderer.validate_syntax(code)
    assert is_valid is True
    assert error == ""

def test_validate_syntax_invalid_python():
    """Test syntax validation rejects invalid Python code."""
    renderer = TemplateRenderer(Path("/tmp"))
    code = "def invalid syntax here"

    is_valid, error = renderer.validate_syntax(code)
    assert is_valid is False
    assert "SyntaxError" in error

def test_render_escapes_dangerous_input():
    """Test template rendering escapes potentially malicious input (Review Focus #1)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        templates_dir = Path(tmpdir)
        template_file = templates_dir / "test.py.j2"
        template_file.write_text('token = "{{ auth_token }}"')

        renderer = TemplateRenderer(templates_dir)
        # Attempt code injection via template variable
        result = renderer.render("test.py.j2", {
            "auth_token": "{{ __import__('os').system('rm -rf /') }}"
        })

        # Should be escaped as literal string, not executed
        assert "__import__" in result
        assert "system" in result
        # Verify it's a string literal, not executable code
        assert 'token = "{{ __import__' in result or "token = '{{ __import__" in result
