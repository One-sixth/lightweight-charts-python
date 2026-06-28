"""
Example 25: Enhanced Screenshot (v5.2.0+)
============================================
演示新的截图参数：add_top_layer 和 include_crosshair。
- add_top_layer=True：截图包含顶层水印元素
- include_crosshair=True：截图包含十字光标

使用方法: python screenshot_enhanced.py
"""
import pandas as pd
import numpy as np
import time
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
    print(" 示例 25: 增强截图 — add_top_layer 和 include_crosshair")
    print("=" * 70)

    chart = Chart(title='增强截图演示', toolbox=False, maximize=False)
    df = generate_bars(80)
    chart.set(df)

    # 添加水印以演示 add_top_layer 效果
    chart.watermark('增强截图', color='rgba(180,180,240,0.7)', font_size=36)

    # 在非阻塞模式下显示图表，以便截图
    chart.show(block=False)
    time.sleep(2)  # 等待窗口渲染

    # 使用两项增强选项进行截图
    img = chart.screenshot(add_top_layer=True, include_crosshair=True)
    with open('screenshot_enhanced.png', 'wb') as f:
        f.write(img)
    print("截图已保存为 'screenshot_enhanced.png'")

    # 再截一张不带十字光标的截图以作对比
    img_no_cross = chart.screenshot(add_top_layer=True, include_crosshair=False)
    with open('screenshot_enhanced_no_cross.png', 'wb') as f:
        f.write(img_no_cross)
    print("不带十字光标的截图已保存为 'screenshot_enhanced_no_cross.png'")

    chart.show(wait=120)
    chart.exit()
