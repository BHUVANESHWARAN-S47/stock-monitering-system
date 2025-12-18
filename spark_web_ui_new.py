# -*- coding: utf-8 -*-
"""
Spark Web UI Integration Module (Without ngrok)
Provides functionality to start and manage Spark Web UI for monitoring PySpark jobs locally.
Web UI available at: http://localhost:4040
"""

import os
import time
import requests
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lag, when, abs as spark_abs, round as spark_round, mean, stddev
from pyspark.sql.window import Window
from pyspark.ml.regression import LinearRegression
from pyspark.ml.feature import VectorAssembler, MinMaxScaler, StandardScaler
import logging
import psutil
import pandas as pd
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables to track Spark session and UI status
_spark_session = None
_spark_ui_url = None
_spark_ui_port = 4040


def kill_existing_spark_sessions():
    """
    Kill any existing Spark sessions and Java processes to ensure clean startup.
    """
    try:
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.cmdline()) if proc.cmdline() else ''
                if 'spark' in cmdline.lower() and 'SparkSubmit' in cmdline:
                    logger.info(f"Killing existing Spark process: {proc.pid}")
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception as e:
        logger.warning(f"Could not kill existing processes: {e}")


def create_spark_session(app_name="StockAnomalyDetection", enable_ui=True):
    """
    Create and configure a Spark session with Web UI enabled.
    
    Args:
        app_name: Name for the Spark application
        enable_ui: Whether to enable Spark Web UI
    
    Returns:
        SparkSession: Configured Spark session or None if failed
    """
    global _spark_session, _spark_ui_url, _spark_ui_port

    if _spark_session is not None:
        logger.info("Spark session already exists. Returning existing session.")
        return _spark_session

    try:
        # Clean up any existing Spark sessions
        logger.info("Checking for existing Spark sessions...")
        kill_existing_spark_sessions()
        time.sleep(2)
        
        # Stop any existing Spark context first
        from pyspark import SparkContext
        try:
            sc = SparkContext._active_spark_context
            if sc is not None:
                logger.info("Stopping existing Spark context...")
                sc.stop()
                time.sleep(1)
        except:
            pass

        logger.info(f"Creating new Spark session: {app_name}")
        
        # Build Spark session with optimized configuration
        builder = SparkSession.builder \
            .appName(app_name) \
            .master("local[*]") \
            .config("spark.ui.enabled", "true") \
            .config("spark.ui.port", str(_spark_ui_port)) \
            .config("spark.driver.host", "localhost") \
            .config("spark.driver.bindAddress", "127.0.0.1") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.driver.memory", "2g") \
            .config("spark.executor.memory", "2g") \
            .config("spark.sql.shuffle.partitions", "4") \
            .config("spark.default.parallelism", "4")

        try:
            _spark_session = builder.getOrCreate()
            logger.info("✅ Spark session created successfully!")
        except Exception as primary_err:
            logger.warning(f"SparkSession creation failed: {primary_err}")
            logger.warning("Spark features will be disabled. App will continue without Spark.")
            _spark_session = None
            return None

        # Get the UI URL if available
        if enable_ui and _spark_session:
            try:
                sc = _spark_session.sparkContext
                ui_web_url = sc.uiWebUrl
                
                if ui_web_url:
                    _spark_ui_url = ui_web_url
                    logger.info(f"🌐 Spark Web UI available at: {_spark_ui_url}")
                else:
                    _spark_ui_url = f"http://localhost:{_spark_ui_port}"
                    logger.info(f"🌐 Spark Web UI should be available at: {_spark_ui_url}")
                
                logger.info(f"   Open in browser: http://localhost:{_spark_ui_port}")
            except Exception as e:
                logger.warning(f"Could not get Spark UI URL: {e}")
                _spark_ui_url = f"http://localhost:{_spark_ui_port}"
        
        logger.info(f"📊 Spark Application Name: {_spark_session.sparkContext.appName}")
        logger.info(f"🔑 Spark Application ID: {_spark_session.sparkContext.applicationId}")
        
        return _spark_session
        
    except Exception as e:
        logger.error(f"Failed to create Spark session: {e}")
        logger.warning("Spark features will be disabled. App will continue.")
        _spark_session = None
        return None


def get_spark_session():
    """
    Get the active Spark session, creating one if needed.
    
    Returns:
        SparkSession: Active Spark session
    """
    global _spark_session
    
    if _spark_session is None:
        _spark_session = create_spark_session()
    
    return _spark_session


def run_anomaly_detection_job(df_pandas, threshold_percent=5.0):
    """
    Run complete anomaly detection pipeline with Spark.
    Includes data preprocessing, normalization, anomaly detection, and predictions.
    
    Args:
        df_pandas: Pandas DataFrame with stock data
        threshold_percent: Anomaly detection threshold (default 5.0%)
    
    Returns:
        dict: Complete processing results
    """
    spark = get_spark_session()
    
    if spark is None:
        logger.warning("❌ Spark not available")
        return None
    
    try:
        logger.info("=" * 60)
        logger.info("🚀 STARTING SPARK ANOMALY DETECTION JOB")
        logger.info("=" * 60)
        
        # Step 1: Convert to Spark DataFrame
        logger.info("📥 Step 1: Loading data into Spark...")
        df_spark = spark.createDataFrame(df_pandas)
        df_spark.cache()
        
        initial_count = df_spark.count()
        logger.info(f"✅ Loaded {initial_count} records into Spark")
        
        # Step 2: Data Preprocessing
        logger.info("🧹 Step 2: Data preprocessing...")
        
        # Remove duplicates
        df_clean = df_spark.dropDuplicates(["Date"])
        
        # Remove null values
        df_clean = df_clean.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
        
        # Remove invalid prices
        df_clean = df_clean.filter(
            (col("Open") > 0) & (col("High") > 0) & 
            (col("Low") > 0) & (col("Close") > 0)
        )
        
        # Remove outliers using IQR
        quantiles = df_clean.approxQuantile("Close", [0.25, 0.75], 0.0)
        q1, q3 = quantiles[0], quantiles[1]
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        df_clean = df_clean.filter((col("Close") >= lower_bound) & (col("Close") <= upper_bound))
        
        clean_count = df_clean.count()
        duplicates_removed = initial_count - clean_count
        logger.info(f"✅ Cleaned data: {clean_count} records (removed {duplicates_removed} duplicates/outliers)")
        
        # Step 3: Feature Engineering & Normalization
        logger.info("⚙️ Step 3: Feature engineering & normalization...")
        
        # Assemble features for scaling
        assembler = VectorAssembler(
            inputCols=["Open", "High", "Low", "Close"], 
            outputCol="features_vec"
        )
        vec_df = assembler.transform(df_clean)
        
        # Apply MinMaxScaler
        minmax_scaler = MinMaxScaler(inputCol="features_vec", outputCol="scaled_minmax")
        scaler_model_minmax = minmax_scaler.fit(vec_df)
        df_scaled = scaler_model_minmax.transform(vec_df)
        
        logger.info("✅ Applied MinMaxScaler normalization")
        
        # Step 4: Anomaly Detection
        logger.info("🚨 Step 4: Anomaly detection...")
        
        # Calculate percentage change
        windowSpec = Window.orderBy("Date")
        
        df_anomaly = df_scaled.withColumn(
            "prev_close", lag("Close").over(windowSpec)
        ).withColumn(
            "percent_change", 
            when(col("prev_close").isNotNull(),
                 ((col("Close") - col("prev_close")) / col("prev_close")) * 100)
            .otherwise(0)
        )
        
        # Calculate Z-score
        stats = df_anomaly.select(mean("Close").alias("mean"), stddev("Close").alias("std")).first()
        mean_val = stats["mean"]
        std_val = stats["std"]
        
        df_anomaly = df_anomaly.withColumn(
            "z_score", 
            (col("Close") - mean_val) / std_val
        )
        
        # Detect anomalies
        threshold_z = 3.0
        df_anomaly = df_anomaly.withColumn(
            "Anomaly",
            when(
                (spark_abs(col("percent_change")) > threshold_percent) | 
                (spark_abs(col("z_score")) > threshold_z),
                1
            ).otherwise(0)
        )
        
        anomaly_count = df_anomaly.filter(col("Anomaly") == 1).count()
        total_records = df_anomaly.count()
        
        logger.info(f"✅ Anomaly detection completed")
        logger.info(f"   Total records: {total_records}")
        logger.info(f"   Anomalies found: {anomaly_count}")
        logger.info(f"   Anomaly rate: {(anomaly_count/total_records*100):.2f}%")
        
        # Step 5: Price Prediction (Next 7 Days)
        logger.info("🔮 Step 5: Stock price prediction...")
        
        # Prepare data for Linear Regression
        df_pred = df_anomaly.withColumn(
            "day_index", 
            col("Date").cast("timestamp").cast("long") / 86400
        )
        
        # Assemble features for prediction
        pred_assembler = VectorAssembler(inputCols=["day_index"], outputCol="features")
        train_df = pred_assembler.transform(df_pred).select("features", "Close")
        
        # Train Linear Regression model
        lr = LinearRegression(featuresCol="features", labelCol="Close")
        lr_model = lr.fit(train_df)
        
        logger.info(f"✅ Trained Linear Regression model")
        logger.info(f"   Intercept: {lr_model.intercept:.4f}")
        logger.info(f"   Coefficient: {lr_model.coefficients[0]:.4f}")
        
        # Generate predictions for next 7 days
        last_date_row = df_pred.select(col("Date"), col("day_index")).orderBy(col("Date").desc()).first()
        last_date = last_date_row["Date"]
        last_index = last_date_row["day_index"]
        
        # Create future dates
        future_data = []
        for i in range(1, 8):
            future_date = last_date + datetime.timedelta(days=i)
            future_index = last_index + i
            future_data.append((future_date, float(future_index)))
        
        future_df = spark.createDataFrame(future_data, ["Date", "day_index"])
        future_assembled = pred_assembler.transform(future_df)
        
        # Make predictions
        predictions = lr_model.transform(future_assembled).select(
            "Date", 
            col("prediction").alias("Predicted_Close")
        )
        
        predictions_pandas = predictions.toPandas()
        logger.info(f"✅ Generated 7-day price predictions")
        
        # Step 6: Prepare results
        logger.info("📦 Step 6: Preparing results...")
        
        # Convert to Pandas
        result_df = df_anomaly.select(
            "Date", "Open", "High", "Low", "Close", "Volume",
            "percent_change", "z_score", "Anomaly"
        ).toPandas()
        
        # Get anomalies only
        anomalies_df = result_df[result_df["Anomaly"] == 1].copy()
        
        # Unpersist cache
        df_spark.unpersist()
        
        logger.info("=" * 60)
        logger.info("✅ SPARK JOB COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"🌐 View Spark Web UI at: {_spark_ui_url}")
        logger.info("=" * 60)
        
        return {
            'success': True,
            'data': result_df.to_dict('records'),
            'anomalies': anomalies_df.to_dict('records'),
            'predictions': predictions_pandas.to_dict('records'),
            'summary': {
                'total_records': total_records,
                'anomalies_found': int(anomaly_count),
                'anomaly_rate': f"{(anomaly_count/total_records*100):.2f}%",
                'duplicates_removed': duplicates_removed,
                'mean_price': float(mean_val),
                'std_price': float(std_val),
                'threshold_percent': threshold_percent,
                'threshold_z': threshold_z
            },
            'model_info': {
                'intercept': float(lr_model.intercept),
                'coefficient': float(lr_model.coefficients[0]),
                'rmse': float(lr_model.summary.rootMeanSquaredError) if hasattr(lr_model, 'summary') else None
            },
            'spark_ui_url': _spark_ui_url,
            'app_id': _spark_session.sparkContext.applicationId
        }
        
    except Exception as e:
        logger.error(f"❌ Spark job failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


def ensure_spark_ui_running():
    """
    Ensure that Spark Web UI is running and accessible.
    
    Returns:
        dict: Status information about the Spark UI
    """
    global _spark_session, _spark_ui_url
    
    status = {
        'ui_running': False,
        'ui_url': None,
        'session_active': False,
        'error': None,
        'app_id': None,
        'app_name': None
    }
    
    try:
        # Check if Spark session exists
        if _spark_session is None:
            _spark_session = create_spark_session()
        
        if _spark_session is not None:
            status['session_active'] = True
            status['ui_running'] = True
            status['ui_url'] = _spark_ui_url or f"http://localhost:{_spark_ui_port}"
            status['app_id'] = _spark_session.sparkContext.applicationId
            status['app_name'] = _spark_session.sparkContext.appName
            
            # Try to ping the UI
            try:
                response = requests.get(status['ui_url'], timeout=2)
                if response.status_code == 200:
                    logger.info(f"✅ Spark Web UI is accessible at {status['ui_url']}")
                else:
                    logger.warning(f"⚠️ Spark UI returned status code: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"⚠️ Spark UI may not be fully accessible: {e}")
        else:
            status['error'] = "Could not create Spark session"
            
    except Exception as e:
        status['error'] = str(e)
        logger.error(f"Error checking Spark UI status: {e}")
    
    return status


def stop_spark_session():
    """
    Stop the active Spark session and clean up resources.
    """
    global _spark_session, _spark_ui_url
    
    if _spark_session is not None:
        try:
            logger.info("Stopping Spark session...")
            _spark_session.stop()
            _spark_session = None
            _spark_ui_url = None
            logger.info("✅ Spark session stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping Spark session: {e}")


def get_spark_metrics():
    """
    Get comprehensive Spark metrics for monitoring.
    
    Returns:
        dict: Spark metrics information
    """
    global _spark_session
    
    metrics = {
        'session_active': _spark_session is not None,
        'ui_url': _spark_ui_url,
        'ui_port': _spark_ui_port,
        'app_name': None,
        'app_id': None,
        'master': None,
        'executors': 0,
        'active_jobs': 0,
        'completed_jobs': 0,
        'active_stages': 0,
        'completed_stages': 0
    }
    
    if _spark_session is not None:
        try:
            sc = _spark_session.sparkContext
            metrics['app_name'] = sc.appName
            metrics['app_id'] = sc.applicationId
            metrics['master'] = sc.master
            
            # Get job and stage information
            status_tracker = sc.statusTracker()
            if status_tracker:
                active_job_ids = status_tracker.getActiveJobIds()
                metrics['active_jobs'] = len(active_job_ids) if active_job_ids else 0
                
                active_stage_ids = status_tracker.getActiveStageIds()
                metrics['active_stages'] = len(active_stage_ids) if active_stage_ids else 0
                
        except Exception as e:
            logger.warning(f"Could not get Spark metrics: {e}")
    
    return metrics


# Flask Blueprint for Spark UI integration
from flask import Blueprint, jsonify, redirect, url_for, render_template

spark_ui = Blueprint('spark_ui', __name__)


@spark_ui.route('/spark-ui')
def spark_ui_page():
    """
    Render Spark UI monitoring page.
    """
    ui_status = ensure_spark_ui_running()
    metrics = get_spark_metrics()
    return render_template('spark_ui.html', status=ui_status, metrics=metrics)


@spark_ui.route('/spark-ui/redirect')
def spark_ui_redirect():
    """
    Redirect to Spark Web UI if available.
    """
    ui_status = ensure_spark_ui_running()
    
    if ui_status['ui_running'] and ui_status['ui_url']:
        return redirect(ui_status['ui_url'])
    else:
        return jsonify({
            'error': 'Spark Web UI is not available',
            'status': ui_status,
            'message': 'Please ensure Spark session is running. Try analyzing data first.'
        }), 503


@spark_ui.route('/api/spark-status')
def spark_status():
    """
    API endpoint to get Spark status information.
    """
    ui_status = ensure_spark_ui_running()
    metrics = get_spark_metrics()
    
    return jsonify({
        'ui_status': ui_status,
        'metrics': metrics,
        'spark_ui_port': _spark_ui_port,
        'direct_link': f"http://localhost:{_spark_ui_port}"
    })


@spark_ui.route('/api/spark-start')
def spark_start():
    """
    API endpoint to start Spark session.
    """
    try:
        session = create_spark_session()
        if session:
            return jsonify({
                'success': True,
                'message': 'Spark session started successfully',
                'ui_url': _spark_ui_url,
                'app_id': session.sparkContext.applicationId
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


@spark_ui.route('/api/spark-stop')
def spark_stop():
    """
    API endpoint to stop Spark session.
    """
    try:
        stop_spark_session()
        return jsonify({
            'success': True,
            'message': 'Spark session stopped successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # Test Spark session creation and run a sample job
    print("=" * 60)
    print("Testing Spark Session Creation & Anomaly Detection")
    print("=" * 60)
    
    session = create_spark_session()
    
    if session:
        print("\n✅ Spark session created successfully!")
        print(f"🌐 Spark Web UI: {_spark_ui_url}")
        print(f"📊 Application Name: {session.sparkContext.appName}")
        print(f"🔑 Application ID: {session.sparkContext.applicationId}")
        print(f"\n🌐 Open in browser: http://localhost:{_spark_ui_port}")
        
        # Test with sample data
        print("\n" + "=" * 60)
        print("Running Test Job with Sample Data")
        print("=" * 60)
        
        try:
            # Load sample data
            sample_file = os.path.join(os.path.dirname(__file__), '..', 'GOOGL.csv')
            if os.path.exists(sample_file):
                df_sample = pd.read_csv(sample_file)
                print(f"\n✅ Loaded sample data: {len(df_sample)} records")
                
                # Run anomaly detection
                result = run_anomaly_detection_job(df_sample, threshold_percent=5.0)
                
                if result and result['success']:
                    print("\n" + "=" * 60)
                    print("JOB RESULTS")
                    print("=" * 60)
                    print(f"Total Records: {result['summary']['total_records']}")
                    print(f"Anomalies Found: {result['summary']['anomalies_found']}")
                    print(f"Anomaly Rate: {result['summary']['anomaly_rate']}")
                    print(f"\n📊 View detailed metrics in Spark Web UI:")
                    print(f"   {result['spark_ui_url']}")
                else:
                    print("\n❌ Job failed")
            else:
                print(f"\n⚠️ Sample file not found: {sample_file}")
                print("Spark session is running. You can view the Web UI.")
        except Exception as e:
            print(f"\n❌ Test job failed: {e}")
        
        print("\n" + "=" * 60)
        print("Press Ctrl+C to stop...")
        print("=" * 60)
        
        try:
            # Keep running to maintain Web UI
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping Spark session...")
            stop_spark_session()
            print("✅ Cleanup complete")
    else:
        print("\n❌ Failed to create Spark session")
