"""
Example 40: ToolBox Multi-Pane Drawing

ToolBox UI 固定在 Pane 0，但鼠标点击哪个 pane 就在哪个 pane 上绘制。
DrawingInfo 回调自动携带 pane_index。

操作步骤：
  1. 点击 ToolBox 上的绘图按钮（如 TrendLine）
  2. 在任意 pane 上点击确定起点
  3. 在同一 pane 上点击确定终点（或移动鼠标预览）
  4. 观察 on_change 回调输出的 pane_index

Usage:
    python examples/40_toolbox_multi_pane/toolbox_multi_pane.py
"""

import pandas as pd
import numpy as np
from lightweight_charts import Chart
from lightweight_charts.toolbox import DrawingInfo


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
    name = name or f'SMA {period}'
    return pd.DataFrame({
        'time': df['time'],
        'value': df['close'].rolling(window=period).mean(),
    })


def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return pd.DataFrame({'time': df['time'], 'value': 100 - (100 / (1 + rs))})


def on_drawings_change(drawings: list[DrawingInfo]):
    """ToolBox 回调：每次 drawing 变更时触发。"""
    for d in drawings:
        t1 = d.start_time or '-'
        t2 = d.end_time or '-'
        p1 = f'{d.start_price:.2f}' if d.start_price is not None else '-'
        p2 = f'{d.end_price:.2f}' if d.end_price is not None else '-'
        print(f'  pane={d.pane_index}  type={d.type:15s}  '
              f'time=[{t1}, {t2}]  price=[{p1}, {p2}]')
    print(f'  ── total: {len(drawings)} drawing(s)')
    print()


def demo():
    chart = Chart(width=1200, height=800, title='ToolBox Multi-Pane Demo', toolbox=True)
    chart.legend(visible=True)

    df = generate_ohlc(120)

    # ── Pane 0: K线 + SMA ──
    chart.set(df)
    sma7 = chart.create_line('SMA 7', color='red', price_line=False, price_label=False)
    sma7.set(calculate_sma(df, 7))
    sma14 = chart.create_line('SMA 14', color='blue', price_line=False, price_label=False)
    sma14.set(calculate_sma(df, 14))

    # ── Pane 1: Histogram ──
    hist = chart.create_histogram('SMA 20', color='#9B59B6', price_line=False, price_label=False, pane_index=1)
    hist.set(calculate_sma(df, 20))

    # ── Pane 2: RSI line ──
    rsi = chart.create_line('RSI', color='#26A69A', price_line=False, price_label=False, pane_index=2)
    rsi.set(calculate_rsi(df))

    # ── 注册 ToolBox 回调 ──
    chart.toolbox.on_change += on_drawings_change

    chart.show(wait=300)
    chart.exit()


if __name__ == '__main__':
    demo()
