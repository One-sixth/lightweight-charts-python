import asyncio
import pandas as pd
import numpy as np
from threading import Thread
from lightweight_charts import Chart


def generate_data(symbol: str, num_bars: int = 200, seed: int = 42):
    """
    Generates random OHLCV data. Different symbols get different seeds
    so the charts look distinct.
    """
    np.random.seed(seed)
    start_price = {'AAPL': 180, 'TSLA': 250}.get(symbol, 100)

    date_range = pd.date_range('2025-01-01', periods=num_bars, freq='D')
    price = float(start_price)

    rows = []
    for i in range(num_bars):
        change = np.random.normal(0, price * 0.015)
        price += change
        high = price + abs(np.random.normal(0, price * 0.01))
        low = price - abs(np.random.normal(0, price * 0.01))
        open_ = price + np.random.normal(0, price * 0.005)
        close = price

        rows.append({
            'time': date_range[i],
            'open': round(max(open_, low + 0.01), 2),
            'high': round(max(high, open_, close), 2),
            'low': round(min(low, open_, close), 2),
            'close': round(close, 2),
            'volume': int(np.random.randint(5000, 500000)),
        })

    return pd.DataFrame(rows)


def run_chart(chart):
    """Runs a chart's async event loop in a separate thread."""
    asyncio.run(chart.show_async())


if __name__ == '__main__':
    chart1 = Chart(width=600, height=600, title='AAPL')
    chart1.legend(visible=True)

    chart2 = Chart(width=600, height=600, title='TSLA')
    chart2.legend(visible=True)

    df1 = generate_data('AAPL', seed=42)
    df2 = generate_data('TSLA', seed=99)

    chart1.set(df1)
    chart2.set(df2)

    # Each chart runs its own event loop in a daemon thread.
    # Both windows are independent: close either one to exit.
    t1 = Thread(target=run_chart, args=(chart1,), daemon=True)
    t2 = Thread(target=run_chart, args=(chart2,), daemon=True)
    t1.start()
    t2.start()

    try:
        t1.join()
    except KeyboardInterrupt:
        chart1.exit()
        chart2.exit()
