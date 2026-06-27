import pandas as pd
import numpy as np
from lightweight_charts import Chart


def generate_data(num_bars: int = 300):
    """
    Generates random OHLCV + open interest data.
    """
    np.random.seed(42)

    date_range = pd.date_range('2025-01-01', periods=num_bars, freq='D')
    price = 5000.0

    rows = []
    for i in range(num_bars):
        change = np.random.normal(0, 20)
        price += change
        high = price + abs(np.random.normal(0, 15))
        low = price - abs(np.random.normal(0, 15))
        open_ = price + np.random.normal(0, 10)
        close = price

        rows.append({
            'time': date_range[i],
            'open': round(max(open_, low + 1), 2),
            'high': round(max(high, open_, close), 2),
            'low': round(min(low, open_, close), 2),
            'close': round(close, 2),
            'volume': int(np.random.randint(500, 50000)),
            # open_interest has a slight upward trend + noise
            'open_interest': int(100000 + i * 200 + np.random.randint(-5000, 15000)),
        })

    return pd.DataFrame(rows)


if __name__ == '__main__':
    chart = Chart(toolbox=True)
    chart.legend(visible=True)

    df = generate_data()
    chart.set(df)

    chart.show(wait=120)
    chart.exit()
