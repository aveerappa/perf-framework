from pathlib import Path
import yaml


class ServiceAnalyzer:
    """Analyzes service repositories to detect types and patterns."""

    def __init__(self):
        pass

    def find_openapi_spec(self, repo_path: Path) -> Path | None:
        """
        Find OpenAPI specification file in repository.

        Args:
            repo_path: Repository root directory

        Returns:
            Path to OpenAPI spec file, or None if not found
        """
        # Search for common OpenAPI file names
        for pattern in ["openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.yml"]:
            for spec_file in repo_path.rglob(pattern):
                # Verify it's actually an OpenAPI spec
                try:
                    content = spec_file.read_text()
                    if spec_file.suffix in ['.yaml', '.yml']:
                        data = yaml.safe_load(content)
                    else:
                        import json
                        data = json.loads(content)

                    if 'openapi' in data or 'swagger' in data:
                        return spec_file
                except Exception:
                    continue

        return None

    def parse_openapi_endpoints(self, spec_path: Path) -> list[dict]:
        """
        Parse endpoints from OpenAPI specification.

        Args:
            spec_path: Path to OpenAPI spec file

        Returns:
            list of dicts with path, method, requires_auth
        """
        content = spec_path.read_text()

        if spec_path.suffix in ['.yaml', '.yml']:
            spec = yaml.safe_load(content)
        else:
            import json
            spec = json.loads(content)

        endpoints = []

        for path, methods in spec.get('paths', {}).items():
            for method, details in methods.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    # Check if endpoint requires auth
                    requires_auth = bool(details.get('security'))

                    endpoints.append({
                        "path": path,
                        "method": method.upper(),
                        "requires_auth": requires_auth
                    })

        return endpoints

    def detect_auth_type(self, repo_path: Path) -> str:
        """
        Detect authentication type from codebase.

        Args:
            repo_path: Repository root directory

        Returns:
            Auth type: "jwt", "apikey", "oauth", "basic", or "none"
        """
        # Search for JWT patterns
        for py_file in repo_path.rglob("*.py"):
            try:
                content = py_file.read_text()
                if 'jwt.decode' in content or 'jwt.encode' in content:
                    return "jwt"
                if 'X-API-Key' in content or 'api_key' in content:
                    return "apikey"
            except Exception:
                continue

        return "none"

    def detect_service_type(self, repo_path: Path) -> str:
        """
        Detect service type from repository.

        Args:
            repo_path: Repository root directory

        Returns:
            Service type: "rest-api", "graphql", "web-app", "microservice", or "unknown"
        """
        # Check for OpenAPI spec (REST API)
        if self.find_openapi_spec(repo_path):
            return "rest-api"

        # Check for GraphQL schema
        for gql_file in repo_path.rglob("*.graphql"):
            return "graphql"

        # Check for web app frameworks
        for html_file in repo_path.rglob("*.html"):
            return "web-app"

        return "unknown"
