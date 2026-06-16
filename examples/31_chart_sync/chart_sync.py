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
    """演示图表同步功能（使用新的 sync_id 组名方式）"""
    print("=== 示例 31: 图表同步功能 ===")
    print("\nsync_id 是同步组名，所有同名图表自动同步：")
    print("  Chart(sync_id='main') -> 主图表加入 'main' 同步组")
    print("  create_subchart(sync_id='main') -> 子图加入 'main' 同步组")
    print("  sync_crosshairs_only=True -> 仅同步十字光标\n")

    # 创建主图表 - 使用 2x2 网格布局，直接加入 'main' 同步组
    chart = Chart(width=1200, height=800, title='Chart Sync Demo',
                  position=(2, 2, 1), sync_id='main')
    chart.legend(visible=True, persistent=True)

    # 生成主图表数据（股票A）
    df_main = generate_data(base_price=100)
    chart.set(df_main)

    # ========== 方式1: 两个子图加入同一组 ==========
    subchart_right = chart.create_subchart(
        position=(2, 2, 2),
        sync_id='main',
        sync_crosshairs_only=False
    )
    df_right = generate_data(base_price=150)
    subchart_right.set(df_right)
    subchart_right.legend(visible=True, persistent=True)

    # ========== 方式2: 仅十字光标同步 ==========
    # 底部子图也加入 'main' 组，但设为仅十字光标同步
    subchart_bottom = chart.create_subchart(
        position=223,
        width=2.0,
        sync_id='main',
        sync_crosshairs_only=True
    )
    df_bottom = generate_data(base_price=80)
    subchart_bottom.set(df_bottom)

    print("主窗口布局:")
    print("┌──────────┬──────────┐")
    print("│ 主图表   │ 右侧同步 │  ← 同步组 'main'（完全同步）")
    print("├──────────┴──────────┤")
    print("│      底部子图        │  ← 同步组 'main'（仅十字光标）")
    print("└─────────────────────┘")

    chart.show(block=True)


if __name__ == '__main__':
    demo_chart_sync()
