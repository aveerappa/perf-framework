#!/usr/bin/env python3
"""
Plot Kubernetes metrics with separate chart per service
Generates individual HTML files for each service
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path


def plot_service_metrics(df, service_name, colors, output_html):
    """Generate side-by-side CPU/Memory chart for a single service"""

    service_data = df[df['service'] == service_name]
    pods = sorted(service_data['pod'].unique())

    print(f"\n{service_name}:")
    print(f"  Pods: {len(pods)}")

    # Create subplot: 2 rows, 2 columns
    # Row 1: CPU (left) | Memory (right)
    # Row 2: Pod Count (full width)
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            f'CPU Utilization (%)',
            f'Memory Utilization (%)',
            f'Pod Count Over Time',
            None
        ],
        horizontal_spacing=0.10,
        vertical_spacing=0.15,
        specs=[
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"colspan": 2, "secondary_y": False}, None]
        ]
    )

    # Add traces for each pod
    for pod_idx, pod in enumerate(pods):
        pod_data = service_data[service_data['pod'] == pod].sort_values('timestamp')
        color = colors[pod_idx % len(colors)]

        # Shortened pod name
        pod_suffix = pod.split('-')[-2] + '-' + pod.split('-')[-1] if len(pod.split('-')) > 1 else pod

        # CPU trace (column 1)
        fig.add_trace(
            go.Scatter(
                x=pod_data['timestamp'],
                y=pod_data['cpu_percent'],
                name=pod_suffix,
                line=dict(color=color, width=2),
                mode='lines',
                legendgroup=f'{service_name}-{pod}',
                showlegend=True,
                hovertemplate=f'<b>{pod_suffix}</b><br>CPU: %{{y:.1f}}%<br>%{{x}}<extra></extra>'
            ),
            row=1, col=1
        )

        # Memory trace (column 2)
        fig.add_trace(
            go.Scatter(
                x=pod_data['timestamp'],
                y=pod_data['memory_percent'],
                name=pod_suffix,
                line=dict(color=color, width=2),
                mode='lines',
                legendgroup=f'{service_name}-{pod}',
                showlegend=False,  # Don't duplicate legend
                hovertemplate=f'<b>{pod_suffix}</b><br>Memory: %{{y:.1f}}%<br>%{{x}}<extra></extra>'
            ),
            row=1, col=2
        )

        print(f"  - {pod_suffix}: CPU avg={pod_data['cpu_percent'].mean():.1f}%, Memory avg={pod_data['memory_percent'].mean():.1f}%")

    # Calculate pod count over time
    pod_counts = service_data.groupby('timestamp').size().reset_index(name='count')
    pod_counts = pod_counts.sort_values('timestamp')

    # Add pod count trace (row 2, spans both columns)
    fig.add_trace(
        go.Scatter(
            x=pod_counts['timestamp'],
            y=pod_counts['count'],
            name='Pod Count',
            line=dict(color='#0066CC', width=3),
            fill='tozeroy',
            mode='lines',
            showlegend=False,
            hovertemplate='<b>Pod Count</b><br>Count: %{y}<br>%{x}<extra></extra>'
        ),
        row=2, col=1
    )

    # Add 80% threshold lines for CPU and Memory
    fig.add_hline(y=80, line_dash='dash', line_color='red', line_width=1.5,
                 row=1, col=1, annotation_text='80%', annotation_position='right')
    fig.add_hline(y=80, line_dash='dash', line_color='red', line_width=1.5,
                 row=1, col=2, annotation_text='80%', annotation_position='right')

    # Update axes
    fig.update_xaxes(title_text='Time', row=1, col=1)
    fig.update_yaxes(title_text='CPU %', row=1, col=1, range=[0, 100])
    fig.update_xaxes(title_text='Time', row=1, col=2)
    fig.update_yaxes(title_text='Memory %', row=1, col=2, range=[0, 100])

    # Pod count axes
    fig.update_xaxes(title_text='Time', row=2, col=1)
    fig.update_yaxes(title_text='Pod Count', row=2, col=1, range=[0, max(pod_counts['count']) + 1])

    # Update layout
    fig.update_layout(
        title=f'{service_name} - Resource Utilization',
        hovermode='x unified',
        template='plotly_white',
        height=700,  # Increased height for 2 rows
        showlegend=True,
        legend=dict(
            title=dict(text=f"<b>Pods</b>"),
            orientation='v',
            yanchor='top',
            y=0.98,
            xanchor='left',
            x=1.02,
            bgcolor='rgba(255,255,255,0.95)',
            bordercolor='#BDC3C7',
            borderwidth=1
        )
    )

    # Save to HTML
    fig.write_html(output_html)
    print(f"  ✓ Chart saved: {output_html}")


def plot_k8s_metrics_individual(csv_file, output_dir='.'):
    """Generate separate charts for each service"""

    print(f"📊 K8s Metrics Visualizer (Individual Service Charts)")
    print(f"=" * 70)
    print(f"Loading: {csv_file}")

    # Load CSV
    df = pd.read_csv(csv_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"✓ Loaded {len(df)} metric samples")

    # Check if multi-service
    if 'service' not in df.columns:
        print("✗ No service column found")
        return

    services = sorted(df['service'].unique())
    print(f"✓ Services: {', '.join(services)}")

    # Color palette
    colors = ['#2E86DE', '#27AE60', '#F39C12', '#E74C3C', '#8E44AD', '#16A085']

    # Create output directory if needed
    output_path = Path(output_dir)

    # Generate chart for each service
    for service in services:
        output_file = output_path / f'k8s_metrics_{service}.html'
        plot_service_metrics(df, service, colors, output_file)

    print(f"\n✅ All charts generated!")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python plot_k8s_metrics_individual.py <metrics.csv> [output_dir]")
        sys.exit(1)

    csv_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'

    plot_k8s_metrics_individual(csv_file, output_dir)
