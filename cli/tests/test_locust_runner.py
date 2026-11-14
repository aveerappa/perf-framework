from pathlib import Path
from datetime import datetime
from perf_framework.locust_runner import LocustRunner, LocustResult
import pytest
import tempfile

def test_parse_results_csv():
    """Test parsing Locust results CSV file."""
    runner = LocustRunner()

    with tempfile.NamedTemporaryFile(mode='w', suffix='_stats.csv', delete=False) as f:
        f.write("""Type,Name,Request Count,Failure Count,Median Response Time,Average Response Time,Min Response Time,Max Response Time,50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%
GET,/api/orders,1000,5,180,195,45,890,180,220,280,320,420,450,650,890,890,890,890
""")
        csv_path = Path(f.name)

    try:
        stats = runner.parse_results_csv(csv_path)

        assert stats["p50"] == 180.0
        assert stats["p95"] == 450.0
        assert stats["p99"] == 890.0
        assert stats["error_rate"] == 0.5  # 5/1000 = 0.5%
    finally:
        csv_path.unlink()

def test_parse_results_detects_high_error_rate():
    """Test that high error rates are detected even with exit code 0 (Review Focus #3)."""
    runner = LocustRunner()

    with tempfile.NamedTemporaryFile(mode='w', suffix='_stats.csv', delete=False) as f:
        # 50% error rate
        f.write("""Type,Name,Request Count,Failure Count,Median Response Time,Average Response Time,Min Response Time,Max Response Time,50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%
GET,/api/orders,1000,500,180,195,45,890,180,220,280,320,420,450,650,890,890,890,890
""")
        csv_path = Path(f.name)

    try:
        stats = runner.parse_results_csv(csv_path)

        # Error rate should be accurately calculated from CSV, not exit code
        assert stats["error_rate"] == 50.0
    finally:
        csv_path.unlink()
