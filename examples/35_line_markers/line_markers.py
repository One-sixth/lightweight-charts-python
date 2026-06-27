"""
Example 35: Line Series Markers
Demonstrates markers on Line and Histogram series (not just CandleSeries).

Usage:
    python examples/35_line_markers/line_markers.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
from lightweight_charts import Chart


def main():
    # Generate sample data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='D')

    # Main candle data
    close = 100 + np.cumsum(np.random.randn(100) * 2)
    high = close + np.abs(np.random.randn(100))
    low = close - np.abs(np.random.randn(100))
    open_ = close + np.random.randn(100) * 0.5
    volume = np.random.randint(1000, 10000, 100)

    candle_df = pd.DataFrame({
        'time': dates, 'open': open_, 'high': high, 'low': low,
        'close': close, 'volume': volume,
    })

    # SMA lines (use Series for rolling)
    close_s = pd.Series(close)
    sma20 = pd.DataFrame({'time': dates, 'SMA20': close_s.rolling(20).mean()})
    sma50 = pd.DataFrame({'time': dates, 'SMA50': close_s.rolling(50).mean()})

    # Volume histogram
    vol_df = pd.DataFrame({'time': dates, 'Volume': volume})

    # Create chart
    chart = Chart(width=1200, height=700, title='Line Series Markers Demo')
    chart.show(block=False)
    chart.legend(visible=True, ohlc=True, percent=True)

    # Set candle data
    chart.set(candle_df)

    # Create lines
    line20 = chart.create_line('SMA20', color='#2196F3', width=2)
    line50 = chart.create_line('SMA50', color='#FF9800', width=2)

    # Create histogram
    hist = chart.create_histogram('Volume', color='rgba(100,100,200,0.5)', pane_index=1)

    # Set line data
    line20.set(sma20)
    line50.set(sma50)
    hist.set(vol_df)

    # === Markers on CandleSeries (original) ===
    chart.marker(dates[10], 'below', 'arrow_up', '#4CAF50', 'Buy Signal')
    chart.marker(dates[50], 'above', 'arrow_down', '#F44336', 'Sell Signal')

    # === Markers on Line series (new!) ===
    line20.marker(dates[25], 'below', 'circle', '#2196F3', 'SMA20 Cross')
    line20.marker(dates[60], 'above', 'square', '#2196F3', 'SMA20 Peak')

    # === Markers on another Line ===
    line50.marker(dates[55], 'below', 'arrow_up', '#FF9800', 'SMA50 Support')

    # === Markers on Histogram (new!) ===
    hist.marker(dates[5], 'below', 'circle', '#9C27B0', 'Vol Spike')
    hist.marker(dates[80], 'below', 'square', '#9C27B0', 'Vol Drop')

    # === Batch markers on Line ===
    line20.marker_list([
        {'time': dates[35], 'position': 'below', 'shape': 'arrow_up',
         'color': '#00BCD4', 'text': 'Batch 1'},
        {'time': dates[45], 'position': 'above', 'shape': 'arrow_down',
         'color': '#00BCD4', 'text': 'Batch 2'},
    ])

    print("Markers created:")
    print(f"  Chart (CandleSeries): {len(chart.markers)} markers")
    print(f"  SMA20 (Line): {len(line20.markers)} markers")
    print(f"  SMA50 (Line): {len(line50.markers)} markers")
    print(f"  Volume (Histogram): {len(hist.markers)} markers")
    print()
    print("All markers should be visible on their respective series!")
    print("Close the window to exit.")

    chart.show(wait=120)
    chart.exit()


if __name__ == '__main__':
    main()
