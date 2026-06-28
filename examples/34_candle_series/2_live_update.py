"""示例 34-2：CandleSeries 实时更新 - 每次追加 1 根 bar"""

import sys
sys.path.insert(0, '..')
from time import sleep
import numpy as np
import pandas as pd
from lightweight_charts import Chart
from generate_data import generate_ohlcv

if __name__ == '__main__':
    chart = Chart(width=1400, height=900, title='CandleSeries 实时更新')

    df_main = generate_ohlcv(200, base_price=100, seed=42)
    df_ref = generate_ohlcv(200, base_price=200, seed=123)

    chart.set(df_main)

    ref = chart.create_candle_series(
        name='参考品种',
        pane_index=1,
        up_color='rgba(0, 150, 255, 0.8)',
        down_color='rgba(255, 100, 0, 0.8)',
    )
    ref.set(df_ref)

    chart.show()

    for i in range(200, 400):
        rng = np.random.RandomState(i)
        close_main = df_main['close'].iloc[-1] + rng.randn() * 2
        close_ref = df_ref['close'].iloc[-1] + rng.randn() * 3

        new_main = pd.Series({
            'time': pd.Timestamp('2024-01-01') + pd.Timedelta(days=i),
            'open': close_main + rng.randn() * 0.5,
            'high': close_main + abs(rng.randn()),
            'low': close_main - abs(rng.randn()),
            'close': close_main,
            'volume': rng.randint(1000, 10000),
        })
        new_ref = pd.Series({
            'time': pd.Timestamp('2024-01-01') + pd.Timedelta(days=i),
            'open': close_ref + rng.randn() * 0.5,
            'high': close_ref + abs(rng.randn() * 1.5),
            'low': close_ref - abs(rng.randn() * 1.5),
            'close': close_ref,
        })

        chart.update(new_main)
        ref.update(new_ref)
        sleep(0.05)

    chart.fit()
    chart.show(wait=120)
    chart.exit()
