# Stock Price Monitoring and Anomaly Detection with Tesla-Style Analytics

A professional web application that processes stock price data using **Pandas** to detect anomalies and visualize trends with **Tesla-inspired analytics dashboards**. Built with Flask, HTML/CSS, and interactive Plotly charts.

## 📘 Overview

This application allows users to:
- Upload stock datasets (CSV/JSON)
- Run intelligent anomaly detection analysis
- View results on **Tesla-style professional dashboards**
- Analyze with 5 interactive charts:
  - Daily Close Price with Trendline
  - Daily High and Low Prices
  - Trading Volume Analysis
  - % Change Between Open & Close
  - 7-Day Price Predictions
- Export anomaly alerts as CSV
- Get 7-day price forecasts using linear regression

## ⚙️ Tech Stack

- **Frontend**: HTML5 + CSS3 (Tesla-inspired responsive design)
- **Backend**: Flask (Python web framework)
- **Data Processing**: Pandas + NumPy (Windows-compatible)
- **Visualization**: Plotly (interactive charts)
- **Predictions**: Linear Regression (NumPy-based)
- **Charts**: Professional analytics matching Tesla dashboard style

## 🗂️ Project Structure

```
spark/
│
├── backend/
│   ├── app.py              # Flask server with routes
│   └── spark_job.py        # PySpark anomaly detection logic
│
├── templates/
│   ├── index.html          # Home page with upload form
│   └── dashboard.html      # Analysis dashboard
│
├── static/
│   └── styles.css          # CSS styling
│
├── data/
│   └── sample_stocks.csv   # Example stock dataset (not used)
│
├── GOOGL.csv               # Google stock data (13 years, 3271 days)
│
├── uploads/                # (Created automatically) User uploaded files
│
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🚀 Setup Instructions

### Prerequisites

- **Python 3.8+** installed on your system
- **Java 8 or 11** (required by Apache Spark)
- **pip** (Python package manager)

### Installation Steps (Windows PowerShell)

1. **Clone or navigate to the project directory**:
   ```powershell
   cd e:\xampp\htdocs\spark
   ```

2. **Create a virtual environment** (recommended):
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Verify Java installation** (required for PySpark):
   ```powershell
   java -version
   ```
   If Java is not installed, download and install [Java 11](https://adoptium.net/).

5. **Set JAVA_HOME environment variable** (if not already set):
   ```powershell
   $env:JAVA_HOME="C:\Program Files\Java\jdk-11"
   ```

## 🏃 Running the Application

1. **Navigate to the backend directory**:
   ```powershell
   cd backend
   ```

2. **Start the Flask server**:
   ```powershell
   python app.py
   ```

3. **Open your browser** and navigate to:
   ```
   http://127.0.0.1:5000
   ```

## 📊 Using the Application

### 1. Upload Data
- On the home page, click "Choose File" and select a CSV or JSON file
- Expected columns: `Date, Open, High, Low, Close, Volume`
- Set your anomaly detection threshold (default: 5%)
- Click "Upload & Analyze"

### 2. View Dashboard
- After processing, you'll be redirected to the dashboard
- View summary statistics (average price, total volume, anomaly count)
- Interactive chart shows stock prices with anomalies highlighted in red
- Scroll down to see a detailed table of detected anomalies

### 3. Export Results
- Click "Export Anomalies" to download a CSV file with all detected anomalies
- The file includes date, price, percent change, and anomaly type

### 4. Start New Analysis
- Click "New Analysis" to clear session and upload a new dataset

## 🧠 How It Works

### Data Processing Pipeline

1. **Data Loading**: PySpark reads CSV/JSON files into a DataFrame
2. **Data Cleaning**: 
   - Remove duplicates based on Date
   - Handle missing values
   - Ensure proper data types
3. **Anomaly Detection**:
   - Calculate day-to-day percentage change in closing price
   - Flag changes exceeding the threshold as anomalies
   - Classify as "Spike" (positive) or "Drop" (negative)
4. **Visualization**:
   - Generate interactive Plotly charts
   - Highlight anomalies in red
5. **Export**:
   - Convert results to Pandas DataFrame
   - Export as CSV for further analysis

### Anomaly Detection Logic

An anomaly is detected when:
```
|((Close_today - Close_yesterday) / Close_yesterday) * 100| > threshold
```

## 📝 Stock Data

The dashboard analyzes `GOOGL.csv` containing Google (GOOGL) stock data:
- **3,271 trading days** (2010-2022)
- **13 years** of comprehensive historical data
- Complete OHLCV data (Open, High, Low, Close, Adj Close, Volume)
- Multiple anomalies including:
  - Major market events
  - Earnings announcements
  - COVID-19 market crash and recovery
  - Tech sector volatility

## 🔧 Configuration

### Adjust Anomaly Threshold
- Modify the threshold in the upload form (UI)
- Or edit `app.py` line 82 to change the default:
  ```python
  threshold = float(request.form.get('threshold', 5.0))  # Change 5.0 to your default
  ```

### Spark Configuration
- Edit `spark_job.py` line 17-20 to adjust Spark memory:
  ```python
  .config("spark.driver.memory", "2g")  # Increase for larger datasets
  ```

## 🐛 Troubleshooting

### Issue: "Java not found"
**Solution**: Install Java 11 and set JAVA_HOME:
```powershell
$env:JAVA_HOME="C:\Program Files\Java\jdk-11"
```

### Issue: "Port 5000 already in use"
**Solution**: Change the port in `app.py` line 162:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Use different port
```

### Issue: Large file upload fails
**Solution**: Increase max file size in `app.py` line 22:
```python
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB
```

## 📚 Additional Notes

- **Performance**: PySpark runs in local mode with all available cores
- **Scalability**: Can be deployed to a Spark cluster for larger datasets
- **File Formats**: Supports CSV and JSON (add more in `spark_job.py`)
- **Academic Use**: Code is well-commented for learning purposes

## 🎯 Future Enhancements

- [ ] Support for real-time streaming data
- [ ] Machine learning-based anomaly detection
- [ ] Multiple stock comparison
- [ ] Docker containerization
- [ ] Streamlit alternative UI
- [ ] Database integration for historical analysis

## 📄 License

This project is for educational purposes. Feel free to modify and extend.

## 👨‍💻 Author

Built with Flask + PySpark | 2025

---

**Happy Analyzing! 📈**
