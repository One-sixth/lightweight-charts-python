"""
Grid Layout Demo - 展示新的 position 参数功能

支持三种格式：
1. 整数格式：111 (1行1列第1个), 221 (2行2列第1个)
2. 元组格式：(2, 2, 1) (2行2列第1个)
3. 字符串格式（已弃用）：'left', 'right', 'top', 'bottom'

width/height 参数：
- 1.0: 占满网格单元
- < 1.0: 向内缩，对齐左上角
- > 1.0: 侵占其他网格空间
"""
import asyncio
import pandas as pd
import numpy as np
from threading import Thread
from lightweight_charts import Chart


def generate_data(symbol: str, num_bars: int = 200, seed: int = 42):
    """生成随机 OHLCV 数据"""
    np.random.seed(seed)
    start_price = {'AAPL': 180, 'TSLA': 250, 'GOOGL': 140, 'MSFT': 380}.get(symbol, 100)

    date_range = pd.date_range('2025-01-01', periods=num_bars, freq='D')
    price = float(start_price)

    rows = []
    for i in range(num_bars):
        change = np.random.normal(0, price * 0.015)
        price += change
        high = price + abs(np.random.normal(0, price * 0.01))
        low = price - abs(np.random.normal(0, price * 0.01))
        open_ = price + np.random.normal(0, price * 0.005)
        close = price

        rows.append({
            'time': date_range[i],
            'open': round(max(open_, low + 0.01), 2),
            'high': round(max(high, open_, close), 2),
            'low': round(min(low, open_, close), 2),
            'close': round(close, 2),
            'volume': int(np.random.randint(5000, 500000)),
        })

    return pd.DataFrame(rows)


def demo_single_chart():
    """
    示例 1: 单个图表占满窗口
    position=111 表示 1行1列第1个位置
    """
    print("示例 1: 单个图表占满窗口 (position=111)")
    chart = Chart(width=800, height=600, title='Single Chart (111)')
    chart.legend(visible=True)

    df = generate_data('AAPL', seed=42)
    chart.set(df)

    # 获取当前位置
    x, y, w, h = chart.get_position()
    print(f"  位置: x={x:.2f}, y={y:.2f}, width={w:.2f}, height={h:.2f}")

    chart.show(block=True)


def demo_two_charts_horizontal():
    """
    示例 2: 两个图表左右排列
    使用整数格式：121 (左) 和 122 (右)
    """
    print("示例 2: 两个图表左右排列 (position=121, 122)")
    
    chart1 = Chart(width=800, height=600, position=121, title='Left (121)')
    chart1.legend(visible=True)
    
    # 创建第二个图表在同一窗口
    chart2 = chart1.create_subchart(position=122)
    chart2.legend(visible=True)

    df1 = generate_data('AAPL', seed=42)
    df2 = generate_data('TSLA', seed=99)

    chart1.set(df1)
    chart2.set(df2)

    # 获取位置
    x1, y1, w1, h1 = chart1.get_position()
    x2, y2, w2, h2 = chart2.get_position()
    print(f"  Chart1 位置: x={x1:.2f}, y={y1:.2f}, width={w1:.2f}, height={h1:.2f}")
    print(f"  Chart2 位置: x={x2:.2f}, y={y2:.2f}, width={w2:.2f}, height={h2:.2f}")

    chart1.show(block=True)


def demo_two_charts_vertical():
    """
    示例 3: 两个图表上下排列
    使用元组格式：(2, 1, 1) (上) 和 (2, 1, 2) (下)
    """
    print("示例 3: 两个图表上下排列 (position=(2,1,1), (2,1,2))")
    
    chart1 = Chart(width=800, height=800, position=(2, 1, 1), title='Top (2,1,1)')
    chart1.legend(visible=True)
    
    chart2 = chart1.create_subchart(position=(2, 1, 2))
    chart2.legend(visible=True)

    df1 = generate_data('GOOGL', seed=42)
    df2 = generate_data('MSFT', seed=99)

    chart1.set(df1)
    chart2.set(df2)

    chart1.show(block=True)


def demo_four_charts():
    """
    示例 4: 四个图表 2x2 网格
    使用整数格式：221, 222, 223, 224
    """
    print("示例 4: 四个图表 2x2 网格 (position=221, 222, 223, 224)")
    
    chart1 = Chart(width=1000, height=800, position=221, title='Top-Left (221)')
    chart1.legend(visible=True)
    
    chart2 = chart1.create_subchart(position=222)
    chart2.legend(visible=True)
    
    chart3 = chart1.create_subchart(position=223)
    chart3.legend(visible=True)
    
    chart4 = chart1.create_subchart(position=224)
    chart4.legend(visible=True)

    df1 = generate_data('AAPL', seed=42)
    df2 = generate_data('TSLA', seed=99)
    df3 = generate_data('GOOGL', seed=123)
    df4 = generate_data('MSFT', seed=456)

    chart1.set(df1)
    chart2.set(df2)
    chart3.set(df3)
    chart4.set(df4)

    chart1.show(block=True)


def demo_custom_size():
    """
    示例 5: 自定义图表大小
    width/height < 1.0 时向内缩，对齐左上角
    """
    print("示例 5: 自定义图表大小 (width=0.6, height=0.6)")
    
    chart = Chart(width=800, height=600, title='Custom Size (0.6 x 0.6)')
    chart.legend(visible=True)
    
    df = generate_data('AAPL', seed=42)
    chart.set(df)
    
    # 获取位置
    x, y, w, h = chart.get_position()
    print(f"  位置: x={x:.2f}, y={y:.2f}, width={w:.2f}, height={h:.2f}")
    
    chart.show(block=True)


def demo_dynamic_position():
    """
    示例 6: 动态设置位置
    使用 set_position() 方法动态调整图表位置
    """
    print("示例 6: 动态设置位置")
    
    chart = Chart(width=800, height=600, title='Dynamic Position')
    chart.legend(visible=True)
    
    df = generate_data('AAPL', seed=42)
    chart.set(df)
    
    # 获取初始位置
    x, y, w, h = chart.get_position()
    print(f"  初始位置: x={x:.2f}, y={y:.2f}, width={w:.2f}, height={h:.2f}")
    
    # 动态设置新位置（左半部分）
    chart.set_position(0.0, 0.0, 0.5, 1.0)
    
    # 获取新位置
    x, y, w, h = chart.get_position()
    print(f"  新位置: x={x:.2f}, y={y:.2f}, width={w:.2f}, height={h:.2f}")
    
    chart.show(block=True)


if __name__ == '__main__':
    print("=" * 60)
    print("Grid Layout Demo - 新 position 参数功能演示")
    print("=" * 60)
    print()
    print("支持的 position 格式:")
    print("  1. 整数格式：111, 221, 311 等")
    print("  2. 元组格式：(2, 2, 1) 等")
    print("  3. 字符串格式（已弃用）：'left', 'right', 'top', 'bottom'")
    print()
    print("width/height 参数:")
    print("  - 1.0: 占满网格单元")
    print("  - < 1.0: 向内缩，对齐左上角")
    print("  - > 1.0: 侵占其他网格空间")
    print()
    print("=" * 60)
    print()
    
    # 运行示例
    demo_single_chart()
    print()
    demo_two_charts_horizontal()
    print()
    demo_two_charts_vertical()
    print()
    demo_four_charts()
    print()
    demo_custom_size()
    print()
    demo_dynamic_position()
