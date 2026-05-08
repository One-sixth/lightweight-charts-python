"""
Example 23: crosshair_move Event — Hit Testing (v5.2.0+)
==========================================================
Demonstrates the new crosshair_move event that fires on every
mouse move, giving you real-time hover coordinates.

Watch the console while moving the mouse across the chart!

Run: python crosshair_move.py
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


def on_crosshair_move(chart, payload):
    """
    Called on every mouse move across the chart.
    payload: dict with 'time' (Unix timestamp) and 'price' (float)
    """
    if payload.get('time') is not None:
        dt = pd.to_datetime(payload['time'], unit='s')
        price = payload.get('price')
        price_str = f'{price:.2f}' if price is not None else 'N/A'
        print(f"[crosshair] {dt}  |  price = {price_str}")


if __name__ == '__main__':
    print("=" * 60)
    print(" Example 23: crosshair_move Event (Hit Testing)")
    print("=" * 60)

    chart = Chart(title='23 - crosshair_move', toolbox=True, maximize=True)
    chart.layout(background_color='#0e1117', text_color='#d1d4dc')
    chart.legend(visible=True, ohlc=True, persistent=True)

    df = generate_bars(200)
    chart.set(df)
    print(f"[OK] {len(df)} bars loaded")

    # Register the crosshair_move callback
    chart.events.crosshair_move += on_crosshair_move
    print("[OK] crosshair_move callback registered")

    print("\n>>> Move your mouse across the chart …")
    print("    Coordinates will print here in real-time.\n")
    print("    (press Ctrl+C in console to exit)\n")

    chart.show(block=True)
