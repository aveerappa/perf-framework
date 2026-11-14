from pathlib import Path
import ast
from jinja2 import Environment, FileSystemLoader, select_autoescape


class TemplateRenderer:
    """Renders Jinja2 templates with syntax validation."""

    def __init__(self, templates_dir: Path):
        """
        Initialize template renderer.

        Args:
            templates_dir: Directory containing Jinja2 templates
        """
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(enabled_extensions=('j2',), default=True)
        )

    def render(self, template_name: str, context: dict) -> str:
        """
        Render a template with given context.

        Args:
            template_name: Name of template file (e.g., "rest-api-jwt.py.j2")
            context: Dictionary of variables to pass to template

        Returns:
            Rendered template string
        """
        template = self.env.get_template(template_name)
        return template.render(context)

    def validate_syntax(self, code: str) -> tuple[bool, str]:
        """
        Validate Python syntax of generated code.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        try:
            ast.parse(code)
            return (True, "")
        except SyntaxError as e:
            return (False, f"SyntaxError: {e}")
