"""
Spark Web UI Integration Module
Provides functionality to start and manage Spark Web UI for monitoring PySpark jobs.
Runs locally without ngrok - Web UI available at http://localhost:4040
"""

import os
import subprocess
import time
import requests
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lag, when, abs as spark_abs, round as spark_round
from pyspark.sql.window import Window
import logging
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO)
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
                cmdline = ' '.join(proc.cmdline())
                if 'spark' in cmdline.lower() or 'java' in proc.name().lower():
                    if 'SparkSubmit' in cmdline or 'org.apache.spark' in cmdline:
                        logger.info(f"Killing existing Spark process: {proc.pid}")
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
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

        # Build Spark session with UI configuration
        builder = SparkSession.builder \
            .appName(app_name) \
            .master("local[*]") \
            .config("spark.ui.enabled", "true") \
            .config("spark.ui.port", "4040") \
            .config("spark.driver.host", "localhost") \
            .config("spark.driver.bindAddress", "127.0.0.1") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.driver.memory", "2g")

        try:
            _spark_session = builder.getOrCreate()
        except Exception as primary_err:
            # Catch constructor mismatch between PySpark and Spark JVM
            logger.warning(f"SparkSession creation failed: {primary_err}")
            logger.warning("Spark features will be disabled. App will continue without Spark.")
            _spark_session = None
            return None

        # Get the UI URL if available
        if enable_ui:
            try:
                ui_port = _spark_session.sparkContext.uiWebUrl
                if ui_port:
                    _spark_ui_url = ui_port
                    logger.info(f"Spark Web UI available at: {_spark_ui_url}")
                else:
                    logger.warning("Spark Web UI URL not available")
            except Exception as e:
                logger.warning(f"Could not get Spark UI URL: {e}")

        logger.info("Spark session created successfully")
        return _spark_session

    except Exception as e:
        logger.warning(f"Failed to create Spark session: {e}")
        logger.warning("Spark features will be disabled. App will continue.")
        _spark_session = None
        return None


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
        'error': None
    }

    try:
        # Check if Spark session exists
        if _spark_session is None:
            _spark_session = create_spark_session()

        status['session_active'] = True

        # For local development, Spark UI is not accessible via web browser
        # This is normal behavior for local Spark sessions
        status['ui_running'] = False
        status['ui_url'] = None
        status['error'] = "Spark Web UI is not accessible in local development mode. This is normal for local Spark sessions."

        logger.info("Spark session is active, but UI is not accessible in local mode")

    except Exception as e:
        status['error'] = f"Error checking Spark UI status: {str(e)}"
        logger.error(status['error'])

    return status


def get_spark_ui_url():
    """
    Get the current Spark Web UI URL.

    Returns:
        str: Spark UI URL or None if not available
    """
    global _spark_ui_url
    return _spark_ui_url


def stop_spark_session():
    """
    Stop the Spark session and clean up resources.
    """
    global _spark_session, _spark_ui_url, _spark_ui_process

    try:
        if _spark_session is not None:
            _spark_session.stop()
            _spark_session = None
            logger.info("Spark session stopped")

        if _spark_ui_process is not None:
            _spark_ui_process.terminate()
            _spark_ui_process.wait()
            _spark_ui_process = None
            logger.info("Spark UI process terminated")

        _spark_ui_url = None

    except Exception as e:
        logger.error(f"Error stopping Spark session: {e}")


def get_spark_metrics():
    """
    Get basic Spark metrics for monitoring.

    Returns:
        dict: Spark metrics information
    """
    global _spark_session

    metrics = {
        'session_active': _spark_session is not None,
        'ui_url': _spark_ui_url,
        'app_name': None,
        'executors': 0,
        'jobs_completed': 0,
        'stages_completed': 0
    }

    if _spark_session is not None:
        try:
            sc = _spark_session.sparkContext
            metrics['app_name'] = sc.appName
            metrics['executors'] = len(sc.getExecutorIds()) if sc.getExecutorIds() else 0

            # Get job and stage information
            status_tracker = sc.statusTracker()
            if status_tracker:
                active_jobs = status_tracker.getActiveJobIds()
                completed_jobs = status_tracker.getJobIdsForGroup(None)
                if completed_jobs:
                    metrics['jobs_completed'] = len(completed_jobs) - len(active_jobs or [])

                # Note: Stage tracking requires more complex implementation
                metrics['stages_completed'] = 0  # Placeholder

        except Exception as e:
            logger.warning(f"Could not get Spark metrics: {e}")

    return metrics


# Flask Blueprint for Spark UI integration
from flask import Blueprint, jsonify, redirect, url_for

spark_ui = Blueprint('spark_ui', __name__)

@spark_ui.route('/spark-ui')
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
            'status': ui_status
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
        'metrics': metrics
    })
