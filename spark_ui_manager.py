# -*- coding: utf-8 -*-
"""
Standalone Spark Web UI Manager
Manages Spark session, executes jobs, and provides Web UI access
No ngrok dependency - runs purely locally at http://localhost:4040
"""

import os
import sys
import time
import logging
import pandas as pd
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lag, when, abs as spark_abs, mean, stddev
from pyspark.sql.window import Window
from pyspark.ml.regression import LinearRegression
from pyspark.ml.feature import VectorAssembler, MinMaxScaler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global Spark session
_spark_session = None
_spark_ui_port = 4040
_spark_ui_url = None


def create_spark_session(auto_trigger_job=True):
    """
    Create Spark session with Web UI enabled.
    Optionally auto-triggers anomaly detection job.
    
    Args:
        auto_trigger_job: If True, automatically runs anomaly detection on GOOGL.csv
    
    Returns SparkSession or None if failed.
    """
    global _spark_session, _spark_ui_url, _spark_ui_port
    
    if _spark_session is not None:
        logger.info("Spark session already exists")
        return _spark_session
    
    try:
        logger.info("=" * 60)
        logger.info("🔥 CREATING SPARK SESSION WITH WEB UI")
        logger.info("=" * 60)
        
        # Set Python executable path for Windows
        python_exe = sys.executable
        os.environ['PYSPARK_PYTHON'] = python_exe
        os.environ['PYSPARK_DRIVER_PYTHON'] = python_exe
        logger.info(f"Using Python: {python_exe}")
        
        # Stop any existing sessions
        try:
            from pyspark import SparkContext
            sc = SparkContext._active_spark_context
            if sc is not None:
                sc.stop()
                time.sleep(1)
        except:
            pass
        
        # Create new session with UI enabled
        _spark_session = SparkSession.builder \
            .appName("StockAnalytics_WebUI") \
            .master("local[*]") \
            .config("spark.ui.enabled", "true") \
            .config("spark.ui.port", str(_spark_ui_port)) \
            .config("spark.driver.host", "localhost") \
            .config("spark.driver.bindAddress", "127.0.0.1") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.driver.memory", "2g") \
            .config("spark.sql.shuffle.partitions", "4") \
            .config("spark.python.worker.reuse", "true") \
            .getOrCreate()
        
        # Get UI URL
        _spark_ui_url = f"http://localhost:{_spark_ui_port}"
        
        logger.info(f"✅ Spark session created successfully!")
        logger.info(f"📊 Application Name: {_spark_session.sparkContext.appName}")
        logger.info(f"🔑 Application ID: {_spark_session.sparkContext.applicationId}")
        logger.info(f"🌐 Spark Web UI: {_spark_ui_url}")
        logger.info("=" * 60)
        
        # Auto-trigger job if requested
        if auto_trigger_job:
            logger.info("\n🚀 AUTO-TRIGGERING ANOMALY DETECTION JOB...")
            # Find GOOGL.csv in parent directory
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(backend_dir)
            csv_path = os.path.join(parent_dir, 'GOOGL.csv')
            
            if os.path.exists(csv_path):
                logger.info(f"📂 Using data file: {csv_path}")
                # Execute job in background (don't block session creation)
                import threading
                job_thread = threading.Thread(
                    target=execute_anomaly_detection_job,
                    args=(csv_path,),
                    daemon=True
                )
                job_thread.start()
                logger.info("✅ Background job started successfully")
            else:
                logger.warning(f"⚠️  GOOGL.csv not found at {csv_path}. Skipping auto-trigger.")
        
        return _spark_session
        
    except Exception as e:
        logger.error(f"❌ Failed to create Spark session: {e}")
        return None


def get_spark_session():
    """Get active Spark session, create if needed."""
    global _spark_session
    if _spark_session is None:
        _spark_session = create_spark_session()
    return _spark_session


def execute_anomaly_detection_job(file_path, threshold_percent=5.0):
    """
    Execute complete anomaly detection job with Spark.
    
    Args:
        file_path: Path to CSV file
        threshold_percent: Anomaly threshold (default 5%)
    
    Returns:
        dict: Results with anomalies, predictions, and statistics
    """
    spark = get_spark_session()
    
    if spark is None:
        return {
            'success': False,
            'error': 'Spark session not available'
        }
    
    try:
        logger.info("=" * 60)
        logger.info("🚀 STARTING SPARK JOB: ANOMALY DETECTION")
        logger.info("=" * 60)
        
        # Load data
        logger.info(f"📥 Loading data from: {file_path}")
        df_pandas = pd.read_csv(file_path)
        initial_count = len(df_pandas)
        logger.info(f"✅ Loaded {initial_count} records")
        
        # Convert to Spark DataFrame
        logger.info("🔄 Converting to Spark DataFrame...")
        df_spark = spark.createDataFrame(df_pandas)
        df_spark.cache()
        
        # Data cleaning
        logger.info("🧹 Cleaning data...")
        df_clean = df_spark.dropDuplicates(["Date"])
        df_clean = df_clean.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
        df_clean = df_clean.filter(
            (col("Open") > 0) & (col("High") > 0) & 
            (col("Low") > 0) & (col("Close") > 0)
        )
        
        # Remove outliers
        quantiles = df_clean.approxQuantile("Close", [0.25, 0.75], 0.0)
        q1, q3 = quantiles[0], quantiles[1]
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        df_clean = df_clean.filter(
            (col("Close") >= lower_bound) & (col("Close") <= upper_bound)
        )
        
        clean_count = df_clean.count()
        logger.info(f"✅ Cleaned: {clean_count} records (removed {initial_count - clean_count})")
        
        # Anomaly Detection
        logger.info("🚨 Detecting anomalies...")
        windowSpec = Window.orderBy("Date")
        
        df_anomaly = df_clean.withColumn(
            "prev_close", lag("Close").over(windowSpec)
        ).withColumn(
            "percent_change",
            when(col("prev_close").isNotNull(),
                 ((col("Close") - col("prev_close")) / col("prev_close")) * 100)
            .otherwise(0)
        )
        
        # Z-score calculation
        stats = df_anomaly.select(
            mean("Close").alias("mean"),
            stddev("Close").alias("std")
        ).first()
        mean_val = stats["mean"]
        std_val = stats["std"]
        
        df_anomaly = df_anomaly.withColumn(
            "z_score",
            (col("Close") - mean_val) / std_val
        ).withColumn(
            "IsAnomaly",
            when(
                (spark_abs(col("percent_change")) > threshold_percent) |
                (spark_abs(col("z_score")) > 3.0),
                True
            ).otherwise(False)
        )
        
        anomaly_count = df_anomaly.filter(col("IsAnomaly") == True).count()
        total_records = df_anomaly.count()
        
        logger.info(f"✅ Anomalies detected: {anomaly_count} / {total_records}")
        logger.info(f"   Anomaly rate: {(anomaly_count/total_records*100):.2f}%")
        
        # Price Prediction
        logger.info("🔮 Generating price predictions...")
        df_pred = df_anomaly.withColumn(
            "day_index",
            col("Date").cast("timestamp").cast("long") / 86400
        )
        
        assembler = VectorAssembler(inputCols=["day_index"], outputCol="features")
        train_df = assembler.transform(df_pred).select("features", "Close")
        
        lr = LinearRegression(featuresCol="features", labelCol="Close")
        lr_model = lr.fit(train_df)
        
        # Get last date and predict 7 days
        last_row = df_pred.select("Date", "day_index").orderBy(col("Date").desc()).first()
        last_date = last_row["Date"]
        last_index = last_row["day_index"]
        
        future_data = []
        for i in range(1, 8):
            future_date = pd.to_datetime(last_date) + pd.Timedelta(days=i)
            future_index = float(last_index + i)
            future_data.append((future_date, future_index))
        
        future_df = spark.createDataFrame(future_data, ["Date", "day_index"])
        future_assembled = assembler.transform(future_df)
        predictions = lr_model.transform(future_assembled).select(
            "Date",
            col("prediction").alias("Predicted_Close")
        )
        
        predictions_pandas = predictions.toPandas()
        logger.info(f"✅ Generated 7-day predictions")
        
        # Convert results to Pandas
        result_df = df_anomaly.select(
            "Date", "Open", "High", "Low", "Close", "Volume",
            "percent_change", "z_score", "IsAnomaly"
        ).toPandas()
        
        anomalies_df = result_df[result_df["IsAnomaly"] == True].copy()
        
        # Unpersist cache
        df_spark.unpersist()
        
        logger.info("=" * 60)
        logger.info("✅ SPARK JOB COMPLETED SUCCESSFULLY")
        logger.info(f"🌐 View Spark Web UI at: {_spark_ui_url}")
        logger.info("=" * 60)
        
        return {
            'success': True,
            'data': result_df,
            'anomalies': anomalies_df,
            'predictions': predictions_pandas,
            'summary': {
                'total_records': int(total_records),
                'anomalies_found': int(anomaly_count),
                'anomaly_rate': f"{(anomaly_count/total_records*100):.2f}%",
                'mean_price': float(mean_val),
                'std_price': float(std_val),
                'threshold_percent': threshold_percent
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


def get_spark_status():
    """
    Get current Spark session status.
    
    Returns:
        dict: Status information
    """
    global _spark_session, _spark_ui_url
    
    status = {
        'session_active': _spark_session is not None,
        'ui_url': _spark_ui_url,
        'ui_port': _spark_ui_port,
        'app_name': None,
        'app_id': None
    }
    
    if _spark_session:
        try:
            status['app_name'] = _spark_session.sparkContext.appName
            status['app_id'] = _spark_session.sparkContext.applicationId
        except:
            pass
    
    return status


def stop_spark_session():
    """Stop the Spark session."""
    global _spark_session, _spark_ui_url
    
    if _spark_session:
        try:
            logger.info("Stopping Spark session...")
            _spark_session.stop()
            _spark_session = None
            _spark_ui_url = None
            logger.info("✅ Spark session stopped")
        except Exception as e:
            logger.error(f"Error stopping Spark: {e}")


if __name__ == '__main__':
    """Test the Spark UI manager"""
    print("=" * 60)
    print("TESTING SPARK WEB UI MANAGER")
    print("=" * 60)
    
    # Create session
    session = create_spark_session()
    
    if session:
        print(f"\n✅ Spark Web UI is running at: {_spark_ui_url}")
        print("\nTest with sample data:")
        
        # Find sample file
        sample_file = os.path.join(os.path.dirname(__file__), '..', 'GOOGL.csv')
        if os.path.exists(sample_file):
            print(f"Running job with: {sample_file}")
            
            result = execute_anomaly_detection_job(sample_file, threshold_percent=5.0)
            
            if result['success']:
                print(f"\n✅ Job completed successfully!")
                print(f"   Total records: {result['summary']['total_records']}")
                print(f"   Anomalies: {result['summary']['anomalies_found']}")
                print(f"   Spark UI: {result['spark_ui_url']}")
            else:
                print(f"\n❌ Job failed: {result.get('error')}")
        
        print("\n" + "=" * 60)
        print("Spark Web UI is running. Press Ctrl+C to stop...")
        print("=" * 60)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping...")
            stop_spark_session()
            print("✅ Done")
    else:
        print("\n❌ Failed to create Spark session")
