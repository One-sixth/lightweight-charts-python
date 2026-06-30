"""
Example 21: marker_auto_scale() — Toggle Marker Auto-Scaling (v5.2.0)
======================================================================
左右对比：左图 marker_auto_scale=False，右图 marker_auto_scale=True。
所有 bar 的 OHLC 固定为 10, 20, 5, 15，20 个标记堆叠在同一个时间戳上。

Run: python marker_auto_scale.py
"""
import pandas as pd
import numpy as np
from lightweight_charts import Chart


def generate_bars(num_bars=100, freq='1h'):
    """生成固定 OHLC 的 K 线数据，全部为 10, 20, 5, 15。"""
    times = pd.date_range('2020-01-01', periods=num_bars, freq=freq)
    return pd.DataFrame({
        'time': times,
        'open': 10,
        'high': 20,
        'low': 5,
        'close': 15,
        'volume': 1000,
    })


if __name__ == '__main__':
    print("=" * 70)
    print(" Example 21: marker_auto_scale() — Left vs Right Comparison")
    print("=" * 70)

    # ── 主图：左侧（marker_auto_scale=False）──
    chart = Chart(
        title='🔵 marker_auto_scale=False  |  🔴 marker_auto_scale=True  |  20 markers 堆叠在同一时间点',
        toolbox=False,
        maximize=False,
        marker_auto_scale=False,
        position=121,  # 1行2列，左侧
    )

    # ── 子图：右侧（marker_auto_scale=True）──
    sub = chart.create_subchart(
        position=122,           # 1行2列，右侧
        marker_auto_scale=True,
        sync_id='main',         # 同步十字光标和时间轴
    )

    # ── TopBar：左右各一个 textbox ──
    chart.topbar.textbox('left_label', '🔵 marker_auto_scale = False', 'left')
    sub.topbar.textbox('right_label', '🔴 marker_auto_scale = True', 'right')

    chart.show()

    # ── 生成固定 OHLC 数据 ──
    df = generate_bars(100)
    chart.set(df)
    sub.set(df)

    # ── 20 个 marker 全部堆在第 50 根 bar 上 ──
    target_time = df.iloc[50]['time']
    positions = ['above', 'below'] * 10  # 10 above + 10 below

    for i in range(20):
        pos = positions[i]
        color = '#26A69A' if pos == 'above' else '#EF5350'

        chart.add_marker(
            time=target_time,
            position=pos,
            shape='arrow_up' if pos == 'above' else 'arrow_down',
            color=color,
            text=f'M{i+1}',
        )
        sub.add_marker(
            time=target_time,
            position=pos,
            shape='arrow_up' if pos == 'above' else 'arrow_down',
            color=color,
            text=f'M{i+1}',
        )

    print("   ✅ 100 bars, 20 markers stacked at same timestamp")
    print("   🔵 Left : marker_auto_scale = False")
    print("   🔴 Right: marker_auto_scale = True")

    chart.show(wait=120)
    chart.exit()