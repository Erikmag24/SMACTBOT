import plotly.graph_objects as go
import pandas as pd
import numpy as np
import io
from PIL import Image
import warnings
from influxdb_client.client.warnings import MissingPivotFunction

# Suppress specific warning
warnings.simplefilter("ignore", MissingPivotFunction)

def create_graph(data_frame, title, metric_name, current_value, 
                 chart_type='line', show_trendline=False, 
                 additional_metrics=None, highlight_threshold=None):
    """
    Creates an enhanced graph from a Pandas DataFrame using Plotly, supporting multiple chart types.

    Parameters:
    - data_frame (pd.DataFrame): DataFrame containing '_time' and '_value' columns.
    - title (str): Title of the graph.
    - metric_name (str): Name of the metric for the graph.
    - current_value (float): Current value of the metric to annotate.
    - chart_type (str): Type of chart to display ('line', 'bar', 'scatter'). Default is 'line'.
    - show_trendline (bool): Option to display a trendline (only applicable for 'line' and 'scatter').
    - additional_metrics (list of tuples): List containing tuples with DataFrame and metric names for additional lines.
    - highlight_threshold (float): Value above which data points will be highlighted.
    
    Returns:
    - PIL.Image: An image object of the graph.
    """
    # Ensure chart_type is in lowercase
    chart_type = chart_type.lower()
    
    # Validate chart_type
    valid_chart_types = ['line', 'bar', 'scatter']
    if chart_type not in valid_chart_types:
        raise ValueError(f"Unknown chart type '{chart_type}'. Please use one of {valid_chart_types}.")
    
    # Check for empty DataFrame
    if data_frame.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available for this metric.",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20, color="red"),
            xref="paper", yref="paper"
        )
    else:
        # Convert _time to datetime format if it's not already
        if not pd.api.types.is_datetime64_any_dtype(data_frame['_time']):
            data_frame['_time'] = pd.to_datetime(data_frame['_time'])

        # Convert _value to float
        data_frame['_value'] = pd.to_numeric(data_frame['_value'], errors='coerce').fillna(0)

        # Initialize figure
        fig = go.Figure()

        # Define marker size and color based on highlight_threshold
        marker_sizes = [10 if highlight_threshold and val > highlight_threshold else 6 for val in data_frame['_value']]
        marker_colors = ['#FF6347' if highlight_threshold and val > highlight_threshold else '#0048BA' for val in data_frame['_value']]

        # Add main trace based on chart type
        if chart_type == 'line':
            fig.add_trace(go.Scatter(
                x=data_frame['_time'],
                y=data_frame['_value'],
                mode='lines+markers',
                name=metric_name,
                line=dict(color='#0048BA', width=2.5),
                marker=dict(size=marker_sizes, color=marker_colors)
            ))
        elif chart_type == 'bar':
            fig.add_trace(go.Bar(
                x=data_frame['_time'],
                y=data_frame['_value'],
                name=metric_name,
                marker=dict(color=marker_colors)
            ))
        elif chart_type == 'scatter':
            fig.add_trace(go.Scatter(
                x=data_frame['_time'],
                y=data_frame['_value'],
                mode='markers',
                name=metric_name,
                marker=dict(size=marker_sizes, color=marker_colors, symbol='circle')
            ))

        # Add trendline if option is selected and applicable
        if show_trendline and chart_type in ['line', 'scatter']:
            trendline = data_frame['_value'].rolling(window=5).mean()  # 5-point moving average
            fig.add_trace(go.Scatter(
                x=data_frame['_time'],
                y=trendline,
                mode='lines',
                name=f'{metric_name} Trendline',
                line=dict(color='rgba(0, 72, 186, 0.5)', dash='dash', width=2)
            ))

        # Add additional metrics if provided
        if additional_metrics:
            for df, name in additional_metrics:
                # Ensure datetime conversion for additional DataFrame
                if not pd.api.types.is_datetime64_any_dtype(df['_time']):
                    df['_time'] = pd.to_datetime(df['_time'])
                df['_value'] = pd.to_numeric(df['_value'], errors='coerce').fillna(0)
                
                fig.add_trace(go.Scatter(
                    x=df['_time'],
                    y=df['_value'],
                    mode='lines+markers',
                    name=name,
                    line=dict(width=2.5),
                    marker=dict(size=8)
                ))

        # Highlight specific date
        important_date = pd.Timestamp('2024-04-15')
        if important_date in data_frame['_time'].values:
            important_value = data_frame.loc[data_frame['_time'] == important_date, '_value'].values[0]
            fig.add_trace(go.Scatter(
                x=[important_date],
                y=[important_value],
                mode='markers+text',
                marker=dict(size=12, color='red'),
                text=['Important Event'],
                textposition='bottom center',
                name='Event Marker'
            ))

        # Update layout for enhanced visual appeal
        fig.update_layout(
            title={'text': title, 'x':0.5, 'xanchor': 'center'},
            xaxis=dict(
                title='Time',
                showgrid=True,
                gridcolor='rgba(0, 0, 0, 0.1)',
                zeroline=False,
                tickformat='%b %d, %Y',
                rangeselector=dict(
                    buttons=list([
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(count=6, label="6m", step="month", stepmode="backward"),
                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                        dict(count=1, label="1y", step="year", stepmode="backward"),
                        dict(step="all")
                    ])
                ),
                rangeslider=dict(visible=True),
                type="date"
            ),
            yaxis=dict(
                title='Value',
                showgrid=True,
                gridcolor='rgba(0, 0, 0, 0.1)',
                zeroline=False,
            ),
            template='plotly_white',
            plot_bgcolor='rgba(255,255,255,1)',
            paper_bgcolor='rgba(255,255,255,1)',
            font=dict(color="black"),
            hovermode='x unified',
            legend=dict(
                x=0.01, y=1.2, orientation="h",
                bgcolor='rgba(255,255,255,1)',
                font=dict(size=10, color='black')
            )
        )

        # Add annotation for current value
        fig.add_annotation(
            x=data_frame['_time'].iloc[-1], y=current_value,
            text=f"Current Value: {current_value:.2f}",
            showarrow=True,
            arrowhead=1,
            ax=0, ay=-40,
            font=dict(color="#0048BA", size=12),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#0048BA",
            borderwidth=1
        )

        # Add interactive hover text
        fig.update_traces(
            hovertemplate=(
                "<b>Date:</b> %{x|%Y-%m-%d}<br>"
                "<b>Value:</b> %{y:.2f}<br>"
                "<b>Additional Info:</b> %{customdata[0]}"
            ),
            customdata=np.stack((data_frame['_value'].cumsum(),), axis=-1)
        )

    # Convert to image and return
    buffer = io.BytesIO()
    fig.write_image(buffer, format='PNG')
    buffer.seek(0)
    return Image.open(buffer)
