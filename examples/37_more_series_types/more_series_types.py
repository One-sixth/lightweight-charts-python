"""
Example 37: More Series Types — AreaSeries / OHLCBarSeries / BaselineSeries
演示三种新增 Series 类型 + legend=False 隐藏系列的用法。

- AreaSeries：面积图（折线+渐变填充），适合展示均线、波动率等
- OHLCBarSeries：美国线（OHLC 横向柱状图），K 线的另一种画法
- BaselineSeries：基准线（以基准值为界上下分色），适合 RSI 偏差、盈亏等
- legend=False：创建不显示在图例中的隐藏系列（背景带、辅助线等）

Usage:
    python examples/37_more_series_types/more_series_types.py
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

    # ════════════════════════════════════════════════════
    # 5. legend=False 隐藏系列 — 不显示在图例中
    # ════════════════════════════════════════════════════

    # 隐藏的 SMA 10 辅助线（灰色半透明，作为背景参考）
    sma10 = calculate_sma(df, 10)
    hidden_line = chart.create_line(
        name='SMA 10 (隐藏)',
        color='rgba(150, 150, 150, 0.3)',
        width=1,
        price_line=False,
        price_label=False,
        legend=False,       # ← 不显示在图例中
    )
    hidden_line.set(pd.DataFrame({
        'time': df['time'],
        'value': sma10,
    }).dropna())

    # 隐藏的面积图（SMA 60 的淡色背景带，增强视觉层次）
    hidden_area = chart.create_area_series(
        name='SMA 60 背景 (隐藏)',
        color='rgba(255, 152, 0, 0.1)',
        top_color='rgba(255, 152, 0, 0.15)',
        bottom_color='rgba(255, 152, 0, 0.0)',
        width=1,
        price_line=False,
        price_label=False,
        legend=False,       # ← 不显示在图例中
        pane_index=0,
    )
    hidden_area.set(pd.DataFrame({
        'time': df['time'],
        'value': sma60,
    }).dropna())

    # ════════════════════════════════════════════════════
    # 6. 更多 legend=False — 分布在 pane 1-3
    # ════════════════════════════════════════════════════

    # ── Pane 1: 美国线面板上的隐藏 SMA 5（快速均线参考）──
    sma5 = calculate_sma(df, 5)
    pane1_line = chart.create_line(
        name='SMA 5 (pane1 隐藏)',
        color='rgba(100, 200, 255, 0.3)',
        width=1,
        price_line=False,
        price_label=False,
        pane_index=1,
        legend=False,
    )
    pane1_line.set(pd.DataFrame({
        'time': df['time'],
        'value': sma5,
    }).dropna())

    # ── Pane 1: 美国线面板上的隐藏 Bollinger 带（上下轨面积）──
    sma20_line = df['close'].rolling(window=20).mean()
    std20 = df['close'].rolling(window=20).std()
    bb_upper = sma20_line + 2 * std20
    bb_lower = sma20_line - 2 * std20

    pane1_bb_upper = chart.create_area_series(
        name='BB 上轨 (pane1 隐藏)',
        color='rgba(150, 150, 255, 0.15)',
        top_color='rgba(150, 150, 255, 0.08)',
        bottom_color='rgba(150, 150, 255, 0.0)',
        width=1,
        price_line=False,
        price_label=False,
        pane_index=1,
        legend=False,
    )
    pane1_bb_upper.set(pd.DataFrame({
        'time': df['time'],
        'value': bb_upper,
    }).dropna())

    # ── Pane 2: RSI 面板上的副 K 线（参考品种）──
    np.random.seed(99)
    ref_price = 50.0
    ref_rows = []
    for d in df['time']:
        ref_change = np.random.randn() * 1.5
        ref_open = ref_price
        ref_close = ref_price + ref_change
        ref_high = max(ref_open, ref_close) + abs(np.random.randn()) * 0.5
        ref_low = min(ref_open, ref_close) - abs(np.random.randn()) * 0.5
        ref_rows.append({
            'time': d, 'open': round(ref_open, 2), 'high': round(ref_high, 2),
            'low': round(ref_low, 2), 'close': round(ref_close, 2),
        })
        ref_price = ref_close
    ref_df = pd.DataFrame(ref_rows)

    candle2 = chart.create_candle_series(
        name='参考品种 (pane2)',
        pane_index=2,
        up_color='rgba(100, 180, 255, 0.7)',
        down_color='rgba(255, 130, 100, 0.7)',
        price_line=False,
        price_label=False,
    )
    candle2.set(ref_df)

    # ── Pane 2: RSI 面板上的隐藏 SMA 30（RSI 平滑参考线）──
    rsi_sma = rsi_dev.rolling(window=30).mean()
    pane2_line = chart.create_line(
        name='RSI SMA30 (pane2 隐藏)',
        color='rgba(200, 200, 200, 0.25)',
        width=1,
        style='dashed',
        price_line=False,
        price_label=False,
        pane_index=2,
        legend=False,
    )
    pane2_line.set(pd.DataFrame({
        'time': df['time'],
        'value': rsi_sma,
    }).dropna())

    # ── Pane 3: 面积图面板上的隐藏 SMA 120（长期均线参考）──
    sma120 = calculate_sma(df, 120)
    pane3_line = chart.create_line(
        name='SMA 120 (pane3 隐藏)',
        color='rgba(255, 255, 255, 0.15)',
        width=1,
        price_line=False,
        price_label=False,
        pane_index=3,
        legend=False,
    )
    pane3_line.set(pd.DataFrame({
        'time': df['time'],
        'value': sma120,
    }).dropna())

    # ── Pane 3: 面积图面板上的隐藏面积带（波动率背景）──
    volatility = df['close'].rolling(window=10).std()
    pane3_vol = chart.create_area_series(
        name='波动率 (pane3 隐藏)',
        color='rgba(255, 100, 100, 0.1)',
        top_color='rgba(255, 100, 100, 0.12)',
        bottom_color='rgba(255, 100, 100, 0.0)',
        width=1,
        price_line=False,
        price_label=False,
        pane_index=3,
        legend=False,
    )
    pane3_vol.set(pd.DataFrame({
        'time': df['time'],
        'value': volatility,
    }).dropna())

    print("More Series Types Demo:")
    print(f"  Pane 0: K 线 + SMA 20 面积 + SMA 10 隐藏 + SMA 60 背景隐藏")
    print(f"  Pane 1: 美国线 + SMA 5 隐藏 + BB 上轨隐藏")
    print(f"  Pane 2: RSI Baseline + 参考品种副K线 + RSI SMA30 隐藏")
    print(f"  Pane 3: SMA 60 面积 + SMA 120 隐藏 + 波动率隐藏")
    print(f"  共 4 个面板，14 个系列（7 个隐藏 legend=False）")

    chart.show(block=True)


if __name__ == '__main__':
    main()
