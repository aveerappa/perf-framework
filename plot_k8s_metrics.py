#!/usr/bin/env python3
"""
Plot Kubernetes metrics collected during load test
Generates charts showing CPU and Memory utilization over time
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path


def plot_k8s_metrics(csv_file, output_html='k8s_metrics_chart.html'):
    """Generate interactive charts from K8s metrics CSV"""

    print(f"📊 K8s Metrics Visualizer")
    print(f"=" * 70)
    print(f"Loading: {csv_file}")

    # Load CSV
    df = pd.read_csv(csv_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"✓ Loaded {len(df)} metric samples")
    print(f"✓ Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Get unique pods
    pods = df['pod'].unique()
    print(f"✓ Pods monitored: {len(pods)}")

    # Create subplots with more spacing
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('CPU Utilization (%)', 'Memory Utilization (%)'),
        vertical_spacing=0.20,  # Increased from 0.12 to 0.20 for more gap
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
    )

    # Color palette
    colors = ['#2E86DE', '#27AE60', '#F39C12', '#E74C3C', '#8E44AD', '#16A085']

    # Plot CPU for each pod
    for i, pod in enumerate(pods):
        pod_data = df[df['pod'] == pod]
        color = colors[i % len(colors)]

        fig.add_trace(
            go.Scatter(
                x=pod_data['timestamp'],
                y=pod_data['cpu_percent'],
                name=pod,
                line=dict(color=color, width=2),
                mode='lines',
                legendgroup=pod,  # Group by pod name so clicking legend affects both CPU and Memory
                showlegend=True
            ),
            row=1, col=1
        )

    # Add CPU threshold line (80%)
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color="red",
        annotation_text="80% threshold",
        row=1, col=1
    )

    # Plot Memory for each pod
    for i, pod in enumerate(pods):
        pod_data = df[df['pod'] == pod]
        color = colors[i % len(colors)]

        fig.add_trace(
            go.Scatter(
                x=pod_data['timestamp'],
                y=pod_data['memory_percent'],
                name=pod,
                line=dict(color=color, width=2),
                mode='lines',
                legendgroup=pod,  # Same legendgroup as CPU, so they toggle together
                showlegend=False  # Don't duplicate legend items
            ),
            row=2, col=1
        )

    # Add Memory threshold line (80%)
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color="red",
        annotation_text="80% threshold",
        row=2, col=1
    )

    # Update layout
    fig.update_xaxes(title_text="Time", row=1, col=1)
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="CPU %", row=1, col=1, range=[0, 100])
    fig.update_yaxes(title_text="Memory %", row=2, col=1, range=[0, 100])

    fig.update_layout(
        title='Kubernetes Resource Utilization During Load Test',
        hovermode='x unified',
        template='plotly_white',
        height=900,  # Increased height for better spacing
        showlegend=True
    )

    # Save to HTML
    fig.write_html(output_html)
    print(f"\n✅ Chart saved: {output_html}")

    # Calculate and print statistics
    print(f"\n📈 Statistics:")
    print(f"=" * 70)

    for pod in pods:
        pod_data = df[df['pod'] == pod]
        print(f"\n{pod}:")
        print(f"  CPU:    Avg={pod_data['cpu_percent'].mean():.1f}% | "
              f"Max={pod_data['cpu_percent'].max():.1f}% | "
              f"Min={pod_data['cpu_percent'].min():.1f}%")
        print(f"  Memory: Avg={pod_data['memory_percent'].mean():.1f}% | "
              f"Max={pod_data['memory_percent'].max():.1f}% | "
              f"Min={pod_data['memory_percent'].min():.1f}%")

    print(f"\n🌐 View chart:")
    print(f"   open {output_html}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python plot_k8s_metrics.py <metrics.csv>")
        sys.exit(1)

    csv_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'k8s_metrics_chart.html'

    plot_k8s_metrics(csv_file, output_file)
