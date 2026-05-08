"""
Example 21: marker_auto_scale() — Toggle Marker Auto-Scaling (v5.2.0)
======================================================================
设定自动缩放时，是否考虑标记的位置，默认是考虑的

Run: python marker_auto_scale.py
"""
import pandas as pd
import numpy as np
from lightweight_charts import Chart


def generate_bars(num_bars=200, freq='1h', start_price=100.0, seed=42):
    np.random.seed(seed)
    times = pd.date_range('2020-01-01', periods=num_bars, freq=freq)
    prices = start_price + np.cumsum(np.random.randn(num_bars) * 0.2)
    data = []
    for i, t in enumerate(times):
        base = prices[i]
        data.append({
            'time': t,
            'open':  base + np.random.randn() * 0.1,
            'high':  base + abs(np.random.randn()) * 0.3 + 0.1,
            'low':   base - abs(np.random.randn()) * 0.3 - 0.1,
            'close': base + np.random.randn() * 0.1,
            'volume': int(np.random.exponential(1000)),
        })
    return pd.DataFrame(data)


if __name__ == '__main__':
    print("=" * 70)
    print(" Example 21: marker_auto_scale() — Marker Auto-Scaling")
    print("=" * 70)

    chart1 = Chart(title='21 - marker_auto_scale(False)', toolbox=False, maximize=False, marker_auto_scale=False)

    df = generate_bars(200)
    chart1.set(df)

    chart2 = Chart(title='21 - marker_auto_scale(True)', toolbox=False, maximize=False, marker_auto_scale=True)
    chart2.set(df)

    far_above_time = df['time'].iloc[30]
    chart1.marker(
        time=far_above_time,
        position='above',
        shape='arrow_up',
        color='#ffaa00',
        text=f'here',
    )
    chart2.marker(
        time=far_above_time,
        position='above',
        shape='arrow_up',
        color='#ffaa00',
        text=f'here',
    )

    chart1.show(block=False)
    chart2.show(block=True)
