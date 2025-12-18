"""
Flask Web Application for Stock Price Monitoring and Anomaly Detection
Routes: /, /upload, /analyze, /dashboard, /export
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session
import os
import json
from werkzeug.utils import secure_filename
import pandas as pd
import plotly
import plotly.graph_objs as go
from datetime import datetime

# Import our PySpark processing module
import spark_job

# Import Spark Web UI Manager (NO NGROK - Pure Local)
import spark_ui_manager

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
ALLOWED_EXTENSIONS = {'csv', 'json'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'stock-anomaly-detection-secret-key-2025'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """
    Home page with welcome message and upload option.
    """
    return render_template('index.html')


@app.route('/spark-ui')
def spark_ui_page():
    """
    Spark Web UI monitoring page.
    """
    status = spark_ui_manager.get_spark_status()
    return render_template('spark_ui_monitor.html', status=status)


@app.route('/spark-ui/open')
def open_spark_ui():
    """
    Redirect to Spark Web UI.
    Creates session if needed and redirects to http://localhost:4040
    """
    # Ensure Spark session exists
    session = spark_ui_manager.get_spark_session()
    
    if session:
        status = spark_ui_manager.get_spark_status()
        return redirect(status['ui_url'])
    else:
        return jsonify({
            'error': 'Spark session not available',
            'message': 'Please analyze data first to start Spark session'
        }), 503


@app.route('/api/spark-status')
def api_spark_status():
    """
    API endpoint to get Spark status.
    """
    status = spark_ui_manager.get_spark_status()
    return jsonify(status)


@app.route('/api/spark-start')
def api_spark_start():
    """
    API endpoint to start Spark session.
    Automatically triggers anomaly detection job on GOOGL.csv.
    """
    try:
        # Create session with auto-trigger enabled
        session = spark_ui_manager.create_spark_session(auto_trigger_job=True)
        if session:
            status = spark_ui_manager.get_spark_status()
            return jsonify({
                'success': True,
                'message': 'Spark session started with auto-triggered job',
                'status': status
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to start Spark session'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Handle file upload from user.
    Validates file type and saves to upload folder.
    """
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400
    
    file = request.files['file']
    
    # Check if filename is empty
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check if file type is allowed
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Add timestamp to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Store filepath in session for later processing
        session['uploaded_file'] = filepath
        
        return jsonify({
            'success': True,
            'filename': filename,
            'message': 'File uploaded successfully'
        })
    
    return jsonify({'error': 'Invalid file type. Only CSV and JSON are allowed.'}), 400


@app.route('/analyze', methods=['POST'])
def analyze_data():
    """
    Run data analysis on uploaded file or sample data.
    Detects anomalies and stores results in session.
    """
    # Get threshold from request (default 5%)
    threshold = float(request.form.get('threshold', 5.0))
    
    # Check if we should use sample data
    use_sample = request.form.get('use_sample', 'false').lower() == 'true'
    
    if use_sample:
        # Use the GOOGL.csv data file
        sample_path = os.path.join(os.path.dirname(__file__), '..', 'GOOGL.csv')
        filepath = os.path.abspath(sample_path)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'GOOGL.csv file not found'}), 404
    else:
        # Get uploaded file path from session
        filepath = session.get('uploaded_file')
        
        if not filepath or not os.path.exists(filepath):
            return jsonify({'error': 'No file uploaded or file not found'}), 400
    
    try:
        # Process data with detailed logging
        result = spark_job.process_stock_data(filepath, threshold)
        
        if not result['success']:
            return jsonify({
                'error': result.get('error', 'Processing failed'),
                'processing_log': result.get('processing_log', [])
            }), 500
        
        # Store results in session
        session['analysis_result'] = result
        session['threshold'] = threshold
        
        return jsonify({
            'success': True,
            'message': 'Analysis completed successfully',
            'summary': result['summary'],
            'processing_log': result.get('processing_log', []),
            'processing_stats': result.get('processing_stats', {})
        })
        
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


@app.route('/dashboard')
def dashboard():
    """
    Display dashboard with analysis results, charts, and anomalies.
    Supports multiple stock symbols via query parameter.
    """
    # Get stock symbol from query parameter (default: GOOGL)
    stock_symbol = request.args.get('stock', 'GOOGL').upper()
    
    # Available stocks
    available_stocks = ['GOOGL', 'AAPL', 'AMZN', 'MSFT', 'TSLA', 'META', 'NFLX', 'NVDA', 'AMD', 'INTC']
    
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
    
    # Create subplots for Tesla-style analytics visualization
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=('Daily Close Price', 'Daily High and Low',
                       'Daily Volume', '% Change Between Open & Close'),
        specs=[[{"type": "xy"}, {"type": "xy"}],
               [{"type": "xy"}, {"type": "xy"}],
               [{"colspan": 2}, None]],
        vertical_spacing=0.12,
        horizontal_spacing=0.12,
        row_heights=[0.35, 0.35, 0.30]
    )
    
    # Add trendline calculation for daily close price
    from numpy import polyfit, polyval
    x_numeric = list(range(len(df_plot)))
    z = polyfit(x_numeric, df_plot['Close'].values, 1)
    p = polyval(z, x_numeric)
    
    # Chart 1: Daily Close Price with trendline (like Tesla chart)
    fig.add_trace(go.Scatter(
        x=df_plot['Date'],
        y=df_plot['Close'],
        mode='lines',
        name='Close Price',
        line=dict(color='#E85D5D', width=3),
        hovertemplate='Date: %{x}<br>Close: $%{y:.2f}<extra></extra>'
    ), row=1, col=1)
    
    # Add trendline
    fig.add_trace(go.Scatter(
        x=df_plot['Date'],
        y=p,
        mode='lines',
        name='Trend',
        line=dict(color='#999999', width=2, dash='dash'),
        hovertemplate='Trend: $%{y:.2f}<extra></extra>'
    ), row=1, col=1)
    
    # Highlight anomalies on close price
    anomaly_df = df_plot[df_plot['IsAnomaly'] == True]
    if not anomaly_df.empty:
        fig.add_trace(go.Scatter(
            x=anomaly_df['Date'],
            y=anomaly_df['Close'],
            mode='markers',
            name='Anomalies',
            marker=dict(color='red', size=14, symbol='x', line=dict(color='darkred', width=2)),
            hovertemplate='<b>ANOMALY</b><br>Date: %{x}<br>Price: $%{y:.2f}<extra></extra>'
        ), row=1, col=1)
    
    # Chart 2: Daily High and Low (like Tesla chart)
    fig.add_trace(go.Scatter(
        x=df_plot['Date'],
        y=df_plot['High'],
        mode='lines',
        name='High',
        line=dict(color='#E85D5D', width=2.5),
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
    
    # Chart 3: Daily Volume (like Tesla chart with bar chart)
    # Find highest and lowest volume for highlighting
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
    
    # Add text annotation for max and min volume
    fig.add_annotation(
        x=df_plot.loc[max_vol_idx, 'Date'],
        y=df_plot.loc[max_vol_idx, 'Volume'],
        text=f"{df_plot.loc[max_vol_idx, 'Volume']:,.0f}",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-40,
        font=dict(size=10, color='black'),
        row=2, col=1
    )
    
    fig.add_annotation(
        x=df_plot.loc[min_vol_idx, 'Date'],
        y=df_plot.loc[min_vol_idx, 'Volume'],
        text=f"{df_plot.loc[min_vol_idx, 'Volume']:,.0f}",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=40,
        font=dict(size=10, color='black'),
        row=2, col=1
    )
    
    # Chart 4: % Change Between Open & Close (like Tesla chart)
    # Calculate % change
    df_plot['OpenCloseChange'] = ((df_plot['Close'] - df_plot['Open']) / df_plot['Open']) * 100
    
    # Find max positive and max negative changes
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
    
    # Add annotations for max and min changes
    fig.add_annotation(
        x=df_plot.loc[max_pos_idx, 'Date'],
        y=df_plot.loc[max_pos_idx, 'OpenCloseChange'],
        text=f"{df_plot.loc[max_pos_idx, 'OpenCloseChange']:.2f}%",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-40,
        font=dict(size=10, color='#2E7D32'),
        row=2, col=2
    )
    
    fig.add_annotation(
        x=df_plot.loc[max_neg_idx, 'Date'],
        y=df_plot.loc[max_neg_idx, 'OpenCloseChange'],
        text=f"{df_plot.loc[max_neg_idx, 'OpenCloseChange']:.2f}%",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=40,
        font=dict(size=10, color='#C62828'),
        row=2, col=2
    )
    
    # Chart 5: Stock Price Prediction (Bottom, full width)
    if predictions:
        # Show last 10 days of actual prices
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
    
    # Update axes labels and styling
    fig.update_xaxes(title_text="Day of Date [2022]", row=1, col=1, showgrid=True, gridcolor='lightgray')
    fig.update_xaxes(title_text="Day of Date [2022]", row=1, col=2, showgrid=True, gridcolor='lightgray')
    fig.update_xaxes(title_text="Day of Date [2022]", row=2, col=1, showgrid=True, gridcolor='lightgray')
    fig.update_xaxes(title_text="Day of Date [2022]", row=2, col=2, showgrid=True, gridcolor='lightgray')
    fig.update_xaxes(title_text="Prediction Date", row=3, col=1, showgrid=True, gridcolor='lightgray')
    
    fig.update_yaxes(title_text="Close", row=1, col=1, showgrid=True, gridcolor='lightgray')
    fig.update_yaxes(title_text="High & Low", row=1, col=2, showgrid=True, gridcolor='lightgray')
    fig.update_yaxes(title_text="Volume", row=2, col=1, showgrid=True, gridcolor='lightgray')
    fig.update_yaxes(title_text="% Change", row=2, col=2, showgrid=True, gridcolor='lightgray')
    fig.update_yaxes(title_text="Price ($)", row=3, col=1, showgrid=True, gridcolor='lightgray')
    
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
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.05,
            xanchor="center",
            x=0.5
        )
    )
    
    # Convert plot to JSON for embedding in HTML
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Get data processing stats
    processing_stats = {
        'total_records': len(data),
        'date_range': f"{df['Date'].min()} to {df['Date'].max()}",
        'duplicates_removed': 0,  # Could track this in actual processing
        'missing_values_handled': 0,  # Could track this too
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


@app.route('/export')
def export():
    """
    Export anomaly results as CSV file.
    """
    result = session.get('analysis_result')
    
    if not result:
        return jsonify({'error': 'No analysis results to export'}), 400
    
    # Create DataFrame from anomalies
    anomalies_df = pd.DataFrame(result['anomalies'])
    
    # Define export file path
    export_path = os.path.join(app.config['UPLOAD_FOLDER'], 'anomalies_export.csv')
    
    # Export to CSV
    anomalies_df.to_csv(export_path, index=False)
    
    # Send file to user
    return send_file(export_path,
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name=f'anomalies_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')


@app.route('/reset')
def reset():
    """
    Clear session and uploaded files, return to home page.
    """
    session.clear()
    return redirect(url_for('index'))


@app.route('/apply_window', methods=['POST'])
def apply_window():
    """
    Apply time window filter to the data and regenerate visualizations.
    """
    try:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        window_type = request.form.get('window_type', 'daily')
        
        print(f"Apply window request: {start_date} to {end_date}, type: {window_type}")
        
        # Get current analysis result
        result = session.get('analysis_result')
        if not result:
            print("ERROR: No analysis data found in session, attempting to reload GOOGL.csv")
            # Try to reload the default GOOGL.csv data
            try:
                sample_path = os.path.join(os.path.dirname(__file__), '..', 'GOOGL.csv')
                filepath = os.path.abspath(sample_path)
                
                if os.path.exists(filepath):
                    threshold = session.get('threshold', 5.0)
                    result = spark_job.process_stock_data(filepath, threshold)
                    
                    if result['success']:
                        session['analysis_result'] = result
                        session['threshold'] = threshold
                        print("Successfully reloaded GOOGL.csv data")
                    else:
                        return jsonify({'success': False, 'error': 'Failed to reload data. Please go to home and analyze data first.'}), 400
                else:
                    return jsonify({'success': False, 'error': 'No analysis data found. Please analyze data first.'}), 400
            except Exception as reload_err:
                print(f"ERROR reloading data: {str(reload_err)}")
                return jsonify({'success': False, 'error': f'Session expired. Please analyze data again: {str(reload_err)}'}), 400
        
        # Convert data to DataFrame
        df = pd.DataFrame(result['data'])
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Apply date filter
        df_filtered = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)].copy()
        
        if len(df_filtered) == 0:
            return jsonify({'success': False, 'error': 'No data found in selected date range'}), 400
        
        # Apply windowing aggregation if not daily
        if window_type == 'weekly':
            df_filtered['Period'] = df_filtered['Date'].dt.to_period('W')
            df_windowed = df_filtered.groupby('Period').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum',
                'IsAnomaly': 'any'
            }).reset_index()
            df_windowed['Date'] = df_windowed['Period'].dt.start_time
            df_windowed['PercentChange'] = ((df_windowed['Close'] - df_windowed['Close'].shift(1)) / 
                                            df_windowed['Close'].shift(1)) * 100
            df_windowed['PercentChange'] = df_windowed['PercentChange'].fillna(0)
            
        elif window_type == 'monthly':
            df_filtered['Period'] = df_filtered['Date'].dt.to_period('M')
            df_windowed = df_filtered.groupby('Period').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum',
                'IsAnomaly': 'any'
            }).reset_index()
            df_windowed['Date'] = df_windowed['Period'].dt.start_time
            df_windowed['PercentChange'] = ((df_windowed['Close'] - df_windowed['Close'].shift(1)) / 
                                            df_windowed['Close'].shift(1)) * 100
            df_windowed['PercentChange'] = df_windowed['PercentChange'].fillna(0)
            
        else:  # daily
            df_windowed = df_filtered
        
        # Convert back to records
        windowed_data = []
        for _, row in df_windowed.iterrows():
            windowed_data.append({
                'Date': row['Date'].strftime('%Y-%m-%d'),
                'Open': float(row['Open']),
                'High': float(row['High']),
                'Low': float(row['Low']),
                'Close': float(row['Close']),
                'Volume': int(row['Volume']),
                'PercentChange': float(row['PercentChange']),
                'IsAnomaly': bool(row['IsAnomaly'])
            })
        
        # Extract anomalies from windowed data
        anomalies_windowed = [record for record in windowed_data if record['IsAnomaly']]
        
        # Calculate summary for windowed data
        summary_windowed = {
            'average_price': float(df_windowed['Close'].mean()),
            'total_volume': int(df_windowed['Volume'].sum()),
            'anomaly_count': int(df_windowed['IsAnomaly'].sum()),
            'min_price': float(df_windowed['Low'].min()),
            'max_price': float(df_windowed['High'].max())
        }
        
        # Store windowed result in session
        result_windowed = {
            'success': True,
            'data': windowed_data,
            'anomalies': anomalies_windowed,
            'summary': summary_windowed,
            'predictions': result.get('predictions'),  # Keep original predictions
            'processing_log': result.get('processing_log', []) + 
                            [f"✓ Applied {window_type} window: {start_date} to {end_date}",
                             f"✓ Filtered to {len(windowed_data)} records"],
            'processing_stats': {
                **result.get('processing_stats', {}),
                'window_applied': True,
                'window_type': window_type,
                'window_start': start_date,
                'window_end': end_date,
                'window_records': len(windowed_data)
            }
        }
        
        session['analysis_result'] = result_windowed
        
        print(f"Window applied successfully: {len(windowed_data)} records, {len(anomalies_windowed)} anomalies")
        
        return jsonify({
            'success': True,
            'records': len(windowed_data),
            'anomalies': len(anomalies_windowed),
            'window_type': window_type
        })
        
    except Exception as e:
        print(f"ERROR in apply_window: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/reset_window', methods=['POST'])
def reset_window():
    """
    Reset window filter and restore original full data.
    """
    try:
        # Get stock symbol from session or default to GOOGL
        stock_symbol = request.form.get('stock', 'GOOGL').upper()
        
        # Re-analyze the original data
        sample_path = os.path.join(os.path.dirname(__file__), '..', f'{stock_symbol}.csv')
        filepath = os.path.abspath(sample_path)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'Data file not found'}), 404
        
        # Process full data again
        result = spark_job.process_stock_data(filepath, 5.0)
        
        if not result['success']:
            return jsonify({'success': False, 'error': 'Failed to reset window'}), 500
        
        # Store in session with stock symbol
        session_key = f'analysis_result_{stock_symbol}'
        session[session_key] = result
        
        return jsonify({
            'success': True,
            'records': len(result['data'])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # Run Flask development server
    print("=" * 60)
    print("🚀 Starting Stock Analytics Web Application")
    print("=" * 60)
    print("📊 Flask Server: http://127.0.0.1:5000")
    print("🔥 Spark Web UI: http://localhost:4040 (starts when analyzing data)")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
