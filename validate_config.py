#!/usr/bin/env python3
"""
API Configuration Validator
Pre-validates API endpoints and credentials before running performance tests.
Catches configuration issues early to prevent wasted test runs.

Usage:
    python validate_config.py config.json
    python validate_config.py --config bcas-add-in-config.json
"""

import sys
import json
import requests
from datetime import datetime
from pathlib import Path
import argparse


class APIValidator:
    """Validates API configuration and endpoints before testing."""

    def __init__(self, config_file):
        self.config_file = Path(config_file)
        self.issues = []
        self.warnings = []
        self.successes = []

        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        with open(self.config_file) as f:
            self.config = json.load(f)

    def validate_all(self):
        """Run all validation checks."""
        print("🔍 API Configuration Validator")
        print("=" * 70)
        print(f"Config: {self.config_file}")
        print(f"Service: {self.config.get('service_name', 'Unknown')}")
        print(f"Base URL: {self.config['base_url']}")
        print("=" * 70)

        self.check_jwt_token()
        self.check_base_url()
        self.check_authentication()
        self.check_critical_endpoints()
        self.check_configuration_values()

        self.print_summary()
        return len(self.issues) == 0

    def check_jwt_token(self):
        """Validate JWT token expiration."""
        print("\n1️⃣  Checking JWT Token...")

        creds = self.config.get('credentials', {})
        if 'jwt_token' not in creds:
            self.warnings.append("No JWT token in config (may not be needed)")
            return

        token = creds['jwt_token']

        try:
            # Decode without verification to read claims
            import jwt as jwt_lib
            decoded = jwt_lib.decode(token, options={"verify_signature": False})

            exp = decoded.get('exp')
            iat = decoded.get('iat')

            if exp:
                exp_time = datetime.fromtimestamp(exp)
                now = datetime.now()

                print(f"   Issued at: {datetime.fromtimestamp(iat) if iat else 'Unknown'}")
                print(f"   Expires at: {exp_time}")
                print(f"   Current time: {now}")

                if now.timestamp() > exp:
                    self.issues.append(
                        f"❌ JWT token EXPIRED at {exp_time} "
                        f"({(now.timestamp() - exp) / 3600:.1f} hours ago)"
                    )
                else:
                    time_left_min = (exp_time - now).total_seconds() / 60
                    if time_left_min < 5:
                        self.warnings.append(
                            f"⚠️ JWT token expires in {time_left_min:.1f} minutes - "
                            "may expire during test"
                        )
                    else:
                        self.successes.append(
                            f"✅ JWT token valid for {time_left_min:.0f} minutes"
                        )
        except ImportError:
            self.warnings.append("⚠️ PyJWT not installed - cannot validate token expiry")
        except Exception as e:
            self.warnings.append(f"⚠️ Could not decode JWT token: {e}")

    def check_base_url(self):
        """Check if base URL is reachable."""
        print("\n2️⃣  Checking Base URL Reachability...")

        base_url = self.config['base_url']

        # Try health endpoints
        health_paths = [
            '/api/health',
            '/api/v1/health',
            '/health',
            '/healthz'
        ]

        for path in health_paths:
            url = f"{base_url}{path}"
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    self.successes.append(f"✅ Health endpoint reachable: {path}")
                    print(f"   ✓ {path} → {resp.status_code}")
                    return
                else:
                    print(f"   ✗ {path} → {resp.status_code}")
            except requests.RequestException:
                print(f"   ✗ {path} → Connection failed")

        self.issues.append(f"❌ No health endpoint reachable at {base_url}")

    def check_authentication(self):
        """Test authentication with provided credentials."""
        print("\n3️⃣  Checking Authentication...")

        creds = self.config.get('credentials', {})
        if not creds:
            self.warnings.append("⚠️ No credentials in config")
            return

        # Build auth headers
        headers = {'Content-Type': 'application/json'}

        if 'jwt_token' in creds:
            headers['Authorization'] = f"Bearer {creds['jwt_token']}"
            auth_type = "JWT"
        elif 'api_key' in creds:
            key_header = creds.get('header_name', 'X-API-Key')
            headers[key_header] = creds['api_key']
            auth_type = "API Key"
        elif 'bearer_token' in creds:
            headers['Authorization'] = f"Bearer {creds['bearer_token']}"
            auth_type = "Bearer Token"
        else:
            self.warnings.append("⚠️ Unknown credential type")
            return

        print(f"   Auth type: {auth_type}")

        # Test authenticated endpoints
        auth_test_paths = [
            '/api/v1/me',
            '/api/me',
            '/api/v1/user',
            '/api/user'
        ]

        base_url = self.config['base_url']

        for path in auth_test_paths:
            url = f"{base_url}{path}"
            try:
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    self.successes.append(f"✅ Authentication working: {path}")
                    print(f"   ✓ {path} → {resp.status_code} (authenticated)")
                    return
                elif resp.status_code == 401:
                    print(f"   ✗ {path} → 401 Unauthorized")
                    self.issues.append(
                        f"❌ Authentication failed (401) - token may be invalid or expired"
                    )
                    return
                elif resp.status_code == 404:
                    print(f"   ✗ {path} → 404 Not Found")
                else:
                    print(f"   ✗ {path} → {resp.status_code}")
            except requests.RequestException as e:
                print(f"   ✗ {path} → {e}")

        self.warnings.append("⚠️ Could not verify authentication (no test endpoint found)")

    def check_critical_endpoints(self):
        """Sample test critical endpoints from config."""
        print("\n4️⃣  Sampling Critical Endpoints...")

        endpoints = self.config.get('endpoints', [])
        if not endpoints:
            self.warnings.append("⚠️ No endpoints defined in config")
            return

        # Test first 5 endpoints
        sample_size = min(5, len(endpoints))
        print(f"   Testing {sample_size} of {len(endpoints)} endpoints...")

        base_url = self.config['base_url']
        creds = self.config.get('credentials', {})

        # Build auth headers
        headers = {'Content-Type': 'application/json'}
        if 'jwt_token' in creds:
            headers['Authorization'] = f"Bearer {creds['jwt_token']}"

        failed_count = 0

        for endpoint in endpoints[:sample_size]:
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
                elif method == 'PUT':
                    payload = endpoint.get('payload', {})
                    resp = requests.put(url, json=payload, headers=headers, timeout=5)
                elif method == 'DELETE':
                    resp = requests.delete(url, headers=headers, timeout=5)
                else:
                    continue

                # Evaluate response
                if 200 <= resp.status_code < 300:
                    print(f"   ✓ {method} {path} → {resp.status_code}")
                elif resp.status_code == 401:
                    print(f"   ✗ {method} {path} → 401 Unauthorized")
                    self.issues.append(f"❌ {method} {path}: Authentication failed")
                    failed_count += 1
                elif resp.status_code == 404:
                    print(f"   ✗ {method} {path} → 404 Not Found")
                    self.warnings.append(f"⚠️ {method} {path}: Endpoint not found - check path")
                    failed_count += 1
                elif resp.status_code == 502:
                    print(f"   ✗ {method} {path} → 502 Bad Gateway")
                    self.issues.append(f"❌ {method} {path}: Backend service unavailable")
                    failed_count += 1
                elif resp.status_code == 400:
                    print(f"   ✗ {method} {path} → 400 Bad Request")
                    self.warnings.append(f"⚠️ {method} {path}: Invalid payload format")
                    failed_count += 1
                else:
                    print(f"   ✗ {method} {path} → {resp.status_code}")
                    self.warnings.append(f"⚠️ {method} {path}: Unexpected status {resp.status_code}")
                    failed_count += 1

            except requests.RequestException as e:
                print(f"   ✗ {method} {path} → Connection error")
                self.issues.append(f"❌ {method} {path}: {e}")
                failed_count += 1

        if failed_count == 0:
            self.successes.append(f"✅ All {sample_size} sampled endpoints working")
        elif failed_count < sample_size:
            self.warnings.append(
                f"⚠️ {failed_count}/{sample_size} sampled endpoints failed"
            )
        else:
            self.issues.append(
                f"❌ All {sample_size} sampled endpoints failed - check config"
            )

    def check_configuration_values(self):
        """Validate configuration values."""
        print("\n5️⃣  Checking Configuration Values...")

        load_profile = self.config.get('load_profile', {})

        # Check required fields
        if 'users' not in load_profile:
            self.issues.append("❌ Missing 'users' in load_profile")
        elif load_profile['users'] <= 0:
            self.issues.append("❌ 'users' must be > 0")
        else:
            print(f"   ✓ Users: {load_profile['users']}")

        if 'spawn_rate' not in load_profile:
            self.issues.append("❌ Missing 'spawn_rate' in load_profile")
        elif load_profile['spawn_rate'] <= 0:
            self.issues.append("❌ 'spawn_rate' must be > 0")
        else:
            print(f"   ✓ Spawn rate: {load_profile['spawn_rate']}/sec")

        if 'duration' not in load_profile:
            self.issues.append("❌ Missing 'duration' in load_profile")
        elif load_profile['duration'] <= 0:
            self.issues.append("❌ 'duration' must be > 0")
        else:
            print(f"   ✓ Duration: {load_profile['duration']}s ({load_profile['duration']/60:.1f} min)")

        # Check SLA thresholds
        sla = self.config.get('sla', {})
        if sla:
            print(f"   ✓ SLA thresholds defined")
            if 'p95_ms' in sla:
                print(f"     - P95: < {sla['p95_ms']}ms")
            if 'error_rate' in sla:
                print(f"     - Error rate: < {sla['error_rate']*100:.1f}%")

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 70)
        print("📊 VALIDATION SUMMARY")
        print("=" * 70)

        if self.successes:
            print(f"\n✅ Passed ({len(self.successes)}):")
            for success in self.successes:
                print(f"   {success}")

        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   {warning}")

        if self.issues:
            print(f"\n❌ Issues ({len(self.issues)}):")
            for issue in self.issues:
                print(f"   {issue}")

        print("\n" + "=" * 70)

        if self.issues:
            print("❌ VALIDATION FAILED")
            print("Fix the issues above before running performance tests.")
            print("\nRecommended actions:")
            if any("EXPIRED" in issue for issue in self.issues):
                print("  1. Refresh JWT token (current token expired)")
            if any("401" in issue for issue in self.issues):
                print("  2. Verify authentication credentials")
            if any("404" in issue for issue in self.issues):
                print("  3. Check endpoint paths (may have wrong prefix)")
            if any("502" in issue for issue in self.issues):
                print("  4. Verify backend services are running")
        else:
            print("✅ VALIDATION PASSED")
            print("Configuration is ready for performance testing.")
            print("\nNext steps:")
            print("  1. Run smoke test: perf-framework execute --users 5 --duration 60")
            print("  2. If smoke test passes, run full test")

        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='Validate API configuration before performance testing'
    )
    parser.add_argument(
        'config',
        nargs='?',
        default='config.json',
        help='Path to configuration file (default: config.json)'
    )
    parser.add_argument(
        '--config',
        dest='config_alt',
        help='Alternative way to specify config file'
    )

    args = parser.parse_args()
    config_file = args.config_alt or args.config

    try:
        validator = APIValidator(config_file)
        passed = validator.validate_all()

        sys.exit(0 if passed else 1)

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
