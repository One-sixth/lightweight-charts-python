"""
Example 22: pop() — Remove Data Points from the End (v5.0.9+)
==============================================================
Demonstrates removing the last N bars from the chart display.
Useful for dynamic dashboards where you want to trim old data.

Run: python pop.py
"""
import pandas as pd
import numpy as np
from time import sleep
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
    print(" Example 22: pop()")
    print("=" * 60)

    chart = Chart(title='22 - pop()', toolbox=True, maximize=True)
    chart.layout(background_color='#0e1117', text_color='#d1d4dc')
    chart.legend(visible=True, ohlc=True, persistent=True)

    chart.show(block=False)

    df = generate_bars(200)
    chart.set(df)
    print(f"[OK] {len(df)} bars loaded")

    # Remove bars in steps
    for n in [5, 20, 50]:
        sleep(2)
        print(f"\n>>> pop({n}) — removing last {n} bars …")
        chart.pop(n)

    print("\n[OK] Watch the chart shrink from the right!\n")
    chart.show(wait=120)
    chart.exit()
