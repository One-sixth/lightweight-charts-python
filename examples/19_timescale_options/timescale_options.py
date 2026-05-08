"""
Example 19: time_scale() New Params (v5.0.9+ / v5.1.0+)
========================================================
Demonstrates:
  - right_offset_pixels    : right margin in pixels (v5.0.9+)
  - enable_conflation      : auto-merge large dataset (v5.1.0+)
  - conflation_threshold_factor / precompute_conflation_on_init

Run: python timescale_options.py
"""
import time

import pandas as pd
import numpy as np
from lightweight_charts import Chart


def generate_large_bars(num_bars=5000, freq='1min', start_price=100.0, seed=42):
    """Generate a large dataset to make conflation noticeable."""
    np.random.seed(seed)
    times = pd.date_range('2020-01-01', periods=num_bars, freq=freq)
    prices = start_price + np.cumsum(np.random.randn(num_bars) * 0.05)
    data = []
    for i, t in enumerate(times):
        base = prices[i]
        data.append({
            'time': t,
            'open':  base + np.random.randn() * 0.02,
            'high':  base + abs(np.random.randn()) * 0.1 + 0.05,
            'low':   base - abs(np.random.randn()) * 0.1 - 0.05,
            'close': base + np.random.randn() * 0.03,
            'volume': int(np.random.exponential(200)),
        })
    return pd.DataFrame(data)


if __name__ == '__main__':
    print("=" * 60)
    print(" Example 19: time_scale() New Params")
    print("=" * 60)

    chart = Chart(title='19 - time_scale() New Params', toolbox=True, maximize=True)
    chart.layout(background_color='#0e1117', text_color='#d1d4dc')
    chart.legend(visible=True, ohlc=True, persistent=True)

    # --- New time_scale params ---
    chart.time_scale(
        right_offset=3,
        right_offset_pixels=50,              # margin in pixels (v5.0.9+)
        enable_conflation=True,              # auto-merge large datasets (v5.1.0+)
        conflation_threshold_factor=2.0,     # higher = smoother zoom
        precompute_conflation_on_init=True,  # pre-calc at startup (uses memory)
    )
    print("[OK] time_scale() applied:")
    print("       right_offset_pixels = 50")
    print("       enable_conflation   = True")
    print("       conflation_threshold_factor = 2.0")
    print("       precompute_conflation_on_init = True")

    # --- Load large dataset ---
    df = generate_large_bars(5000)
    chart.set(df)
    print(f"[OK] {len(df)} bars loaded — zoom out to see conflation in action!")

    print("\n>>> Zoom out using mouse wheel or drag …")
    print("    Data points will automatically merge for smoother rendering.\n")

    chart.show(block=True)
