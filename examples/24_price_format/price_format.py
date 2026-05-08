"""
Example 24: Base Price Format (v5.2.0+)
============================================
演示 'base' 价格格式，通过定义基准值和精度来避免浮点精度问题。
这是 minMove 的替代方案。

使用方法: python price_format.py
"""
import pandas as pd
import numpy as np
from lightweight_charts import Chart


def generate_bars(num_bars=100, start_price=100.0, seed=42):
    np.random.seed(seed)
    times = pd.date_range('2024-01-01', periods=num_bars, freq='1h')
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
        })
    return pd.DataFrame(data)


if __name__ == '__main__':
    print("=" * 70)
    print(" 示例 24: Base 价格格式 — set_price_format(type='base', base, precision)")
    print("=" * 70)

    # 创建图表
    chart = Chart(title='Base 价格格式 (base=100, precision=2)',
                  toolbox=False, maximize=False)

    # 生成并设置数据（价格在 100 左右）
    df = generate_bars(80, start_price=100.0)
    chart.set(df)

    # 应用 base 价格格式：基准值=100，精度=2
    # 这意味着所有价格值将显示为 (实际值 / 基准值) 并保留 2 位小数
    # 例如，实际价格 100.00 将显示为 1.00
    chart.set_price_format(type='base', base=100, precision=2)

    chart.show(block=True)
