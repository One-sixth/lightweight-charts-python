"""生成模拟 OHLCV 数据的工具函数"""

import pandas as pd
import numpy as np


def generate_ohlcv(n=100, base_price=100, seed=42, start_date='2024-01-01'):
    """生成模拟 OHLCV 数据。

    :param n: 数据条数
    :param base_price: 基准价格
    :param seed: 随机种子
    :param start_date: 起始日期，用于控制多批数据的时间不重叠
    """
    rng = np.random.RandomState(seed)
    dates = pd.date_range(start_date, periods=n, freq='D')
    close = base_price + np.cumsum(rng.randn(n) * 2)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    open_ = close + rng.randn(n) * 0.5
    volume = rng.randint(1000, 10000, n)
    return pd.DataFrame({
        'time': dates,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    })
