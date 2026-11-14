from datetime import datetime
from perf_framework.newrelic_client import NewRelicClient, NewRelicQueryError
import pytest
from unittest.mock import patch

def test_query_nrql_success():
    """Test successful NRQL query execution."""
    client = NewRelicClient(api_key="test-key", account_id="12345")

    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "data": {
                "actor": {
                    "account": {
                        "nrql": {
                            "results": [
                                {"average_duration": 180.5, "count": 1500}
                            ]
                        }
                    }
                }
            }
        }

        result = client.query_nrql("SELECT average(duration) FROM Transaction")

        assert result["results"][0]["average_duration"] == 180.5
        assert mock_post.call_args.kwargs['headers']['Api-Key'] == "test-key"

def test_get_transaction_traces():
    """Test fetching transaction traces for time window."""
    client = NewRelicClient(api_key="test-key", account_id="12345")
    start = datetime(2026, 11, 14, 10, 30, 0)
    end = datetime(2026, 11, 14, 10, 40, 0)

    with patch.object(client, 'query_nrql') as mock_query:
        mock_query.return_value = {
            "results": [
                {
                    "name": "POST /api/v1/orders",
                    "duration": 0.185,
                    "databaseDuration": 0.080,
                    "externalDuration": 0.020
                }
            ]
        }

        traces = client.get_transaction_traces("orders-api", start, end)

        assert len(traces) == 1
        assert traces[0]["name"] == "POST /api/v1/orders"
        assert traces[0]["duration_ms"] == 185.0
        assert traces[0]["database_ms"] == 80.0
        assert traces[0]["external_ms"] == 20.0

def test_query_nrql_auth_error():
    """Test handling of New Relic authentication failures."""
    client = NewRelicClient(api_key="invalid-key", account_id="12345")

    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 403

        with pytest.raises(NewRelicQueryError, match="Authentication failed"):
            client.query_nrql("SELECT * FROM Transaction")
