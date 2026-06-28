import pandas as pd
import numpy as np
from lightweight_charts import Chart


def generate_data(seed: int = 42):
    """Generates random OHLCV data."""
    np.random.seed(seed)
    date_range = pd.date_range('2025-01-01', periods=200, freq='D')
    price = 100.0
    rows = []
    for i in range(200):
        price += np.random.normal(0, 2)
        high = price + abs(np.random.normal(0, 2))
        low = price - abs(np.random.normal(0, 2))
        rows.append({
            'time': date_range[i],
            'open': round(max(price + np.random.normal(0, 1), low + 0.01), 2),
            'high': round(max(high, price), 2),
            'low': round(min(low, price), 2),
            'close': round(price, 2),
            'volume': int(np.random.randint(1000, 50000)),
        })
    return pd.DataFrame(rows)


if __name__ == '__main__':
    df = generate_data()

    # Left: legend without persistent (default) — OHLC hides when mouse leaves
    chart_default = Chart(width=500, height=600, title='Legend: default')
    chart_default.legend(visible=True, ohlc=True, persistent=False)
    chart_default.set(df)

    # Right: legend with persistent=True — OHLC stays visible
    chart_persist = Chart(width=500, height=600, title='Legend: persistent')
    chart_persist.legend(visible=True, ohlc=True, persistent=True)
    chart_persist.set(df)

    chart_default.show()
    chart_persist.show()

    chart_default.show(wait=120)

    chart_default.exit()
    chart_persist.exit()
