"""
Example 37: New Series Types — AreaSeries / OHLCBarSeries / BaselineSeries
演示三种新增 Series 类型的用法。

- AreaSeries：面积图（折线+渐变填充），适合展示均线、波动率等
- OHLCBarSeries：美国线（OHLC 横向柱状图），K 线的另一种画法
- BaselineSeries：基准线（以基准值为界上下分色），适合 RSI 偏差、盈亏等

Usage:
    python examples/37_more_series_types/new_series_types.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
from lightweight_charts import Chart


def generate_ohlc(n=120):
    """生成模拟 OHLC 数据。"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=n, freq='D')

    price = 100.0
    rows = []
    for d in dates:
        change = np.random.randn() * 2
        open_ = price
        close = price + change
        high = max(open_, close) + abs(np.random.randn()) * 0.8
        low = min(open_, close) - abs(np.random.randn()) * 0.8
        vol = np.random.randint(5000, 20000)
        rows.append({
            'time': d, 'open': round(open_, 2), 'high': round(high, 2),
            'low': round(low, 2), 'close': round(close, 2), 'volume': vol,
        })
        price = close

    return pd.DataFrame(rows)


def calculate_sma(df, period):
    """计算简单移动平均。"""
    return df['close'].rolling(window=period).mean()


def calculate_rsi_deviation(df, period=14):
    """计算 RSI 偏离零轴的值（用于 BaselineSeries 演示）。"""
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return (rsi - 50)  # 偏离 50 的值


def main():
    # ── 生成数据 ──
    df = generate_ohlc(120)
    sma20 = calculate_sma(df, 20)
    sma60 = calculate_sma(df, 60)
    rsi_dev = calculate_rsi_deviation(df, 14)

    # ── 主图表：K 线 ──
    chart = Chart(width=1200, height=800, title='New Series Types Demo')
    chart.show(block=False)
    chart.legend(visible=True, ohlc=True, percent=True)
    chart.set(df)

    # ════════════════════════════════════════════════════
    # 1. AreaSeries（面积图）— 叠加到主 K 线
    # ════════════════════════════════════════════════════
    area = chart.create_area_series(
        name='SMA 20 (Area)',
        color='#2196F3',
        top_color='rgba(33, 150, 243, 0.35)',
        bottom_color='rgba(33, 150, 243, 0.0)',
        width=2,
        price_line=False,
        price_label=False,
    )
    area.set(pd.DataFrame({
        'time': df['time'],
        'value': sma20,
    }).dropna())

    # ════════════════════════════════════════════════════
    # 2. OHLCBarSeries（美国线）— 独立面板
    # ════════════════════════════════════════════════════
    bar_series = chart.create_ohlc_bar_series(
        name='美国线',
        up_color='#26a69a',
        down_color='#ef5350',
        open_visible=True,
        thin_bars=False,
        pane_index=1,
    )
    bar_series.set(df[['time', 'open', 'high', 'low', 'close']])

    # ════════════════════════════════════════════════════
    # 3. BaselineSeries（基准线）— 独立面板，RSI 偏离零轴
    # ════════════════════════════════════════════════════
    baseline = chart.create_baseline_series(
        name='RSI 偏离 (Baseline)',
        base_value=0,
        top_fill_color1='rgba(38, 166, 154, 0.3)',
        top_fill_color2='rgba(38, 166, 154, 0.0)',
        top_line_color='rgba(38, 166, 154, 1)',
        bottom_fill_color1='rgba(239, 83, 80, 0.0)',
        bottom_fill_color2='rgba(239, 83, 80, 0.3)',
        bottom_line_color='rgba(239, 83, 80, 1)',
        line_width=2,
        price_line=False,
        price_label=False,
        pane_index=2,
    )
    baseline.set(pd.DataFrame({
        'time': df['time'],
        'value': rsi_dev,
    }).dropna())

    # ── 面积图也可以放在独立面板 ──
    area2 = chart.create_area_series(
        name='SMA 60 (独立面板)',
        color='#FF9800',
        top_color='rgba(255, 152, 0, 0.3)',
        bottom_color='rgba(255, 152, 0, 0.0)',
        width=1,
        price_line=False,
        price_label=False,
        pane_index=3,
    )
    area2.set(pd.DataFrame({
        'time': df['time'],
        'value': sma60,
    }).dropna())

    print("New Series Types Demo:")
    print(f"  AreaSeries: SMA 20 渐变面积叠加到主图 + SMA 60 独立面板")
    print(f"  OHLCBarSeries: 美国线独立面板 (pane 1)")
    print(f"  BaselineSeries: RSI 偏离零轴 (pane 2)")
    print(f"  共 4 个面板，5 个系列（含 candle）")

    chart.show(block=True)


if __name__ == '__main__':
    main()
