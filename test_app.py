"""
Quick test script to verify PySpark logic works correctly
Run this before starting the Flask app
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import spark_job

def test_spark_job():
    """Test the PySpark processing pipeline with sample data"""
    print("=" * 60)
    print("Testing PySpark Anomaly Detection")
    print("=" * 60)
    
    # Path to sample data
    sample_file = os.path.join(os.path.dirname(__file__), 'data', 'sample_stocks.csv')
    
    if not os.path.exists(sample_file):
        print(f"❌ Sample file not found: {sample_file}")
        return False
    
    print(f"✓ Found sample file: {sample_file}")
    print("\nProcessing with PySpark...")
    
    # Process the data
    result = spark_job.process_stock_data(sample_file, threshold_percent=5.0)
    
    if not result['success']:
        print(f"❌ Processing failed: {result.get('error')}")
        return False
    
    # Display results
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)
    summary = result['summary']
    print(f"Average Price:     ${summary['average_price']:.2f}")
    print(f"Total Volume:      {summary['total_volume']:,}")
    print(f"Anomalies Found:   {summary['anomaly_count']}")
    print(f"Price Range:       ${summary['min_price']:.2f} - ${summary['max_price']:.2f}")
    
    # Display anomalies
    anomalies = result['anomalies']
    if anomalies:
        print("\n" + "=" * 60)
        print(f"DETECTED ANOMALIES ({len(anomalies)} total)")
        print("=" * 60)
        for anomaly in anomalies:
            print(f"\nDate: {anomaly['Date']}")
            print(f"  Close Price:      ${anomaly['Close']:.2f}")
            print(f"  Previous Close:   ${anomaly.get('PrevClose', 0):.2f}")
            print(f"  Percent Change:   {anomaly['PercentChange']:.2f}%")
            print(f"  Type:             {anomaly['AnomalyType']}")
    else:
        print("\n✓ No anomalies detected (threshold: 5.0%)")
    
    print("\n" + "=" * 60)
    print("✓ Test completed successfully!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    try:
        success = test_spark_job()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
