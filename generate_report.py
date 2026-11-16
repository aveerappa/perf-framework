#!/usr/bin/env python3
"""Generate HTML performance test report with Plotly charts."""

import pandas as pd
import json
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys

def generate_report(run_dir_path):
    run_dir = Path(run_dir_path)

    # Load config
    with open(run_dir / "config.json") as f:
        config = json.load(f)

    # Load stats
    stats = pd.read_csv(run_dir / "results/stats_stats.csv")
    history = pd.read_csv(run_dir / "results/stats_stats_history.csv")
    failures = pd.read_csv(run_dir / "results/stats_failures.csv")

    # Get aggregated stats
    agg_row = stats[stats['Name'] == 'Aggregated']
    if len(agg_row) == 0:
        total_requests = int(stats['Request Count'].sum())
        total_failures = int(stats['Failure Count'].sum())
        p50 = stats['50%'].median()
        p95 = stats['95%'].median()
        p99 = stats['99%'].median()
        avg_rps = stats['Requests/s'].mean()
    else:
        agg = agg_row.iloc[0]
        total_requests = int(agg['Request Count'])
        total_failures = int(agg['Failure Count'])
        p50 = agg['50%']
        p95 = agg['95%']
        p99 = agg['99%']
        avg_rps = agg['Requests/s']

    error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0

    # SLA evaluation
    sla = config.get('sla', {})
    p95_threshold = sla.get('p95_latency_ms', 500)
    error_threshold = sla.get('error_rate_percent', 1.0)
    p95_pass = p95 <= p95_threshold
    error_pass = error_rate <= error_threshold
    overall_pass = p95_pass and error_pass

    # Create charts
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=('Response Time Over Time', 'Requests Per Second',
                        'Error Rate Over Time', 'User Count',
                        'Request Distribution', 'K8s Resource Usage'),
        specs=[[{}, {}],
               [{}, {}],
               [{"type": "bar"}, {}]]
    )

    # Filter history to only Aggregated rows
    hist_agg = history[history['Name'] == 'Aggregated']

    # Chart 1: Response Time
    fig.add_trace(go.Scatter(x=list(range(len(hist_agg))), y=hist_agg['50%'],
                             name='p50', line=dict(color='blue')), row=1, col=1)
    fig.add_trace(go.Scatter(x=list(range(len(hist_agg))), y=hist_agg['95%'],
                             name='p95', line=dict(color='orange')), row=1, col=1)
    fig.add_trace(go.Scatter(x=list(range(len(hist_agg))), y=hist_agg['99%'],
                             name='p99', line=dict(color='red')), row=1, col=1)
    fig.add_hline(y=p95_threshold, line_dash="dash", line_color="red",
                  annotation_text=f"SLA: {p95_threshold}ms", row=1, col=1)

    # Chart 2: RPS
    fig.add_trace(go.Scatter(x=list(range(len(hist_agg))), y=hist_agg['Requests/s'],
                             fill='tozeroy', name='RPS'), row=1, col=2)

    # Chart 3: Error Rate
    error_pct = (hist_agg['Failures/s'] / hist_agg['Requests/s'] * 100).fillna(0)
    fig.add_trace(go.Scatter(x=list(range(len(hist_agg))), y=error_pct,
                             name='Error %', line=dict(color='red')), row=2, col=1)
    fig.add_hline(y=error_threshold, line_dash="dash", line_color="red",
                  annotation_text=f"SLA: {error_threshold}%", row=2, col=1)

    # Chart 4: User Count
    fig.add_trace(go.Scatter(x=list(range(len(hist_agg))), y=hist_agg['User Count'],
                             fill='tozeroy', name='Users'), row=2, col=2)

    # Chart 5: Request Distribution by endpoint
    endpoint_stats = stats[stats['Name'] != 'Aggregated']
    fig.add_trace(go.Bar(x=endpoint_stats['Name'], y=endpoint_stats['Request Count'],
                         name='Requests'), row=3, col=1)

    # Chart 6: K8s metrics if available
    k8s_file = run_dir / "k8s_metrics.csv"
    if k8s_file.exists():
        k8s_df = pd.read_csv(k8s_file)
        for service in k8s_df['service'].unique():
            svc_data = k8s_df[k8s_df['service'] == service]
            fig.add_trace(go.Scatter(x=list(range(len(svc_data))), y=svc_data['cpu_percent'],
                                     name=f'{service} CPU%'), row=3, col=2)

    fig.update_xaxes(title_text="Time (s)", row=1, col=1)
    fig.update_xaxes(title_text="Time (s)", row=1, col=2)
    fig.update_xaxes(title_text="Time (s)", row=2, col=1)
    fig.update_xaxes(title_text="Time (s)", row=2, col=2)
    fig.update_xaxes(title_text="Endpoint", row=3, col=1)
    fig.update_xaxes(title_text="Sample", row=3, col=2)

    fig.update_yaxes(title_text="Latency (ms)", row=1, col=1)
    fig.update_yaxes(title_text="RPS", row=1, col=2)
    fig.update_yaxes(title_text="Error %", row=2, col=1)
    fig.update_yaxes(title_text="Users", row=2, col=2)
    fig.update_yaxes(title_text="Requests", row=3, col=1)
    fig.update_yaxes(title_text="CPU %", row=3, col=2)

    fig.update_layout(height=1200, showlegend=True, title_text="Performance Test Results")

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Performance Test Report - {run_dir.name}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        h1 {{ color: #333; }}
        .summary {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .pass {{ color: green; font-weight: bold; }}
        .fail {{ color: red; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; background: white; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .metric-box {{ display: inline-block; padding: 15px; margin: 10px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); min-width: 150px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
        .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
    </style>
</head>
<body>
    <h1>🎯 Performance Test Report</h1>

    <div class="summary">
        <h2>Executive Summary</h2>
        <p><strong>Run ID:</strong> {run_dir.name}</p>
        <p><strong>Service:</strong> {config['service_name']}</p>
        <p><strong>Base URL:</strong> {config['base_url']}</p>
        <p><strong>Test Duration:</strong> ~{len(hist_agg)}s (planned: {config['load_profile']['duration']}s)</p>
        <p><strong>Load Profile:</strong> {config['load_profile']['users']} users @ {config['load_profile']['spawn_rate']}/s spawn rate</p>
        <p><strong>Overall Result:</strong> <span class="{'pass' if overall_pass else 'fail'}">{'✅ PASS' if overall_pass else '❌ FAIL'}</span></p>
    </div>

    <div class="summary">
        <h2>Key Metrics</h2>
        <div class="metric-box">
            <div class="metric-label">Total Requests</div>
            <div class="metric-value">{total_requests:,}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Failures</div>
            <div class="metric-value" style="color: {'green' if error_pass else 'red'}">{total_failures}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Error Rate</div>
            <div class="metric-value" style="color: {'green' if error_pass else 'red'}">{error_rate:.2f}%</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Avg RPS</div>
            <div class="metric-value">{avg_rps:.1f}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">p50 Latency</div>
            <div class="metric-value">{p50:.0f}ms</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">p95 Latency</div>
            <div class="metric-value" style="color: {'green' if p95_pass else 'red'}">{p95:.0f}ms</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">p99 Latency</div>
            <div class="metric-value">{p99:.0f}ms</div>
        </div>
    </div>

    <div class="summary">
        <h2>SLA Compliance</h2>
        <table>
            <tr><th>Metric</th><th>Actual</th><th>Threshold</th><th>Status</th></tr>
            <tr>
                <td>p95 Latency</td>
                <td>{p95:.0f}ms</td>
                <td>&lt; {p95_threshold}ms</td>
                <td class="{'pass' if p95_pass else 'fail'}">{'✅ PASS' if p95_pass else '❌ FAIL'}</td>
            </tr>
            <tr>
                <td>Error Rate</td>
                <td>{error_rate:.2f}%</td>
                <td>&lt; {error_threshold}%</td>
                <td class="{'pass' if error_pass else 'fail'}">{'✅ PASS' if error_pass else '❌ FAIL'}</td>
            </tr>
        </table>
    </div>

    {fig.to_html(full_html=False, include_plotlyjs='cdn')}

    {'<div class="summary"><h2>⚠️ Failures</h2>' + failures.to_html(index=False) + '</div>' if total_failures > 0 else ''}

</body>
</html>
"""

    # Save report
    report_path = run_dir / "PERFORMANCE_REPORT.html"
    report_path.write_text(html)
    print(f"✅ Report generated: {report_path}")
    return str(report_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: generate_report.py <run-directory>")
        sys.exit(1)

    report_path = generate_report(sys.argv[1])
    print(f"\nOpen report: open {report_path}")
