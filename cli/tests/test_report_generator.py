from pathlib import Path
from perf_framework.report_generator import ReportGenerator
import tempfile

def test_generate_html_report():
    """Test generating HTML report from Locust and metrics data."""
    generator = ReportGenerator()

    locust_stats = {
        "p50": 180.0,
        "p95": 450.0,
        "p99": 890.0,
        "error_rate": 0.5,
        "requests_per_sec": 100.0
    }

    prometheus_data = {
        "cpu_usage": {
            "metric": "cpu_usage",
            "values": [(1731583800, 65.5), (1731583900, 70.2)]
        },
        "memory_usage": {
            "metric": "memory_bytes",
            "values": [(1731583800, 4200000000), (1731583900, 4400000000)]
        }
    }

    newrelic_data = [
        {
            "name": "POST /api/v1/orders",
            "duration_ms": 185.0,
            "database_ms": 80.0,
            "external_ms": 20.0
        }
    ]

    sla = {
        "p95_latency_ms": 500,
        "p99_latency_ms": 1000,
        "error_rate_percent": 1
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        output_path = Path(f.name)

    try:
        generator.generate(locust_stats, prometheus_data, newrelic_data, sla, output_path)

        assert output_path.exists()
        html_content = output_path.read_text()

        # Verify HTML structure
        assert "<html>" in html_content
        assert "Performance Test Report" in html_content
        assert "plotly" in html_content.lower()

        # Verify data present
        assert "450.0" in html_content  # p95 latency
        assert "PASS" in html_content or "FAIL" in html_content
        assert "CPU" in html_content
        assert "Database" in html_content
    finally:
        output_path.unlink()

def test_generate_report_with_missing_prometheus():
    """Test report generation gracefully handles missing Prometheus data (Review Focus #5)."""
    generator = ReportGenerator()

    locust_stats = {"p50": 180.0, "p95": 450.0, "p99": 890.0, "error_rate": 0.5, "requests_per_sec": 100.0}
    prometheus_data = {}
    newrelic_data = []
    sla = {"p95_latency_ms": 500, "p99_latency_ms": 1000, "error_rate_percent": 1}

    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        output_path = Path(f.name)

    try:
        generator.generate(locust_stats, prometheus_data, newrelic_data, sla, output_path)

        html_content = output_path.read_text()
        assert "450.0" in html_content
    finally:
        output_path.unlink()
