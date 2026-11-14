from datetime import datetime, timedelta
from perf_framework.prometheus_client import PrometheusClient, PrometheusQueryError
import pytest
from unittest.mock import Mock, patch

def test_query_range_success():
    """Test successful Prometheus range query."""
    client = PrometheusClient("http://prometheus.local:9090")
    start = datetime(2026, 11, 14, 10, 30, 0)
    end = datetime(2026, 11, 14, 10, 40, 0)

    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": "success",
            "data": {
                "result": [{
                    "metric": {"__name__": "cpu_usage"},
                    "values": [[1731583800, "65.5"], [1731583815, "70.2"]]
                }]
            }
        }

        result = client.query_range("cpu_usage", start, end)

        assert result["metric"] == "cpu_usage"
        assert len(result["values"]) == 2
        assert result["values"][0] == (1731583800, 65.5)

def test_query_range_with_labels():
    """Test range query with label filtering."""
    client = PrometheusClient("http://prometheus.local:9090")
    start = datetime(2026, 11, 14, 10, 30, 0)
    end = datetime(2026, 11, 14, 10, 40, 0)

    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": "success",
            "data": {
                "result": [{
                    "metric": {"__name__": "http_request_duration_seconds"},
                    "values": [[1731583800, "0.5"]]
                }]
            }
        }

        result = client.query_range(
            "http_request_duration_seconds",
            start, end,
            labels={"service": "orders-api", "method": "POST"}
        )

        # Verify labels included in query string
        call_args = mock_get.call_args
        query_param = call_args.kwargs['params']['query']
        assert 'service="orders-api"' in query_param
        assert 'method="POST"' in query_param

def test_query_range_prometheus_error():
    """Test handling of Prometheus API errors."""
    client = PrometheusClient("http://prometheus.local:9090")
    start = datetime(2026, 11, 14, 10, 30, 0)
    end = datetime(2026, 11, 14, 10, 40, 0)

    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 500

        with pytest.raises(PrometheusQueryError, match="Prometheus query failed"):
            client.query_range("cpu_usage", start, end)

def test_query_range_midnight_boundary():
    """Test range query across midnight correctly handles timezone."""
    client = PrometheusClient("http://prometheus.local:9090")
    # 23:55 to 00:05 next day
    start = datetime(2026, 11, 14, 23, 55, 0)
    end = datetime(2026, 11, 15, 0, 5, 0)

    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": "success",
            "data": {
                "result": [{
                    "metric": {"__name__": "cpu_usage"},
                    "values": [[1731630900, "50.0"]]
                }]
            }
        }

        result = client.query_range("cpu_usage", start, end)

        # Verify query params use Unix timestamps (timezone-agnostic)
        call_args = mock_get.call_args
        start_ts = call_args.kwargs['params']['start']
        end_ts = call_args.kwargs['params']['end']
        assert isinstance(start_ts, (int, float))
        assert end_ts > start_ts
