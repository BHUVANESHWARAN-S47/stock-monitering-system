# 🔥 Apache Spark Web UI Integration Guide

## Overview

This project now includes a **complete Apache Spark Web UI integration** that allows you to monitor PySpark jobs in real-time without using ngrok. The Web UI runs locally at `http://localhost:4040` and provides comprehensive monitoring of:

- Job execution and progress
- Stage details and task distribution
- Memory usage and storage
- Executor metrics and performance
- SQL query execution plans
- Environment configuration

## 🚀 Quick Start

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

**New dependencies added:**
- `psutil==5.9.5` - Process management for Spark session cleanup
- `requests==2.31.0` - HTTP requests for UI status checks
- `scikit-learn==1.3.0` - Machine learning for price predictions

### 2. Start the Application

```powershell
cd c:\Users\hyper\Desktop\project\stack\stack\backend
python app.py
```

### 3. Access the Spark Web UI Monitor

Open your browser and navigate to:
```
http://127.0.0.1:5000/spark-ui
```

### 4. Start Processing Data

- Click "View Analytics Dashboard" on the home page
- The Spark session will automatically start
- Spark Web UI becomes available at: `http://localhost:4040`

## 📁 New Files Created

### 1. `spark_web_ui_new.py`

**Location:** `backend/spark_web_ui_new.py`

**Purpose:** Complete Spark Web UI integration without ngrok

**Key Features:**
- ✅ Automatic Spark session creation
- ✅ Local Web UI at `http://localhost:4040`
- ✅ Process cleanup and management
- ✅ Real-time job monitoring
- ✅ Complete anomaly detection pipeline
- ✅ Machine learning price predictions (7 days)
- ✅ Data preprocessing and normalization
- ✅ Flask Blueprint for UI routes

**Main Functions:**

```python
# Create Spark session with Web UI
create_spark_session(app_name="StockAnomalyDetection", enable_ui=True)

# Run complete anomaly detection job
run_anomaly_detection_job(df_pandas, threshold_percent=5.0)

# Check Spark UI status
ensure_spark_ui_running()

# Get performance metrics
get_spark_metrics()

# Stop Spark session
stop_spark_session()
```

### 2. Updated `templates/spark_ui.html`

**Location:** `templates/spark_ui.html`

**Purpose:** Beautiful monitoring dashboard for Spark Web UI

**Features:**
- Real-time status display
- Session and performance metrics
- Direct link to Spark Web UI
- Auto-refresh every 10 seconds
- Comprehensive instructions
- Professional Tesla-style design

### 3. Updated `templates/index.html`

**Added:** Link to Spark Web UI monitor button on home page

## 🔧 How to Use the New Spark Web UI

### Method 1: Via Web Interface (Recommended)

1. **Start the Flask app:**
   ```powershell
   cd backend
   python app.py
   ```

2. **Open browser:** `http://127.0.0.1:5000`

3. **Click:** "🔥 View Spark Web UI Monitor" button

4. **Analyze data:** Click "View Analytics Dashboard"

5. **Access Spark UI:** Direct link appears on the monitoring page
   - Or go directly to `http://localhost:4040`

### Method 2: Test Spark Directly

Run the standalone Spark Web UI module:

```powershell
cd backend
python spark_web_ui_new.py
```

This will:
- ✅ Create a Spark session
- ✅ Start Web UI at `http://localhost:4040`
- ✅ Load sample data (`GOOGL.csv`)
- ✅ Run anomaly detection job
- ✅ Display results and metrics
- ✅ Keep Web UI running until Ctrl+C

**Expected Output:**
```
============================================================
Testing Spark Session Creation & Anomaly Detection
============================================================

✅ Spark session created successfully!
🌐 Spark Web UI: http://localhost:4040
📊 Application Name: StockAnomalyDetection
🔑 Application ID: local-1733...

============================================================
Running Test Job with Sample Data
============================================================

✅ Loaded sample data: 3272 records
🚀 STARTING SPARK ANOMALY DETECTION JOB
...
✅ SPARK JOB COMPLETED SUCCESSFULLY
============================================================
🌐 View Spark Web UI at: http://localhost:4040
============================================================

Press Ctrl+C to stop...
```

## 📊 What the Spark Job Does

The `run_anomaly_detection_job()` function performs a complete pipeline:

### Step 1: Data Loading
- Converts Pandas DataFrame to Spark DataFrame
- Caches data for performance

### Step 2: Data Preprocessing
- Removes duplicates by Date
- Removes null values
- Filters invalid prices (≤ 0)
- Removes outliers using IQR method

### Step 3: Feature Engineering & Normalization
- Vector assembly of features (Open, High, Low, Close)
- MinMaxScaler normalization
- StandardScaler with mean centering

### Step 4: Anomaly Detection
- **Percent change calculation** between consecutive Close prices
- **Z-score calculation** for statistical anomaly detection
- **Dual threshold detection:**
  - Percent change > 5% (configurable)
  - Z-score > 3.0 (statistical outlier)

### Step 5: Price Prediction
- Linear Regression model training
- 7-day future price predictions
- Model metrics (intercept, coefficient, RMSE)

### Step 6: Results
Returns comprehensive dictionary with:
- Processed data with anomaly flags
- List of detected anomalies
- 7-day price predictions
- Summary statistics
- Model information
- Spark UI URL and App ID

## 🌐 Spark Web UI Features

When you open `http://localhost:4040`, you'll see:

### Jobs Tab
- List of all Spark jobs
- Execution timeline
- Status and duration
- Stages per job

### Stages Tab
- Detailed stage information
- Task distribution
- Input/output data sizes
- Shuffle read/write

### Storage Tab
- Cached RDDs and DataFrames
- Memory usage
- Storage levels

### Environment Tab
- Spark configuration
- System properties
- Classpath entries

### Executors Tab
- Executor metrics
- Memory usage per executor
- Task execution statistics

### SQL Tab (if using SQL)
- Query execution plans
- Physical and logical plans
- Metrics per operation

## 🔍 Monitoring Your Jobs

### Real-time Monitoring

1. **Start a job** (analyze data)
2. **Open Spark UI** at `http://localhost:4040`
3. **Watch live progress:**
   - Active jobs appear immediately
   - Stages show task progress
   - Timeline visualization shows execution flow

### Key Metrics to Watch

- **Duration:** How long each job/stage takes
- **Shuffle Read/Write:** Data movement between stages
- **GC Time:** Garbage collection overhead
- **Task Metrics:** Min, median, max execution times

## 🛠️ Troubleshooting

### Issue: Spark UI not accessible

**Solution:**
1. Ensure you've run at least one analysis
2. Check if Spark session is active: `http://127.0.0.1:5000/api/spark-status`
3. Try accessing directly: `http://localhost:4040`

### Issue: Port 4040 already in use

**Solution:**
Spark automatically tries ports 4041, 4042, etc.
Check the console output for the actual port:
```
🌐 Spark Web UI available at: http://localhost:4041
```

### Issue: Java not found

**Solution:**
Install Java 11 and set JAVA_HOME:
```powershell
$env:JAVA_HOME="C:\Program Files\Java\jdk-11"
```

### Issue: PySpark import errors

**Solution:**
Reinstall dependencies:
```powershell
pip uninstall pyspark
pip install pyspark==3.4.1
```

## 📡 API Endpoints

### Check Spark Status
```
GET /api/spark-status
```

Response:
```json
{
  "ui_status": {
    "ui_running": true,
    "ui_url": "http://localhost:4040",
    "session_active": true,
    "app_id": "local-1733...",
    "app_name": "StockAnomalyDetection"
  },
  "metrics": {
    "session_active": true,
    "ui_url": "http://localhost:4040",
    "app_name": "StockAnomalyDetection",
    "active_jobs": 0,
    "active_stages": 0
  },
  "spark_ui_port": 4040,
  "direct_link": "http://localhost:4040"
}
```

### Start Spark Session
```
GET /api/spark-start
```

### Stop Spark Session
```
GET /api/spark-stop
```

## 🎯 Comparison: Before vs After

| Feature | Original | With Spark Web UI |
|---------|----------|-------------------|
| Processing | Pandas only | Spark + Pandas |
| Monitoring | None | Real-time Web UI |
| Scalability | Limited | Distributed |
| Job Tracking | Manual logs | Automatic UI |
| Performance Metrics | None | Comprehensive |
| Anomaly Detection | Basic | Advanced (dual threshold) |
| Predictions | None | 7-day ML predictions |
| Data Normalization | None | MinMax + Standard scaling |

## 🚀 Performance Benefits

### Spark Advantages:
1. **Distributed Processing:** Can scale to larger datasets
2. **In-Memory Caching:** Faster repeated operations
3. **Lazy Evaluation:** Optimized execution plans
4. **Built-in ML:** MLlib for predictions
5. **Real-time Monitoring:** Track job progress live

### When to Use Spark vs Pandas:
- **Use Spark:** Datasets > 1GB, need scalability, want monitoring
- **Use Pandas:** Small datasets, rapid prototyping, simple operations

## 📝 Code Examples

### Example 1: Process Data with Spark

```python
from backend.spark_web_ui_new import run_anomaly_detection_job
import pandas as pd

# Load your data
df = pd.read_csv('GOOGL.csv')

# Run Spark job
result = run_anomaly_detection_job(df, threshold_percent=5.0)

# Access results
if result['success']:
    print(f"Total records: {result['summary']['total_records']}")
    print(f"Anomalies found: {result['summary']['anomalies_found']}")
    print(f"Spark UI: {result['spark_ui_url']}")
    
    # Get predictions
    predictions = result['predictions']
    print(f"Next 7 days predictions: {predictions}")
```

### Example 2: Check Spark Status Programmatically

```python
from backend.spark_web_ui_new import ensure_spark_ui_running, get_spark_metrics

# Check status
status = ensure_spark_ui_running()
print(f"Spark running: {status['session_active']}")
print(f"Web UI: {status['ui_url']}")

# Get metrics
metrics = get_spark_metrics()
print(f"Active jobs: {metrics['active_jobs']}")
print(f"App ID: {metrics['app_id']}")
```

## 🎓 Learning Resources

### Understanding Spark Web UI:
1. **Jobs:** High-level operations triggered by actions (collect, count, save)
2. **Stages:** Sets of tasks that can run in parallel
3. **Tasks:** Individual units of work sent to executors
4. **Shuffle:** Data redistribution across partitions

### Optimization Tips:
1. Monitor shuffle operations (expensive)
2. Check for data skew in task durations
3. Tune partition counts for your data size
4. Cache DataFrames used multiple times
5. Avoid wide transformations when possible

## 🎉 Summary

You now have a **production-ready Spark Web UI integration** that:

✅ Runs locally without ngrok  
✅ Provides real-time job monitoring  
✅ Includes complete anomaly detection pipeline  
✅ Offers 7-day price predictions  
✅ Features beautiful monitoring dashboard  
✅ Works seamlessly with existing app  
✅ Includes comprehensive API endpoints  
✅ Provides detailed performance metrics  

**Access it at:** `http://127.0.0.1:5000/spark-ui`  
**Direct Spark UI:** `http://localhost:4040`

Happy monitoring! 🚀
