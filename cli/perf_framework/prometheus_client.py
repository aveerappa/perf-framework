from datetime import datetime
import requests


class PrometheusQueryError(Exception):
    """Raised when Prometheus query fails."""
    pass


class PrometheusClient:
    """Client for querying Prometheus HTTP API."""

    def __init__(self, base_url: str):
        """
        Initialize Prometheus client.

        Args:
            base_url: Prometheus server URL (e.g., http://prometheus.local:9090)
        """
        self.base_url = base_url.rstrip('/')

    def query_range(
        self,
        metric: str,
        start: datetime,
        end: datetime,
        step: str = "15s",
        labels: dict = None
    ) -> dict:
        """
        Query Prometheus for metric values over a time range.

        Args:
            metric: Metric name to query
            start: Start time for the range
            end: End time for the range
            step: Query resolution (default: 15s)
            labels: Optional label filters (e.g., {"service": "api", "method": "POST"})

        Returns:
            dict with "metric" (str) and "values" (list of (timestamp, value) tuples)

        Raises:
            PrometheusQueryError: If query fails
        """
        # Build PromQL query with labels
        query = metric
        if labels:
            label_filters = ','.join([f'{k}="{v}"' for k, v in labels.items()])
            query = f"{metric}{{{label_filters}}}"

        # Convert datetime to Unix timestamps
        start_ts = int(start.timestamp())
        end_ts = int(end.timestamp())

        # Make API request
        url = f"{self.base_url}/api/v1/query_range"
        params = {
            "query": query,
            "start": start_ts,
            "end": end_ts,
            "step": step
        }

        response = requests.get(url, params=params)

        if response.status_code != 200:
            raise PrometheusQueryError(
                f"Prometheus query failed: HTTP {response.status_code}"
            )

        data = response.json()

        if data.get("status") != "success":
            raise PrometheusQueryError(
                f"Prometheus query failed: {data.get('error', 'Unknown error')}"
            )

        # Extract result
        result = data["data"]["result"]
        if not result:
            return {"metric": metric, "values": []}

        # Parse first result series
        series = result[0]
        metric_name = series["metric"].get("__name__", metric)
        values = [(int(ts), float(val)) for ts, val in series["values"]]

        return {"metric": metric_name, "values": values}
