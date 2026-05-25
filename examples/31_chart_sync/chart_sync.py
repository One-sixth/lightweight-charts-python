import pandas as pd
import numpy as np
from lightweight_charts import Chart


def generate_data(base_price=100, days=100):
    """生成模拟数据"""
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    data = []
    price = base_price
    for date in dates:
        open_price = price
        high_price = price + np.random.uniform(0, 2)
        low_price = price - np.random.uniform(0, 2)
        close_price = price + np.random.uniform(-1, 1)
        volume = int(np.random.uniform(1000, 5000))

        data.append({
            'time': date,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
        price = close_price

    return pd.DataFrame(data)


def demo_chart_sync():
    """演示图表同步功能（使用新的 position 设置方式）"""
    print("=== 示例 31: 图表同步功能 ===")
    print("\nposition 参数支持多种设置方式：")
    print("1. 网格元组格式: (nrows, ncols, index) - 类似 matplotlib 的 subplot")
    print("2. 字符串格式: 'left', 'right', 'top', 'bottom'")
    print("3. 数字格式: 111 (百位=行数, 十位=列数, 个位=索引)\n")

    # 创建主图表 - 使用 2x2 网格布局
    chart = Chart(width=1200, height=800, title='Chart Sync Demo', position=(2, 2, 1))
    chart.legend(visible=True, persistent=True)

    # 生成主图表数据（股票A）
    df_main = generate_data(base_price=100)
    chart.set(df_main)

    # ========== 方式1: 使用网格元组格式 (nrows, ncols, index) ==========
    # 创建右侧子图表（2行2列布局，第2个位置）
    subchart_right = chart.create_subchart(
        position=(2, 2, 2),  # 2行2列，第2个位置（右上角）
        sync=chart.id,
        sync_crosshairs_only=False  # 完全同步
    )
    df_right = generate_data(base_price=150)
    subchart_right.set(df_right)
    subchart_right.legend(visible=True, persistent=True)

    # ========== 方式2: 使用数字网格格式 + 跨栏宽度 ==========
    # 创建底部子图表（223 = 2行2列，第3个位置），width=2.0 使其横跨两列
    subchart_bottom = chart.create_subchart(
        position=223,  # 等同于 (2, 2, 3)
        width=2.0,     # 跨两列显示
        sync=chart.id,
        sync_crosshairs_only=True  # 仅同步十字光标
    )
    df_bottom = generate_data(base_price=80)
    subchart_bottom.set(df_bottom)

    print("主窗口布局:")
    print("┌──────────┬──────────┐")
    print("│ 主图表   │ 右侧同步 │  ← 完全同步")
    print("├──────────┴──────────┤")
    print("│      底部子图        │  ← 仅十字光标同步（跨两列）")
    print("└─────────────────────┘")

    chart.show(block=True)


if __name__ == '__main__':
    demo_chart_sync()
