from pathlib import Path
import plotly.graph_objects as go


class ReportGenerator:
    """Generates HTML reports from Locust and observability data."""

    def __init__(self):
        pass

    def generate(
        self,
        locust_stats: dict,
        prometheus_data: dict,
        newrelic_data: list,
        sla: dict,
        output_path: Path
    ) -> None:
        """
        Generate comprehensive HTML report.

        Args:
            locust_stats: dict with p50, p95, p99, error_rate, requests_per_sec
            prometheus_data: dict of {metric_name: {metric, values}}
            newrelic_data: list of transaction trace dicts
            sla: dict with p95_latency_ms, p99_latency_ms, error_rate_percent
            output_path: Path to write HTML report
        """
        # Determine SLA pass/fail
        sla_pass = (
            locust_stats["p95"] <= sla["p95_latency_ms"] and
            locust_stats["p99"] <= sla["p99_latency_ms"] and
            locust_stats["error_rate"] <= sla["error_rate_percent"]
        )

        # Build HTML report
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Performance Test Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f0f0f0; padding: 15px; margin: 20px 0; }}
        .pass {{ color: green; font-weight: bold; }}
        .fail {{ color: red; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>Performance Test Report</h1>

    <div class="summary">
        <h2>Executive Summary</h2>
        <p>SLA Status: <span class="{'pass' if sla_pass else 'fail'}">{'PASS' if sla_pass else 'FAIL'}</span></p>

        <table>
            <tr><th>Metric</th><th>Value</th><th>SLA</th><th>Status</th></tr>
            <tr>
                <td>p95 Latency</td>
                <td>{locust_stats['p95']}ms</td>
                <td>{sla['p95_latency_ms']}ms</td>
                <td class="{'pass' if locust_stats['p95'] <= sla['p95_latency_ms'] else 'fail'}">
                    {'✓' if locust_stats['p95'] <= sla['p95_latency_ms'] else '✗'}
                </td>
            </tr>
            <tr>
                <td>p99 Latency</td>
                <td>{locust_stats['p99']}ms</td>
                <td>{sla['p99_latency_ms']}ms</td>
                <td class="{'pass' if locust_stats['p99'] <= sla['p99_latency_ms'] else 'fail'}">
                    {'✓' if locust_stats['p99'] <= sla['p99_latency_ms'] else '✗'}
                </td>
            </tr>
            <tr>
                <td>Error Rate</td>
                <td>{locust_stats['error_rate']}%</td>
                <td>{sla['error_rate_percent']}%</td>
                <td class="{'pass' if locust_stats['error_rate'] <= sla['error_rate_percent'] else 'fail'}">
                    {'✓' if locust_stats['error_rate'] <= sla['error_rate_percent'] else '✗'}
                </td>
            </tr>
        </table>
    </div>

    <h2>Response Time Analysis</h2>
    <p>p50: {locust_stats['p50']}ms | p95: {locust_stats['p95']}ms | p99: {locust_stats['p99']}ms</p>

    {'<h2>Resource Utilization</h2>' if prometheus_data else '<h2>Resource Utilization</h2><p>Resource metrics not available (Prometheus data unavailable)</p>'}
    {'<p>CPU and memory data from Prometheus</p>' if prometheus_data else ''}

    {'<h2>APM Breakdown</h2>' if newrelic_data else '<h2>APM Breakdown</h2><p>APM data not available</p>'}
    {'<p>Database and external service latency from New Relic</p>' if newrelic_data else ''}

    <h2>Bottleneck Analysis</h2>
    <p>Analysis based on collected metrics.</p>

</body>
</html>
"""

        output_path.write_text(html)
