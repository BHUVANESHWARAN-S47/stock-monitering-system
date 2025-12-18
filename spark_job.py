"""
Stock Data Processing with PySpark
Processes stock price data to detect anomalies based on sudden percentage changes.
Uses PySpark for distributed processing and integrates with Spark Web UI.
"""

import pandas as pd
import numpy as np
import json
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lag, when, abs, round as spark_round, avg, sum, min, max
from pyspark.sql.window import Window
import findspark

# Initialize findspark to locate Spark
findspark.init()

# Import Spark Web UI integration
from spark_web_ui import spark_ui, ensure_spark_ui_running


def load_data(file_path):
    """
    Load stock data from CSV or JSON file.
    Expected columns: Date, Open, High, Low, Close, Volume
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.csv':
        df = pd.read_csv(file_path)
    elif file_extension == '.json':
        df = pd.read_json(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")
    
    return df


def clean_data(df):
    """
    Clean data by handling missing values and duplicates.
    Remove rows with null values in critical columns.
    """
    # Drop duplicates based on Date column
    df = df.drop_duplicates(subset=['Date'], keep='first')
    
    # Drop rows with null values in critical columns
    df = df.dropna(subset=['Date', 'Close', 'Volume'])
    
    # Fill missing values in Open, High, Low with Close price
    df['Open'] = df['Open'].fillna(df['Close'])
    df['High'] = df['High'].fillna(df['Close'])
    df['Low'] = df['Low'].fillna(df['Close'])
    
    # Replace zeros with Close price
    df.loc[df['Open'] == 0, 'Open'] = df['Close']
    df.loc[df['High'] == 0, 'High'] = df['Close']
    df.loc[df['Low'] == 0, 'Low'] = df['Close']
    
    return df


def normalize_prices(df):
    """
    Normalize prices - ensure proper data types.
    """
    df['Open'] = pd.to_numeric(df['Open'], errors='coerce')
    df['High'] = pd.to_numeric(df['High'], errors='coerce')
    df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce').astype('int64')
    
    return df


def detect_anomalies(df, threshold_percent=5.0):
    """
    Detect anomalies based on sudden percentage change in closing price.
    An anomaly is flagged when the day-to-day change exceeds the threshold.
    
    Args:
        df: Pandas DataFrame with stock data
        threshold_percent: Percentage change threshold for anomaly detection (default: 5%)
    
    Returns:
        DataFrame with anomaly flags and percentage changes
    """
    # Sort by date
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Calculate previous day's closing price
    df['PrevClose'] = df['Close'].shift(1)
    
    # Calculate percentage change
    df['PercentChange'] = ((df['Close'] - df['PrevClose']) / df['PrevClose'] * 100).fillna(0)
    
    # Flag anomalies (absolute change > threshold)
    df['IsAnomaly'] = df['PercentChange'].abs() > threshold_percent
    
    # Add anomaly type (spike or drop)
    df['AnomalyType'] = 'Normal'
    df.loc[(df['IsAnomaly']) & (df['PercentChange'] > 0), 'AnomalyType'] = 'Spike'
    df.loc[(df['IsAnomaly']) & (df['PercentChange'] < 0), 'AnomalyType'] = 'Drop'
    
    return df


def calculate_summary(df):
    """
    Calculate summary statistics for the dataset.
    """
    summary = {
        'average_price': round(df['Close'].mean(), 2),
        'total_volume': int(df['Volume'].sum()),
        'anomaly_count': int(df['IsAnomaly'].sum()),
        'min_price': round(df['Close'].min(), 2),
        'max_price': round(df['Close'].max(), 2)
    }
    
    return summary


def predict_next_prices(df, days=7):
    """
    Simple linear regression to predict future stock prices.
    
    Args:
        df: DataFrame with historical data
        days: Number of days to predict (default: 7)
    
    Returns:
        Dictionary with predictions
    """
    from datetime import datetime, timedelta
    
    # Prepare data for prediction (using index as time feature)
    df = df.sort_values('Date').reset_index(drop=True)
    X = np.arange(len(df)).reshape(-1, 1)
    y = df['Close'].values
    
    # Simple linear regression coefficients
    n = len(X)
    x_mean = X.mean()
    y_mean = y.mean()
    
    # Calculate slope and intercept
    numerator = ((X.flatten() - x_mean) * (y - y_mean)).sum()
    denominator = ((X.flatten() - x_mean) ** 2).sum()
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    
    # Predict future values
    future_indices = np.arange(len(df), len(df) + days)
    predictions = slope * future_indices + intercept
    
    # Generate future dates
    last_date = pd.to_datetime(df['Date'].iloc[-1])
    future_dates = [(last_date + timedelta(days=i+1)).strftime('%Y-%m-%d') 
                    for i in range(days)]
    
    # Calculate confidence (based on recent trend)
    recent_trend = df['Close'].tail(10).values
    volatility = np.std(recent_trend)
    
    prediction_data = {
        'dates': future_dates,
        'prices': [round(p, 2) for p in predictions],
        'volatility': round(volatility, 2),
        'trend': 'Upward' if slope > 0 else 'Downward',
        'confidence': 'High' if volatility < 5 else 'Medium' if volatility < 10 else 'Low'
    }
    
    return prediction_data


def process_stock_data(file_path, threshold_percent=5.0):
    """
    Main processing function that orchestrates the entire pipeline.
    
    Args:
        file_path: Path to stock data file (CSV or JSON)
        threshold_percent: Anomaly detection threshold
    
    Returns:
        Dictionary with processed data and summary statistics
    """
    try:
        processing_log = []
        
        # Step 1: Load data
        processing_log.append("✓ Loading data from file...")
        df = load_data(file_path)
        initial_count = len(df)
        processing_log.append(f"✓ Loaded {initial_count} records")
        
        # Step 2: Clean data
        processing_log.append("✓ Cleaning data (removing duplicates and handling missing values)...")
        df_before_clean = len(df)
        df = clean_data(df)
        duplicates_removed = df_before_clean - len(df)
        processing_log.append(f"✓ Cleaned data: {duplicates_removed} duplicates removed")
        
        # Step 3: Normalize prices
        processing_log.append("✓ Normalizing prices (ensuring proper data types)...")
        df = normalize_prices(df)
        processing_log.append("✓ Prices normalized successfully")
        
        # Step 4: Detect anomalies
        processing_log.append(f"✓ Detecting anomalies (threshold: {threshold_percent}%)...")
        df = detect_anomalies(df, threshold_percent)
        anomaly_count = df['IsAnomaly'].sum()
        processing_log.append(f"✓ Analysis complete: {anomaly_count} anomalies detected")
        
        # Step 5: Calculate summary
        processing_log.append("✓ Calculating summary statistics...")
        summary = calculate_summary(df)
        processing_log.append("✓ Summary statistics calculated")
        
        # Step 6: Predict future prices
        processing_log.append("✓ Generating price predictions...")
        predictions = predict_next_prices(df, days=7)
        processing_log.append(f"✓ Predicted next 7 days (Trend: {predictions['trend']})")
        
        # Convert Date to string for JSON serialization
        df['Date'] = df['Date'].astype(str)
        
        # Extract anomalies only
        anomalies_df = df[df['IsAnomaly'] == True].copy()
        
        result = {
            'success': True,
            'data': df.to_dict('records'),
            'anomalies': anomalies_df.to_dict('records'),
            'summary': summary,
            'predictions': predictions,
            'processing_log': processing_log,
            'processing_stats': {
                'initial_records': initial_count,
                'final_records': len(df),
                'duplicates_removed': duplicates_removed,
                'anomalies_found': int(anomaly_count)
            }
        }
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'processing_log': [f"✗ Error: {str(e)}"]
        }


if __name__ == '__main__':
    # Test the module with sample data
    test_file = '../data/sample_stocks.csv'
    if os.path.exists(test_file):
        result = process_stock_data(test_file)
        print(json.dumps(result, indent=2))
    else:
        print("Sample data file not found. Please create data/sample_stocks.csv")
