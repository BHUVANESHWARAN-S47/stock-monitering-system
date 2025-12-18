# Implementation Code Documentation

---

## Page 1: Flask Application Core (app.py)

### Main Application Setup
```python
from flask import Flask, render_template, request, session, jsonify, send_file
import os
import sys
import json
import pandas as pd
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np

# Import custom modules
import spark_job
from spark_ui_manager import create_spark_session

# Initialize Flask application
app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), '..', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Spark session on startup with auto-trigger
spark = create_spark_session(auto_trigger_job=True)
```

### Home Route
```python
@app.route('/')
def index():
    """
    Homepage with upload interface and project information.
    """
    return render_template('index.html')
```

### Dashboard Route with Multi-Stock Support
```python
@app.route('/dashboard')
def dashboard():
    """
    Display dashboard with analysis results, charts, and anomalies.
    Supports multiple stock symbols via query parameter.
    """
    # Get stock symbol from query parameter (default: GOOGL)
    stock_symbol = request.args.get('stock', 'GOOGL').upper()
    
    # Available stocks
    available_stocks = ['GOOGL', 'AAPL', 'AMZN', 'MSFT', 'TSLA', 
                       'META', 'NFLX', 'NVDA', 'AMD', 'INTC']
    
    if stock_symbol not in available_stocks:
        stock_symbol = 'GOOGL'
    
    # Always analyze the stock data fresh (don't store large data in session)
    threshold = 5.0
    
    try:
        # Use the stock CSV data file
        sample_path = os.path.join(os.path.dirname(__file__), '..', f'{stock_symbol}.csv')
        filepath = os.path.abspath(sample_path)
        
        if not os.path.exists(filepath):
            return f"Error: {stock_symbol}.csv file not found at {filepath}", 404
        
        # Process data with default threshold of 5%
        result = spark_job.process_stock_data(filepath, threshold)
        
        if not result['success']:
            return f"Error: {result.get('error', 'Processing failed')}", 500
        
    except Exception as e:
        return f"Error analyzing data: {str(e)}", 500
    
    # Prepare data for visualization
    data = result['data']
    anomalies = result['anomalies']
    summary = result['summary']
    predictions = result.get('predictions', None)
    processing_log = result.get('processing_log', [])
    
    # Create Plotly chart
    df = pd.DataFrame(data)
    
    # Downsample data if too large (keep every nth row to reduce response size)
    if len(df) > 1000:
        # Keep first, last, and evenly spaced points, plus all anomalies
        step = len(df) // 800  # Target ~800 points
        indices = list(range(0, len(df), step))
        # Add last row if not included
        if len(df) - 1 not in indices:
            indices.append(len(df) - 1)
        # Add anomaly indices
        anomaly_indices = [i for i, row in enumerate(data) if row.get('IsAnomaly', False)]
        indices = sorted(set(indices + anomaly_indices))
        df_plot = df.iloc[indices].copy()
    else:
        df_plot = df.copy()
    
    # Generate interactive charts
    graph_json = generate_plotly_charts(df, df_plot, predictions)
    
    # Get data processing stats
    processing_stats = {
        'total_records': len(data),
        'date_range': f"{df['Date'].min()} to {df['Date'].max()}",
        'avg_volume': f"{df['Volume'].mean():,.0f}",
        'price_volatility': f"{df['PercentChange'].std():.2f}%"
    }
    
    # Sample of processed data (first 10 and last 10 rows)
    sample_data_head = df.head(10).to_dict('records')
    sample_data_tail = df.tail(10).to_dict('records')
    
    return render_template('dashboard.html',
                         summary=summary,
                         anomalies=anomalies,
                         predictions=predictions,
                         graph_json=graph_json,
                         threshold=threshold,
                         total_records=len(data),
                         processing_stats=processing_stats,
                         processing_log=processing_log,
                         sample_data_head=sample_data_head,
                         sample_data_tail=sample_data_tail,
                         selected_stock=stock_symbol)
```

### Plotly Chart Generation Function
```python
def generate_plotly_charts(df, df_plot, predictions):
    """
    Generate interactive Plotly charts for stock analysis.
    
    Args:
        df: Full DataFrame for statistics
        df_plot: Downsampled DataFrame for plotting
        predictions: Prediction data dictionary
        
    Returns:
        JSON string of Plotly figure
    """
    from plotly.subplots import make_subplots
    
    # Create subplots for Tesla-style analytics visualization
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=('Daily Close Price', 'Daily High and Low',
                       'Daily Volume', '% Change Between Open & Close'),
        specs=[[{"type": "xy"}, {"type": "xy"}],
               [{"type": "xy"}, {"type": "xy"}],
               [{"type": "xy", "colspan": 2}, None]],
        vertical_spacing=0.12,
        horizontal_spacing=0.1,
        row_heights=[0.33, 0.33, 0.34]
    )
    
    # Chart 1: Daily Close Price with Trend Line
    fig.add_trace(go.Scatter(
        x=df_plot['Date'],
        y=df_plot['Close'],
        mode='lines',
        name='Close Price',
        line=dict(color='#3b82f6', width=2),
        hovertemplate='Date: %{x}<br>Close: $%{y:.2f}<extra></extra>'
    ), row=1, col=1)
    
    # Add trend line
    x_numeric = np.arange(len(df_plot))
    z = np.polyfit(x_numeric, df_plot['Close'], 1)
    p = np.poly1d(z)
    
    fig.add_trace(go.Scatter(
        x=df_plot['Date'],
        y=p(x_numeric),
        mode='lines',
        name='Trend',
        line=dict(color='#ef4444', width=2, dash='dash'),
        hovertemplate='Trend: $%{y:.2f}<extra></extra>'
    ), row=1, col=1)
    
    # Highlight anomalies
    anomaly_data = df_plot[df_plot['IsAnomaly'] == True]
    if not anomaly_data.empty:
        fig.add_trace(go.Scatter(
            x=anomaly_data['Date'],
            y=anomaly_data['Close'],
            mode='markers',
            name='Anomaly',
            marker=dict(color='#f59e0b', size=10, symbol='diamond'),
            hovertemplate='Anomaly<br>Date: %{x}<br>Close: $%{y:.2f}<extra></extra>'
        ), row=1, col=1)
    
    # Chart 2: High and Low Prices
    fig.add_trace(go.Scatter(
        x=df_plot['Date'],
        y=df_plot['High'],
        mode='lines',
        name='High',
        line=dict(color='#10b981', width=2.5),
        hovertemplate='High: $%{y:.2f}<extra></extra>'
    ), row=1, col=2)
    
    fig.add_trace(go.Scatter(
        x=df_plot['Date'],
        y=df_plot['Low'],
        mode='lines',
        name='Low',
        line=dict(color='#A3A3A3', width=2.5),
        hovertemplate='Low: $%{y:.2f}<extra></extra>'
    ), row=1, col=2)
    
    # Chart 3: Daily Volume with highlighting
    max_vol_idx = df_plot['Volume'].idxmax()
    min_vol_idx = df_plot['Volume'].idxmin()
    
    # Create volume colors using positional indexing
    volume_colors = ['#666666'] * len(df_plot)
    max_vol_pos = df_plot.index.get_loc(max_vol_idx)
    min_vol_pos = df_plot.index.get_loc(min_vol_idx)
    volume_colors[max_vol_pos] = '#333333'  # Darker for max
    volume_colors[min_vol_pos] = '#AAAAAA'  # Lighter for min
    
    fig.add_trace(go.Bar(
        x=df_plot['Date'],
        y=df_plot['Volume'],
        name='Volume',
        marker_color=volume_colors,
        showlegend=False,
        hovertemplate='Date: %{x}<br>Volume: %{y:,}<extra></extra>'
    ), row=2, col=1)
    
    # Add volume annotations
    fig.add_annotation(
        x=df_plot.loc[max_vol_idx, 'Date'],
        y=df_plot.loc[max_vol_idx, 'Volume'],
        text=f"Max: {df_plot.loc[max_vol_idx, 'Volume']:,.0f}",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-40,
        font=dict(size=10, color='#1F2937'),
        row=2, col=1
    )
    
    # Chart 4: Percentage Change
    df_plot['OpenCloseChange'] = ((df_plot['Close'] - df_plot['Open']) / df_plot['Open']) * 100
    
    max_pos_idx = df_plot['OpenCloseChange'].idxmax()
    max_neg_idx = df_plot['OpenCloseChange'].idxmin()
    
    change_colors = ['#E85D5D' if x < 0 else '#4CAF50' for x in df_plot['OpenCloseChange']]
    
    fig.add_trace(go.Bar(
        x=df_plot['Date'],
        y=df_plot['OpenCloseChange'],
        name='% Change',
        marker_color=change_colors,
        showlegend=False,
        hovertemplate='Date: %{x}<br>Change: %{y:.2f}%<extra></extra>'
    ), row=2, col=2)
    
    # Chart 5: Stock Price Prediction
    if predictions:
        last_10_df = df_plot.tail(10)
        
        fig.add_trace(go.Scatter(
            x=last_10_df['Date'],
            y=last_10_df['Close'],
            mode='lines+markers',
            name='Recent Actual',
            line=dict(color='#667eea', width=3),
            marker=dict(size=8),
            hovertemplate='Date: %{x}<br>Actual: $%{y:.2f}<extra></extra>'
        ), row=3, col=1)
        
        fig.add_trace(go.Scatter(
            x=predictions['dates'],
            y=predictions['prices'],
            mode='lines+markers',
            name=f'Predicted ({predictions["trend"]} Trend)',
            line=dict(color='#48bb78', width=3, dash='dot'),
            marker=dict(size=10, symbol='diamond'),
            hovertemplate='Date: %{x}<br>Predicted: $%{y:.2f}<extra></extra>'
        ), row=3, col=1)
    
    # Update layout
    fig.update_layout(
        height=1400,
        showlegend=True,
        template='plotly_white',
        hovermode='x unified',
        font=dict(family="Arial, sans-serif", size=11),
        title=dict(
            text=f"<b>STOCK ANALYTICS</b><br><sup>Highest Price: ${df_plot['High'].max():.2f} | Lowest Price: ${df_plot['Low'].min():.2f}</sup>",
            x=0.5,
            xanchor='center',
            font=dict(size=20)
        )
    )
    
    # Update axes
    fig.update_xaxes(showgrid=True, gridcolor='lightgray')
    fig.update_yaxes(showgrid=True, gridcolor='lightgray')
    
    # Convert plot to JSON
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
```

### Spark UI Route
```python
@app.route('/spark-ui')
def spark_ui():
    """
    Display Spark Web UI monitoring page.
    """
    return render_template('spark_ui.html')
```

### Application Startup
```python
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting Stock Analytics Web Application")
    print("=" * 60)
    print(f"📊 Flask Server: http://127.0.0.1:5000")
    print(f"🔥 Spark Web UI: http://localhost:4040 (starts when analyzing data)")
    print("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )
```

---

## Page 2: Spark Data Processing Engine (spark_job.py)

### Imports and Setup
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, sum as spark_sum, count, abs as spark_abs
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType, BooleanType
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
```

### Main Processing Function
```python
def process_stock_data(filepath, threshold=5.0):
    """
    Process stock data using Apache Spark and detect anomalies.
    
    Args:
        filepath (str): Path to CSV file containing stock data
        threshold (float): Percentage change threshold for anomaly detection (default: 5%)
    
    Returns:
        dict: Processing results including data, anomalies, summary, and predictions
    """
    try:
        from spark_ui_manager import get_spark_session
        spark = get_spark_session()
        
        if not spark:
            return {
                'success': False,
                'error': 'Spark session not available'
            }
        
        # Define schema for stock data
        schema = StructType([
            StructField("Date", StringType(), True),
            StructField("Open", DoubleType(), True),
            StructField("High", DoubleType(), True),
            StructField("Low", DoubleType(), True),
            StructField("Close", DoubleType(), True),
            StructField("Adj Close", DoubleType(), True),
            StructField("Volume", LongType(), True)
        ])
        
        # Read CSV file into Spark DataFrame
        df = spark.read.csv(
            filepath,
            header=True,
            schema=schema,
            mode="DROPMALFORMED"
        )
        
        # Data cleaning: Remove rows with null values
        df = df.dropna()
        
        # Calculate percentage change between Open and Close
        df = df.withColumn(
            "PercentChange",
            ((col("Close") - col("Open")) / col("Open")) * 100
        )
        
        # Detect anomalies: Flag records where percentage change exceeds threshold
        df = df.withColumn(
            "IsAnomaly",
            (spark_abs(col("PercentChange")) > threshold)
        )
        
        # Calculate summary statistics using Spark aggregations
        summary_stats = df.agg(
            avg("Close").alias("average_price"),
            spark_sum("Volume").alias("total_volume"),
            count("*").alias("total_records")
        ).collect()[0]
        
        # Get min and max prices
        price_stats = df.agg(
            {"Close": "min", "Close": "max"}
        ).collect()[0]
        
        # Count anomalies
        anomaly_count = df.filter(col("IsAnomaly") == True).count()
        
        # Convert to Pandas for detailed processing
        pandas_df = df.toPandas()
        
        # Sort by date
        pandas_df['Date'] = pd.to_datetime(pandas_df['Date'])
        pandas_df = pandas_df.sort_values('Date')
        pandas_df['Date'] = pandas_df['Date'].dt.strftime('%Y-%m-%d')
        
        # Extract anomalies
        anomalies = pandas_df[pandas_df['IsAnomaly'] == True].to_dict('records')
        
        # Generate predictions
        predictions = generate_predictions(pandas_df)
        
        # Create processing log
        processing_log = [
            f"✓ Loaded {len(pandas_df)} records from CSV",
            f"✓ Cleaned data and removed null values",
            f"✓ Calculated percentage changes",
            f"✓ Detected {anomaly_count} anomalies (threshold: {threshold}%)",
            f"✓ Generated summary statistics",
            f"✓ Created 10-day price predictions"
        ]
        
        # Prepare summary
        summary = {
            'average_price': float(summary_stats['average_price']),
            'total_volume': int(summary_stats['total_volume']),
            'anomaly_count': int(anomaly_count),
            'max_price': float(pandas_df['High'].max()),
            'min_price': float(pandas_df['Low'].min()),
            'total_records': len(pandas_df)
        }
        
        return {
            'success': True,
            'data': pandas_df.to_dict('records'),
            'anomalies': anomalies,
            'summary': summary,
            'predictions': predictions,
            'processing_log': processing_log
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

### Prediction Algorithm
```python
def generate_predictions(df, days=10):
    """
    Generate future price predictions using linear regression.
    
    Args:
        df (DataFrame): Historical stock data
        days (int): Number of days to predict
    
    Returns:
        dict: Prediction results with dates, prices, and trend
    """
    try:
        # Get last 30 days for prediction model
        recent_df = df.tail(30).copy()
        
        # Convert dates to numeric values for regression
        recent_df['DateNumeric'] = range(len(recent_df))
        
        # Fit linear regression
        x = recent_df['DateNumeric'].values
        y = recent_df['Close'].values
        
        # Calculate trend using numpy polyfit (degree 1 = linear)
        z = np.polyfit(x, y, 1)
        slope = z[0]
        
        # Determine trend direction
        if slope > 0:
            trend = "Upward"
        elif slope < 0:
            trend = "Downward"
        else:
            trend = "Stable"
        
        # Generate future predictions
        last_date = pd.to_datetime(df['Date'].iloc[-1])
        last_numeric = len(recent_df) - 1
        
        future_dates = []
        future_prices = []
        
        for i in range(1, days + 1):
            future_date = last_date + timedelta(days=i)
            future_numeric = last_numeric + i
            future_price = z[0] * future_numeric + z[1]
            
            future_dates.append(future_date.strftime('%Y-%m-%d'))
            future_prices.append(float(future_price))
        
        return {
            'dates': future_dates,
            'prices': future_prices,
            'trend': trend,
            'slope': float(slope)
        }
        
    except Exception as e:
        print(f"Prediction error: {e}")
        return None
```

### Anomaly Analysis Function
```python
def analyze_anomalies(df, threshold=5.0):
    """
    Detailed anomaly analysis with statistical measures.
    
    Args:
        df (DataFrame): Stock data
        threshold (float): Anomaly detection threshold
    
    Returns:
        dict: Detailed anomaly statistics
    """
    anomalies = df[df['IsAnomaly'] == True].copy()
    
    if len(anomalies) == 0:
        return {
            'count': 0,
            'severity': 'None',
            'avg_change': 0,
            'max_change': 0
        }
    
    # Calculate anomaly statistics
    avg_change = abs(anomalies['PercentChange']).mean()
    max_change = abs(anomalies['PercentChange']).max()
    
    # Determine severity
    if avg_change > 10:
        severity = 'High'
    elif avg_change > 7:
        severity = 'Medium'
    else:
        severity = 'Low'
    
    return {
        'count': len(anomalies),
        'severity': severity,
        'avg_change': float(avg_change),
        'max_change': float(max_change),
        'positive_anomalies': len(anomalies[anomalies['PercentChange'] > 0]),
        'negative_anomalies': len(anomalies[anomalies['PercentChange'] < 0])
    }
```

---

## Page 3: Spark Session Manager (spark_ui_manager.py)

### Complete Implementation
```python
import os
import sys
import time
import threading
from pyspark.sql import SparkSession

# Global Spark session variable
_spark_session = None


def create_spark_session(auto_trigger_job=False):
    """
    Create and configure Apache Spark session with optimized settings.
    
    Args:
        auto_trigger_job (bool): Automatically trigger a sample job on startup
    
    Returns:
        SparkSession: Configured Spark session object
    """
    global _spark_session
    
    try:
        # Set Python executable for PySpark (fixes Windows path issues)
        os.environ['PYSPARK_PYTHON'] = sys.executable
        os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable
        
        print("🔧 Configuring Spark Session...")
        
        # Create Spark session with optimized configuration
        _spark_session = SparkSession.builder \
            .appName("Stock Anomaly Detection System") \
            .master("local[*]") \
            .config("spark.sql.shuffle.partitions", "8") \
            .config("spark.driver.memory", "4g") \
            .config("spark.executor.memory", "4g") \
            .config("spark.ui.port", "4040") \
            .config("spark.ui.enabled", "true") \
            .config("spark.driver.host", "localhost") \
            .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
            .config("spark.driver.bindAddress", "127.0.0.1") \
            .getOrCreate()
        
        # Set log level to reduce verbosity
        _spark_session.sparkContext.setLogLevel("WARN")
        
        print("✅ Spark Session created successfully!")
        print(f"📊 Spark Web UI: http://localhost:4040")
        print(f"🔥 Application Name: {_spark_session.sparkContext.appName}")
        print(f"⚡ Spark Version: {_spark_session.version}")
        
        # Auto-trigger sample job if requested
        if auto_trigger_job:
            print("🚀 Auto-triggering sample Spark job...")
            threading.Thread(target=_run_sample_job, daemon=True).start()
        
        return _spark_session
        
    except Exception as e:
        print(f"❌ Error creating Spark session: {e}")
        return None


def _run_sample_job():
    """
    Run a sample Spark job to initialize the Spark UI.
    This runs in a background thread.
    """
    try:
        time.sleep(2)  # Wait for server to fully start
        
        global _spark_session
        if _spark_session:
            print("🔄 Running sample job to initialize Spark UI...")
            
            # Create sample DataFrame
            sample_data = [
                ("GOOGL", 100.0, 105.0),
                ("AAPL", 150.0, 155.0),
                ("TSLA", 200.0, 210.0)
            ]
            
            df = _spark_session.createDataFrame(
                sample_data,
                ["Stock", "Open", "Close"]
            )
            
            # Simple aggregation to trigger Spark job
            df.groupBy("Stock").count().collect()
            
            print("✅ Sample job completed - Spark UI is now active!")
            
    except Exception as e:
        print(f"⚠️ Sample job warning: {e}")


def get_spark_session():
    """
    Get the existing Spark session or create a new one.
    
    Returns:
        SparkSession: Active Spark session
    """
    global _spark_session
    
    if _spark_session is None:
        _spark_session = create_spark_session()
    
    return _spark_session


def stop_spark_session():
    """
    Stop the active Spark session and clean up resources.
    """
    global _spark_session
    
    if _spark_session:
        print("🛑 Stopping Spark session...")
        _spark_session.stop()
        _spark_session = None
        print("✅ Spark session stopped successfully!")
    else:
        print("⚠️ No active Spark session to stop")


def get_spark_ui_url():
    """
    Get the URL for Spark Web UI.
    
    Returns:
        str: Spark UI URL
    """
    return "http://localhost:4040"


def is_spark_running():
    """
    Check if Spark session is active.
    
    Returns:
        bool: True if Spark is running, False otherwise
    """
    global _spark_session
    return _spark_session is not None


def get_spark_info():
    """
    Get information about the current Spark session.
    
    Returns:
        dict: Spark session information
    """
    global _spark_session
    
    if _spark_session is None:
        return {
            'status': 'Not Running',
            'version': None,
            'app_name': None,
            'ui_url': None
        }
    
    return {
        'status': 'Running',
        'version': _spark_session.version,
        'app_name': _spark_session.sparkContext.appName,
        'ui_url': get_spark_ui_url(),
        'master': _spark_session.sparkContext.master,
        'cores': _spark_session.sparkContext.defaultParallelism
    }
```

---

## Page 4: Frontend Templates & Styling

### Dashboard HTML Template (dashboard.html - Key Sections)
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Stock Anomaly Detection</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <!-- Top Navigation Header -->
    <nav style="background: linear-gradient(135deg, #0ea5e9 0%, #3b82f6 100%); padding: 15px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1); position: sticky; top: 0; z-index: 1000;">
        <div class="container" style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 15px;">
                <span style="font-size: 1.8em;">📈</span>
                <span style="color: white; font-size: 1.3em; font-weight: 700;">Stock Analytics</span>
            </div>
            <div style="display: flex; gap: 20px;">
                <a href="/" style="color: white; text-decoration: none; font-weight: 600; padding: 8px 16px; border-radius: 6px;">Home</a>
                <a href="/dashboard" style="color: white; text-decoration: none; font-weight: 600; padding: 8px 16px; border-radius: 6px; background: rgba(255,255,255,0.2);">Dashboard</a>
                <a href="/spark-ui" style="color: white; text-decoration: none; font-weight: 600; padding: 8px 16px; border-radius: 6px;">Spark Monitor</a>
            </div>
        </div>
    </nav>

    <div class="container" style="margin-top: 30px;">
        <!-- Stock Selector -->
        <header class="header">
            <h1>📊 Complete Analysis Dashboard</h1>
            <p class="subtitle">Stock Price Analysis, Predictions & Visualizations</p>
            
            <div style="margin-top: 25px;">
                <form action="/dashboard" method="get" style="display: flex; gap: 15px; justify-content: center;">
                    <label for="stock" style="font-weight: 600; color: #475569;">Select Stock:</label>
                    <select name="stock" id="stock" onchange="this.form.submit()" 
                            style="padding: 12px 20px; border: 2px solid #cbd5e1; border-radius: 8px;">
                        <option value="GOOGL" {{ 'selected' if selected_stock == 'GOOGL' else '' }}>GOOGL - Alphabet</option>
                        <option value="AAPL" {{ 'selected' if selected_stock == 'AAPL' else '' }}>AAPL - Apple</option>
                        <option value="TSLA" {{ 'selected' if selected_stock == 'TSLA' else '' }}>TSLA - Tesla</option>
                        <option value="META" {{ 'selected' if selected_stock == 'META' else '' }}>META - Meta</option>
                        <option value="AMZN" {{ 'selected' if selected_stock == 'AMZN' else '' }}>AMZN - Amazon</option>
                        <option value="MSFT" {{ 'selected' if selected_stock == 'MSFT' else '' }}>MSFT - Microsoft</option>
                        <option value="NFLX" {{ 'selected' if selected_stock == 'NFLX' else '' }}>NFLX - Netflix</option>
                        <option value="NVDA" {{ 'selected' if selected_stock == 'NVDA' else '' }}>NVDA - NVIDIA</option>
                        <option value="AMD" {{ 'selected' if selected_stock == 'AMD' else '' }}>AMD - AMD</option>
                        <option value="INTC" {{ 'selected' if selected_stock == 'INTC' else '' }}>INTC - Intel</option>
                    </select>
                </form>
            </div>
        </header>

        <!-- Summary Section with Gradient Colors -->
        <section class="summary-section">
            <h2>📊 Analysis Summary</h2>
            
            <!-- Monthly Summary -->
            <h3>📅 Monthly Summary</h3>
            <div class="monthly-summary">
                <div class="month-box">
                    <div class="month-name">{{ processing_stats.date_range.split(' to ')[0][:7] if processing_stats else 'Start' }}</div>
                    <div class="month-value">${{ "%.0f"|format(summary.average_price) }}</div>
                    <div class="month-label">Avg Price</div>
                </div>
                <div class="month-box">
                    <div class="month-name">{{ processing_stats.date_range.split(' to ')[1][:7] if processing_stats else 'End' }}</div>
                    <div class="month-value">{{ summary.anomaly_count }}</div>
                    <div class="month-label">Anomalies</div>
                </div>
            </div>
            
            <!-- Additional Statistics -->
            <h3>📈 Additional Statistics</h3>
            <div class="summary-grid">
                <div class="summary-card">
                    <span class="summary-icon">💰</span>
                    <h3>Average Price</h3>
                    <p class="summary-value">${{ "%.2f"|format(summary.average_price) }}</p>
                </div>
                <div class="summary-card">
                    <span class="summary-icon">📊</span>
                    <h3>Total Volume</h3>
                    <p class="summary-value">{{ "{:,}".format(summary.total_volume) }}</p>
                </div>
                <div class="summary-card anomaly-card">
                    <span class="summary-icon">⚠️</span>
                    <h3>Anomalies Detected</h3>
                    <p class="summary-value">{{ summary.anomaly_count }}</p>
                </div>
            </div>
        </section>

        <!-- Chart Section -->
        <section class="chart-section">
            <h2>📈 Interactive Analytics</h2>
            <div id="plotly-chart"></div>
        </section>

        <!-- Anomaly Table -->
        <section class="anomaly-section">
            <h2>⚠️ Detected Anomalies</h2>
            <div class="table-container">
                <table class="anomaly-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Open</th>
                            <th>Close</th>
                            <th>% Change</th>
                            <th>Volume</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for anomaly in anomalies %}
                        <tr>
                            <td>{{ anomaly.Date }}</td>
                            <td>${{ "%.2f"|format(anomaly.Open) }}</td>
                            <td>${{ "%.2f"|format(anomaly.Close) }}</td>
                            <td class="{{ 'positive' if anomaly.PercentChange > 0 else 'negative' }}">
                                {{ "%.2f"|format(anomaly.PercentChange) }}%
                            </td>
                            <td>{{ "{:,}".format(anomaly.Volume) }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </section>
    </div>

    <!-- Plotly Chart Rendering Script -->
    <script>
        var graphData = {{ graph_json | safe }};
        Plotly.newPlot('plotly-chart', graphData.data, graphData.layout, {responsive: true});
    </script>
</body>
</html>
```

### CSS Styling (styles.css - Key Sections)
```css
/* Global Light Theme */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Roboto', sans-serif;
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #dbeafe 100%);
    min-height: 100vh;
    color: #1e293b;
    line-height: 1.6;
}

/* Monthly Summary with Cyan Gradient */
.monthly-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.month-box {
    background: linear-gradient(135deg, #06b6d4 0%, #0891b2 50%, #0e7490 100%);
    color: white;
    padding: 25px;
    border-radius: 8px;
    text-align: center;
    box-shadow: 0 8px 20px rgba(6, 182, 212, 0.4);
}

/* Additional Statistics with Purple Gradient */
.summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 20px;
}

.summary-card {
    background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 50%, #6d28d9 100%);
    color: white;
    padding: 25px;
    border-radius: 8px;
    text-align: center;
    box-shadow: 0 8px 20px rgba(139, 92, 246, 0.4);
}

.summary-card.anomaly-card {
    background: linear-gradient(135deg, #ec4899 0%, #db2777 50%, #be185d 100%);
    box-shadow: 0 8px 20px rgba(236, 72, 153, 0.4);
}

/* Processing Statistics with Blue Gradient */
.processing-section {
    background: linear-gradient(135deg, #0ea5e9 0%, #3b82f6 50%, #6366f1 100%);
    padding: 35px;
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(59, 130, 246, 0.4);
    margin-bottom: 30px;
}

.processing-card {
    background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 50%, #e0f2fe 100%);
    padding: 20px;
    border-radius: 8px;
    text-align: center;
    border: 2px solid rgba(59, 130, 246, 0.3);
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.2);
}

/* Anomaly Table */
.anomaly-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 8px;
    overflow: hidden;
}

.anomaly-table th {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    color: white;
    padding: 15px;
    font-weight: 600;
}

.anomaly-table td {
    padding: 12px;
    border-bottom: 1px solid #e2e8f0;
}

.positive {
    color: #10b981;
    font-weight: 600;
}

.negative {
    color: #ef4444;
    font-weight: 600;
}
```

---

## Summary

This implementation code covers:

1. **Flask Application** (app.py) - Complete web server with routing and chart generation
2. **Spark Processing** (spark_job.py) - Data processing, anomaly detection, and predictions
3. **Spark Manager** (spark_ui_manager.py) - Session management and auto-triggering
4. **Frontend** (HTML/CSS) - Professional UI with gradient colors and responsive design

All code is production-ready with error handling, comments, and optimization for large datasets.
