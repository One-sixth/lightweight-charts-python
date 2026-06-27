"""
Example 38: Drawing Series — Multi Pane Drawing 测试

测试 DrawingSeries 在多 pane 场景下的完整功能：
- Pane 0（主图）: K线 + SMA + 水平线 + 趋势线 + Box
- Pane 1（子图1）: 柱状图(Histogram) + RSI 线 + 射线 + 水平线
- Pane 2（子图2）: SMA50 线 + 垂直线
- ToolBox 启用（点击按钮绘制 → 测试 attachPrimitive 到 invisible series）

Usage:
    python examples/38_drawing_multi_pane/drawing_multi_pane.py
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


def calculate_sma(df, period, name=None):
    """计算 SMA。"""
    name = name or f'SMA {period}'
    return pd.DataFrame({
        'time': df['time'],
        'value': df['close'].rolling(window=period).mean(),
    })


def calculate_rsi(df, period=14):
    """计算 RSI。"""
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return pd.DataFrame({'time': df['time'], 'value': rsi})


def demo():
    chart = Chart(width=1200, height=800, title='Drawing Series Multi-Pane Test', toolbox=True, debug=False)
    chart.legend(visible=True)

    df = generate_ohlc(120)

    # ═══════════════════════════════════════════════════
    # Pane 0（主图）: K线 + SMA7/SMA14 + Drawings
    # ═══════════════════════════════════════════════════
    chart.set(df)

    # 两条 SMA 线
    sma7 = chart.create_line('SMA 7', color='red', price_line=False, price_label=False)
    sma7.set(calculate_sma(df, 7))
    sma14 = chart.create_line('SMA 14', color='blue', price_line=False, price_label=False)
    sma14.set(calculate_sma(df, 14))

    # Pane 0 上的 Drawings（通过 pane_index=0 或默认）
    mid_price = round(df['close'].mean(), 2)
    chart.horizontal_line(
        price=mid_price,
        color='orange',
        width=2,
        style='solid',
        text=f'均价 {mid_price}',
    )

    chart.trend_line(
        start_time=df['time'].iloc[20],
        start_value=df['close'].iloc[20],
        end_time=df['time'].iloc[60],
        end_value=df['close'].iloc[60],
        line_color='#1E80F0',
        width=2,
    )

    chart.box(
        start_time=df['time'].iloc[80],
        start_value=df['high'].iloc[80:100].max(),
        end_time=df['time'].iloc[100],
        end_value=df['low'].iloc[80:100].min(),
        color='#E91E63',
        fill_color='rgba(233, 30, 99, 0.15)',
        width=2,
    )

    # ═══════════════════════════════════════════════════
    # Pane 1（子图）: RSI 柱状图 + RSI 线 + Drawings
    # ═══════════════════════════════════════════════════
    rsi_data = calculate_rsi(df, 14)

    # 柱状图：RSI 偏离 50 的幅度
    rsi_dev = pd.DataFrame({
        'time': df['time'],
        'value': (rsi_data['value'] - 50).fillna(0),
    })
    hist = chart.create_histogram('RSI Dev', price_line=False, price_label=False, pane_index=1)
    hist.set(rsi_dev)

    # RSI 线
    rsi_line = chart.create_line('RSI', color='purple', price_line=False, price_label=False, pane_index=1)
    rsi_line.set(rsi_data)

    # Pane 1 上的 Drawings
    chart.ray_line(
        start_time=df['time'].iloc[0],
        value=50,
        color='gray',
        width=1,
        style='dashed',
        text='RSI 50',
        pane_index=1,
    )

    chart.horizontal_line(
        price=70,
        color='red',
        width=1,
        style='dashed',
        text='超买 70',
        pane_index=1,
    )

    chart.horizontal_line(
        price=30,
        color='green',
        width=1,
        style='dashed',
        text='超卖 30',
        pane_index=1,
    )

    # ═══════════════════════════════════════════════════
    # Pane 2（子图）: SMA50 + 垂直线
    # ═══════════════════════════════════════════════════
    sma50 = chart.create_line('SMA 50', color='green', price_line=False, price_label=False, pane_index=2)
    sma50.set(calculate_sma(df, 50))

    # Pane 2 上的 Drawings（注意：vertical_line 不需要 pane_index，它作用于全图）
    chart.vertical_line(
        time=df['time'].iloc[40],
        color='#FF5722',
        width=2,
        style='dashed',
        text='关键时间点',
        pane_index=2,
    )

    chart.vertical_line(
        time=df['time'].iloc[80],
        color='#9C27B0',
        width=2,
        style='dashed',
        text='第二个时间点',
        pane_index=2,
    )

    # ToolBox 回调：打印 drawing 变更信息
    def on_drawings_change(drawings):
        print(f'\n[ToolBox] Drawings changed! Total: {len(drawings)}')
        for i, d in enumerate(drawings):
            prices = [f"{p.get('price', 0):.2f}" for p in d.points if p]
            print(f'  [{i}] {d.type}  id={d.id}  prices=[{", ".join(prices)}]')
        print()

    chart.toolbox.on_change += on_drawings_change

    chart.show(wait=120)
    chart.exit()


if __name__ == '__main__':
    demo()
