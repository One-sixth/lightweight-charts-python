"""
Example 18: chart_options() — Compare hovered_series_on_top
============================================================
Left Chart:  hovered_series_on_top = False (default of older versions)
Right Chart: hovered_series_on_top = True  (v5.2.0+)

Move your mouse over the yellow SMA line in both charts to see the difference:
- Left side: the candles always stays behind the line.
- Right side: the candles rises above the line (when mouse hovered on candles).

Run: python chart_options.py
"""
import pandas as pd
import numpy as np
from lightweight_charts import Chart


def generate_bars(num_bars=200, freq='1h', start_price=100.0, seed=42):
    np.random.seed(seed)
    times = pd.date_range('2020-01-01', periods=num_bars, freq=freq)
    prices = start_price + np.cumsum(np.random.randn(num_bars) * 0.3)
    data = []
    for i, t in enumerate(times):
        base = prices[i]
        data.append({
            'time': t,
            'open':  base + np.random.randn() * 0.1,
            'high':  base + abs(np.random.randn()) * 0.5 + 0.1,
            'low':   base - abs(np.random.randn()) * 0.5 - 0.1,
            'close': base + np.random.randn() * 0.2,
            'volume': int(np.random.exponential(1000)),
        })
    return pd.DataFrame(data)


if __name__ == '__main__':
    print("=" * 60)
    print(" Example 18: Compare hovered_series_on_top")
    print("=" * 60)
    print("\nLeft chart:  hovered_series_on_top = False")
    print("Right chart: hovered_series_on_top = True")
    print("\n>>> Hover your mouse over the yellow SMA line in each pane.\n")

    # Create a main chart with two panes (left & right)

    # --- Left pane (hovered_series_on_top = False) ---
    left = Chart(title='18 - chart_options() Comparison left', toolbox=False, maximize=False)
    left.legend(visible=True, ohlc=True, lines=True, persistent=True)
    left.chart_options(hovered_series_on_top=False)   # explicit False
    left.time_scale(right_offset=5)
    left.price_scale(auto_scale=True)

    # --- Right pane (hovered_series_on_top = True) ---
    right = Chart(title='18 - chart_options() Comparison right', toolbox=False, maximize=False)
    left.legend(visible=True, ohlc=True, lines=True, persistent=True)
    right.chart_options(hovered_series_on_top=True)    # default True, but explicit
    right.time_scale(right_offset=5)
    right.price_scale(auto_scale=True)

    # Load same data into both panes
    df = generate_bars(200)
    left.set(df)
    right.set(df)

    # Add SMA line to both panes
    sma_values = df['close'].rolling(window=20).mean()
    sma_df = pd.DataFrame({'time': df['time'], 'value': sma_values})

    line_left = left.create_line('SMA 20', color='#f0c040', width=2, price_label=True)
    line_left.set(sma_df)

    line_right = right.create_line('SMA 20', color='#f0c040', width=2, price_label=True)
    line_right.set(sma_df)

    print("Both panes show the same K-line data + SMA 20.")
    print("Move mouse over the yellow line — only the right side lifts above candles.\n")



    left.show(block=False)
    right.show(block=True)
