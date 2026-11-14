from datetime import datetime
import requests


class NewRelicQueryError(Exception):
    """Raised when New Relic query fails."""
    pass


class NewRelicClient:
    """Client for querying New Relic NerdGraph API."""

    def __init__(self, api_key: str, account_id: str):
        """
        Initialize New Relic client.

        Args:
            api_key: New Relic API key
            account_id: New Relic account ID
        """
        self.api_key = api_key
        self.account_id = account_id
        self.base_url = "https://api.newrelic.com/graphql"

    def query_nrql(self, query: str, timeout: int = 30) -> dict:
        """
        Execute NRQL query against New Relic.

        Args:
            query: NRQL query string
            timeout: Request timeout in seconds

        Returns:
            dict with query results

        Raises:
            NewRelicQueryError: If query fails
        """
        headers = {
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        }

        # Build NerdGraph query
        graphql_query = f"""
        {{
          actor {{
            account(id: {self.account_id}) {{
              nrql(query: "{query}") {{
                results
              }}
            }}
          }}
        }}
        """

        payload = {"query": graphql_query}

        response = requests.post(
            self.base_url,
            json=payload,
            headers=headers,
            timeout=timeout
        )

        if response.status_code == 403:
            raise NewRelicQueryError("Authentication failed: Invalid API key")

        if response.status_code != 200:
            raise NewRelicQueryError(
                f"New Relic query failed: HTTP {response.status_code}"
            )

        data = response.json()

        # Extract results from GraphQL response
        try:
            results = data["data"]["actor"]["account"]["nrql"]["results"]
            return {"results": results}
        except (KeyError, TypeError) as e:
            raise NewRelicQueryError(f"Invalid response format: {e}")

    def get_transaction_traces(
        self,
        app_name: str,
        start: datetime,
        end: datetime
    ) -> list[dict]:
        """
        Get transaction traces for application in time window.

        Args:
            app_name: Application name in New Relic
            start: Start time
            end: End time

        Returns:
            list of dicts with name, duration_ms, database_ms, external_ms
        """
        # Convert datetime to NRQL SINCE/UNTIL format
        start_ts = int(start.timestamp())
        end_ts = int(end.timestamp())

        query = f"""
        SELECT name, duration, databaseDuration, externalDuration
        FROM Transaction
        WHERE appName='{app_name}'
        SINCE {start_ts} UNTIL {end_ts}
        """

        result = self.query_nrql(query)

        # Convert seconds to milliseconds
        traces = []
        for item in result["results"]:
            traces.append({
                "name": item["name"],
                "duration_ms": item["duration"] * 1000,
                "database_ms": item.get("databaseDuration", 0) * 1000,
                "external_ms": item.get("externalDuration", 0) * 1000
            })

        return traces
