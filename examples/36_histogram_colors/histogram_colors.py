"""
Example 36: Histogram with Custom Colors
Demonstrates Histogram series with arbitrary per-bar colors.
支持正数和负数，每根柱子可独立着色。

Usage:
    python examples/36_histogram_colors/histogram_colors.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
from lightweight_charts import Chart


def generate_delta_data(n=100):
    """生成买卖量差数据（正=买方主导，负=卖方主导）。"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=n, freq='D')

    # 模拟价格
    price = 100.0
    prices = []
    for _ in range(n):
        price += np.random.randn() * 2
        prices.append(round(price, 2))

    # 买卖量差：正值=买方强，负值=卖方强
    buy_vol = np.random.randint(1000, 8000, n)
    sell_vol = np.random.randint(1000, 8000, n)
    delta = buy_vol - sell_vol

    # 五颜六色：根据值的大小映射到渐变色谱
    # 正值→暖色系（黄→橙→红），负值→冷色系（青→蓝→紫）
    def value_to_color(v, vmin, vmax):
        if v >= 0:
            # 正值：0→黄色, max→红色
            ratio = v / vmax if vmax > 0 else 0
            r = 255
            g = int(230 - ratio * 130)  # 230→100
            b = int(50 + ratio * 30)    # 50→80
        else:
            # 负值：0→青色, min→紫色
            ratio = abs(v) / abs(vmin) if vmin < 0 else 0
            r = int(50 + ratio * 130)   # 50→180
            g = int(200 - ratio * 150)  # 200→50
            b = 230
        return f'#{r:02x}{g:02x}{b:02x}'

    vmin, vmax = delta.min(), delta.max()
    colors = [value_to_color(v, vmin, vmax) for v in delta]

    # OHLC（简化）
    close = np.array(prices)
    open_ = close + np.random.randn(n) * 0.5
    high = np.maximum(open_, close) + np.abs(np.random.randn(n)) * 0.5
    low = np.minimum(open_, close) - np.abs(np.random.randn(n)) * 0.5

    candle_df = pd.DataFrame({
        'time': dates, 'open': open_, 'high': high, 'low': low,
        'close': close, 'volume': buy_vol + sell_vol,
    })

    delta_df = pd.DataFrame({
        'time': dates,
        'value': delta,
        'color': colors,
    })

    return candle_df, delta_df


def main():
    candle_df, delta_df = generate_delta_data(100)

    chart = Chart(width=1200, height=700, title='Histogram Custom Colors Demo')
    chart.show(block=False)
    chart.legend(visible=True, ohlc=True, percent=True)

    # 主 K 线（chart.set 不会转发 color 列，所以 histogram 必须单独 set）
    chart.set(candle_df)

    # 创建 Histogram（内置 color 支持，无需额外参数）
    hist = chart.create_histogram(
        name='Volume Delta',
        color='rgba(100,200,100,0.5)',
        pane_index=1,
    )

    # 单独 set：DataFrame 中的 color 列自动携带到 JS 端，每根柱子独立着色
    hist.set(delta_df)

    print("Histogram with custom colors:")
    print(f"  Rows: {len(delta_df)}")
    print(f"  Positive (buy-dominant): {(delta_df['value'] >= 0).sum()}")
    print(f"  Negative (sell-dominant): {(delta_df['value'] < 0).sum()}")

    chart.show(wait=120)
    chart.exit()


if __name__ == '__main__':
    main()
