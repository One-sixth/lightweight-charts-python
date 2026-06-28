"""
Example 20: tick_mark_density — Price Scale Label Spacing (v5.2.0+)
====================================================================
Demonstrates how tickMarkDensity controls the vertical spacing
between price-axis labels.  Higher values = more spacing, fewer labels.

This example switches between three densities so you can see the
difference directly.

Run: python tick_mark_density.py
"""
import pandas as pd
import numpy as np
from time import sleep
from lightweight_charts import Chart


def generate_bars(num_bars=200, freq='1h', start_price=100.0, seed=42):
    np.random.seed(seed)
    times = pd.date_range('2020-01-01', periods=num_bars, freq=freq)
    prices = start_price + np.cumsum(np.random.randn(num_bars) * 0.5)
    data = []
    for i, t in enumerate(times):
        base = prices[i]
        data.append({
            'time': t,
            'open':  base + np.random.randn() * 0.1,
            'high':  base + abs(np.random.randn()) * 0.8 + 0.2,
            'low':   base - abs(np.random.randn()) * 0.8 - 0.2,
            'close': base + np.random.randn() * 0.2,
            'volume': int(np.random.exponential(1000)),
        })
    return pd.DataFrame(data)


if __name__ == '__main__':
    print("=" * 60)
    print(" Example 20: tick_mark_density")
    print("=" * 60)

    chart = Chart(title='20 - tick_mark_density', toolbox=True)

    chart.show()

    chart.layout(background_color='#0e1117', text_color='#d1d4dc')
    chart.legend(visible=True, ohlc=True, persistent=True)

    df = generate_bars(200)
    chart.set(df)
    print(f"[OK] {len(df)} bars loaded")

    # --- Show three different densities ---
    for density, desc in [(1.0, "more labels"), (2.5, "default"), (6.0, "fewer labels")]:
        print(f"\n>>> tick_mark_density = {density} ({desc})")
        chart.price_scale(tick_mark_density=density)
        sleep(5)  # let user observe

    print("\n[OK] All three densities shown — compare the Y-axis label spacing!\n")
    chart.show(wait=120)
    chart.exit()
