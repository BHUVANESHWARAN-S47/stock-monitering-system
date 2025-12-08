## 📊 Stock Analytics Dashboard - Chart Reference

### Chart Layout Overview
```
┌─────────────────────────────────────────────────────────────────┐
│                     STOCK ANALYTICS                             │
│        Real-time Price Monitoring and Anomaly Detection         │
│                                                                 │
│   Highest Price: $237.4        Lowest Price: $108.2            │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────┬──────────────────────────────┐
│  📈 Daily Close Price        │  📊 Daily High and Low       │
│                              │                              │
│  [Red line with trendline]   │  [High line (red)]           │
│  [Shows anomalies as X]      │  [Low line (grey)]           │
│                              │                              │
└──────────────────────────────┴──────────────────────────────┘

┌──────────────────────────────┬──────────────────────────────┐
│  📊 Daily Volume             │  % Change Open & Close       │
│                              │                              │
│  [Grey bars]                 │  [Green bars for positive]   │
│  [Annotations for max/min]   │  [Red bars for negative]     │
│                              │  [Annotations for extremes]  │
└──────────────────────────────┴──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                Stock Price Prediction (7 Days)                  │
│                                                                 │
│  [Blue solid line: Last 10 actual days]                         │
│  [Green dotted line with diamonds: 7-day forecast]              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 📋 Chart Details

#### Chart 1: Daily Close Price
```
Features:
• Red line (#E85D5D) showing historical close prices
• Grey dashed trendline showing overall direction
• Red X markers highlighting detected anomalies
• Smooth line for professional appearance
• Hover shows: Date and Close Price

Example:
Date: 2024-01-15
Close: $182.50
[Anomaly marker if > threshold]
```

#### Chart 2: Daily High and Low
```
Features:
• Two lines showing price range each day
• High prices in red (#E85D5D)
• Low prices in grey (#A3A3A3)
• Shows trading range volatility
• Hover shows: High and Low values

Example:
Date: 2024-01-15
High: $185.20
Low: $180.10
Range: $5.10
```

#### Chart 3: Daily Volume
```
Features:
• Bar chart with grey gradient colors
• Maximum volume: Darkest bar with annotation
• Minimum volume: Lightest bar with annotation
• Clear volume trends visible
• Hover shows: Date and Volume

Example:
Date: 2024-01-15
Volume: 125,432,789
[Annotation: "221,923,313" on highest bar]
[Annotation: "50,872,789" on lowest bar]
```

#### Chart 4: % Change Between Open & Close
```
Features:
• Bar chart showing daily % change
• Green bars (#4CAF50) = price increased
• Red bars (#E85D5D) = price decreased
• Max positive change annotated (e.g., +6.78%)
• Max negative change annotated (e.g., -7.96%)
• Hover shows: Date and % Change

Example:
Date: 2024-01-15
Open: $180.00
Close: $182.50
Change: +1.39% [GREEN bar]
```

#### Chart 5: Stock Price Prediction
```
Features:
• Last 10 days actual (blue solid line)
• Next 7 days predicted (green dotted line)
• Diamond markers on predictions
• Upward/Downward trend indicator
• Hover shows: Date and Price

Example:
Last Actual: 2024-03-12 @ $182.50
Predictions:
  2024-03-13: $183.20 (Upward Trend)
  2024-03-14: $183.90
  ...
  2024-03-19: $187.40
```

### 🎨 Color Reference

```css
/* Primary Colors */
Chart Lines (Red):    #E85D5D
Trendline (Grey):     #999999 (dashed)
High/Low Line (Grey): #A3A3A3

/* Volume Colors */
Default Bar:          #666666
Maximum Bar:          #333333 (darker)
Minimum Bar:          #AAAAAA (lighter)

/* % Change Colors */
Positive (Green):     #4CAF50
Negative (Red):       #E85D5D

/* Predictions */
Actual Line (Blue):   #667eea
Predicted (Green):    #48bb78 (dotted)

/* Background */
Chart Background:     #f8f9fa
Grid Lines:           lightgray
```

### 📏 Dimensions

```
Total Chart Height:   1400px
Layout:              3 rows × 2 columns
Row 1 (Charts 1-2):  35% height
Row 2 (Charts 3-4):  35% height
Row 3 (Chart 5):     30% height (full width)

Spacing:
Vertical spacing:    12%
Horizontal spacing:  12%
Container padding:   20px
```

### 🔍 Interactive Features

```
✓ Hover Tooltips
  - Shows exact values for data points
  - Unified hover mode (aligned across time)
  - Custom formatted values ($ for prices, % for changes)

✓ Zoom & Pan
  - Click and drag to zoom into specific date ranges
  - Double-click to reset zoom
  - Pan by dragging on the chart

✓ Legend
  - Click legend items to show/hide data series
  - Double-click to isolate single series
  - Positioned at bottom center

✓ Export
  - Built-in Plotly export to PNG
  - Camera icon in top-right of chart
  - High-resolution download
```

### 📊 Annotations

```
Maximum Volume:
├─ Position: On the highest bar
├─ Arrow: Points down to bar top
├─ Text: Formatted number (e.g., "221,923,313")
└─ Color: Black

Minimum Volume:
├─ Position: On the lowest bar
├─ Arrow: Points up to bar top
├─ Text: Formatted number (e.g., "50,872,789")
└─ Color: Black

Maximum Positive Change:
├─ Position: Top of highest green bar
├─ Arrow: Points down
├─ Text: Percentage (e.g., "+6.78%")
└─ Color: Dark green (#2E7D32)

Maximum Negative Change:
├─ Position: Bottom of lowest red bar
├─ Arrow: Points up
├─ Text: Percentage (e.g., "-7.96%")
└─ Color: Dark red (#C62828)
```

### 📈 Data Flow

```
User Uploads CSV
      ↓
Processing with Pandas
      ↓
Anomaly Detection (% threshold)
      ↓
Trendline Calculation (polyfit)
      ↓
Max/Min Identification
      ↓
7-Day Prediction (linear regression)
      ↓
Chart Generation (Plotly)
      ↓
Interactive Dashboard Display
```

### 🎯 Key Metrics Display

```
┌─────────────────────────────────────────┐
│  📈                                     │
│  STOCK ANALYTICS                        │
│  Real-time Price Monitoring             │
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │   $237.4     │  │   $108.2     │   │
│  │Highest Price │  │Lowest Price  │   │
│  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────┘

Monthly Summary:
┌──────────────┐  ┌──────────────┐
│ 2024-01      │  │ 2024-03      │
│    $182      │  │      2       │
│  Avg Price   │  │  Anomalies   │
└──────────────┘  └──────────────┘
```

### 🚀 Usage Example

```python
# Upload your stock data CSV with columns:
Date, Open, High, Low, Close, Volume

# Example row:
2024-01-15, 180.00, 185.20, 179.50, 182.50, 125432789

# The dashboard will automatically:
1. Calculate % change between Open & Close
2. Detect anomalies based on threshold
3. Generate trendline for close prices
4. Find max/min volume with annotations
5. Find max positive/negative % changes
6. Predict next 7 days of prices
7. Display all in Tesla-style charts
```

### 📱 Responsive Design

```
Desktop (>1200px):
├─ Full 2-column layout
├─ All charts visible
└─ Optimal viewing experience

Tablet (768px-1200px):
├─ 2-column layout maintained
├─ Slightly smaller text
└─ Scrollable content

Mobile (<768px):
├─ Single column layout
├─ Charts stack vertically
├─ Touch-friendly interactions
└─ Optimized for portrait view
```

### 🎨 Tesla-Style Elements

```
✓ Bold Header Typography
  - Uppercase titles
  - Letter-spacing: 2px
  - Font weight: 700

✓ Professional Color Palette
  - Red for prices (#E85D5D)
  - Grey for neutrals (#999, #666, #A3A3A3)
  - Green for positives (#4CAF50)

✓ Clean Grid Lines
  - Light grey (#lightgray)
  - Subtle but visible
  - Professional appearance

✓ Minimal Annotations
  - Only max/min values
  - No clutter
  - Clear and concise

✓ Dashed Trendline
  - Shows overall direction
  - Non-intrusive
  - Easy to interpret
```

### 🎯 Best Practices

```
Upload Guidelines:
• CSV format preferred
• Date format: YYYY-MM-DD
• Minimum 30 days of data recommended
• Include all columns: Date, Open, High, Low, Close, Volume

Threshold Setting:
• Default: 5% (recommended)
• Conservative: 3-4% (more anomalies)
• Aggressive: 6-8% (fewer anomalies)
• Adjust based on stock volatility

Viewing Tips:
• Use scroll-to-top button for navigation
• Hover over charts for exact values
• Zoom into specific date ranges
• Export charts for presentations
• Check anomalies table for details
```

---

**Dashboard created with ❤️ using Flask, Pandas, and Plotly**
