"""
Example 30: Table Component - 表格组件完整演示
===============================================

演示表格组件的各种功能：
1. 创建表格（自选股列表）
2. 创建表格（持仓管理）
3. 动态更新表格内容
4. 行点击回调事件
5. 表格样式定制

运行方式: python table_component.py
"""
import pandas as pd
import numpy as np
from lightweight_charts import Chart


def generate_data(num_bars: int = 200):
    """生成随机 OHLCV 数据"""
    np.random.seed(42)
    date_range = pd.date_range('2025-01-01', periods=num_bars, freq='D')
    price = 100.0
    rows = []
    for i in range(num_bars):
        price += np.random.normal(0, 1.5)
        rows.append({
            'time': date_range[i],
            'open': round(price + np.random.normal(0, 0.5), 2),
            'high': round(price + abs(np.random.normal(0, 0.8)), 2),
            'low': round(price - abs(np.random.normal(0, 0.8)), 2),
            'close': round(price, 2),
            'volume': int(np.random.randint(1000, 50000)),
        })
    return pd.DataFrame(rows)


def on_watchlist_click(row):
    """自选股表格点击回调"""
    symbol = row.get('Symbol') if isinstance(row, dict) else str(row)
    print(f"📈 点击自选股: {symbol}")


def on_position_click(row):
    """持仓表格点击回调"""
    if isinstance(row, dict):
        symbol = row.get('Symbol')
        action = row.get('Action')
        print(f"⚡ 持仓操作: {action} - {symbol}")
    else:
        print(f"⚡ 点击: {row}")


def demo_watchlist_table():
    """演示自选股表格"""
    print("\n--- 示例 1: 自选股表格 ---")

    chart = Chart(width=1000, height=600, title='Watchlist Demo')
    chart.legend(visible=True, persistent=True)

    # 设置主图表数据
    df = generate_data()
    chart.set(df)

    # 创建自选股表格
    watchlist = chart.create_table(
        width=220,  # 固定像素宽度
        height=None,  # None 表示自动适应内容高度
        headings=('Symbol', 'Price', 'Chg%', 'Volume'),
        widths=(0.35, 0.25, 0.2, 0.2),
        alignments=('left', 'right', 'right', 'right'),
        position=(0.02, 0.1),  # 左侧位置（相对坐标）
        draggable=True,   # 可拖拽
        func=on_watchlist_click,
        # 表头样式
        heading_text_colors=('#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFFFF'),
        heading_background_colors=(
            'rgba(70, 130, 180, 0.8)',
            'rgba(70, 130, 180, 0.8)',
            'rgba(70, 130, 180, 0.8)',
            'rgba(70, 130, 180, 0.8)'
        )
    )

    # 添加行数据并保存引用
    row_aapl = watchlist.new_row('AAPL', '198.50', '+1.2%', '12.5M')
    row_googl = watchlist.new_row('GOOGL', '141.80', '-0.8%', '8.2M')
    row_msft = watchlist.new_row('MSFT', '420.30', '+2.1%', '15.8M')
    watchlist.new_row('TSLA', '245.00', '-1.5%', '22.1M')
    watchlist.new_row('NVDA', '875.50', '+3.2%', '18.9M')
    watchlist.new_row('AMD', '156.70', '+0.5%', '9.3M')

    # 设置特定单元格的文本颜色
    row_aapl.text_color('Price', '#00ff00')  # 价格为绿色
    row_googl.text_color('Price', '#ff0000')  # 价格为红色
    row_msft.text_color('Chg%', '#00ff00')  # 涨幅为绿色

    chart.show(wait=120)
    chart.exit()


def demo_position_table():
    """演示持仓管理表格"""
    print("\n--- 示例 2: 持仓管理表格 ---")

    chart = Chart(width=1000, height=600, title='Position Management Demo')
    chart.legend(visible=True, persistent=True)

    # 设置主图表数据
    df = generate_data()
    chart.set(df)

    # 创建持仓表格（使用相对坐标贴在右边，不能拖动）
    positions = chart.create_table(
        width=0.28,  # 相对宽度：占窗口宽度的28%
        height=0.35,  # 相对高度：占窗口高度的35%
        headings=('Symbol', 'Qty', 'Avg Cost', 'Current', 'P&L', 'Action'),
        widths=(0.18, 0.12, 0.18, 0.18, 0.18, 0.16),
        alignments=('left', 'right', 'right', 'right', 'right', 'center'),
        position=(0.7, 0.1),  # 相对位置：右边 70%，顶部 10%
        draggable=False,  # 不能拖动
        func=on_position_click,
        heading_text_colors=('#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFFFF'),
        heading_background_colors=('rgba(100, 149, 237, 0.9)',) * 6
    )

    # 添加持仓数据并保存引用
    pos_aapl = positions.new_row('AAPL', '100', '185.00', '198.50', '+$1,350', '📊')
    pos_msft = positions.new_row('MSFT', '50', '390.00', '420.30', '+$1,515', '📊')
    pos_tsla = positions.new_row('TSLA', '30', '280.00', '245.00', '-$1,050', '🔻')
    pos_nvda = positions.new_row('NVDA', '20', '750.00', '875.50', '+$2,510', '📊')

    # 设置盈亏列颜色
    pos_aapl.text_color('P&L', '#00ff00')  # 盈利
    pos_msft.text_color('P&L', '#00ff00')  # 盈利
    pos_tsla.text_color('P&L', '#ff0000')  # 亏损
    pos_nvda.text_color('P&L', '#00ff00')  # 盈利

    chart.show(wait=120)
    chart.exit()


def demo_dynamic_update():
    """演示表格动态更新"""
    import time

    print("\n--- 示例 3: 表格动态更新 ---")

    chart = Chart(width=1000, height=600, title='Dynamic Table Update Demo')
    chart.legend(visible=True, persistent=True)

    # 设置主图表数据
    df = generate_data()
    chart.set(df)

    # 创建实时数据表格（放在右侧，自动调整大小）
    realtime_table = chart.create_table(
        width=None,  # 自动宽度
        height=None,  # 自动高度
        headings=('Symbol', 'Price', 'Volume', 'Time'),
        widths=(0.25, 0.25, 0.25, 0.25),
        alignments=('left', 'right', 'right', 'right'),
        position=(0.7, 0.1),  # 右侧位置（相对坐标）
        draggable=True,  # 启用拖动
        heading_text_colors=('#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFFFF'),
        heading_background_colors=('rgba(34, 193, 195, 0.9)',) * 4
    )

    # 初始数据并保存引用
    rt_aapl = realtime_table.new_row('AAPL', '198.50', '12.5M', '10:30:00')
    rt_googl = realtime_table.new_row('GOOGL', '141.80', '8.2M', '10:30:00')
    rt_msft = realtime_table.new_row('MSFT', '420.30', '15.8M', '10:30:00')

    chart.show(block=False)
    time.sleep(2)

    # 模拟实时更新
    print("正在模拟实时数据更新...")
    for i in range(5):
        time.sleep(1)
        # 更新价格（模拟小幅波动）
        new_price_aapl = round(198.50 + np.random.normal(0, 0.5), 2)
        new_price_googl = round(141.80 + np.random.normal(0, 0.3), 2)
        new_price_msft = round(420.30 + np.random.normal(0, 0.8), 2)

        # 更新表格行（使用 Row 对象的 __setitem__）
        rt_aapl['Price'] = f'{new_price_aapl:.2f}'
        rt_googl['Price'] = f'{new_price_googl:.2f}'
        rt_msft['Price'] = f'{new_price_msft:.2f}'

        # 更新时间
        from datetime import datetime
        current_time = datetime.now().strftime('%H:%M:%S')
        rt_aapl['Time'] = current_time
        rt_googl['Time'] = current_time
        rt_msft['Time'] = current_time

        print(f"更新 #{i+1}: {current_time}")

    print("动态更新演示完成！")
    chart.show(wait=120)
    chart.exit()


def demo_multi_tables():
    """演示多个表格同时显示"""
    print("\n--- 示例 4: 多表格布局 ---")

    chart = Chart(width=1100, height=700, title='Multi-Table Layout Demo')
    chart.legend(visible=True, persistent=True)

    # 设置主图表数据
    df = generate_data()
    chart.set(df)

    # 左上角：自选股（自动调整大小）
    watchlist = chart.create_table(
        width=None,  # 自动宽度
        height=None,  # 自动高度
        headings=('Symbol', 'Price', 'Chg%'),
        widths=(0.4, 0.3, 0.3),
        position=(0.02, 0.1),  # 左上角位置
        draggable=True,
        heading_text_colors=('#FFFFFF', '#FFFFFF', '#FFFFFF'),
        heading_background_colors=('rgba(70, 130, 180, 0.8)',) * 3
    )
    watchlist.new_row('AAPL', '198.50', '+1.2%')
    watchlist.new_row('GOOGL', '141.80', '-0.8%')
    watchlist.new_row('MSFT', '420.30', '+2.1%')

    # 右上角：持仓（自动调整大小）
    positions = chart.create_table(
        width=None,  # 自动宽度
        height=None,  # 自动高度
        headings=('Symbol', 'Qty', 'P&L'),
        widths=(0.4, 0.3, 0.3),
        alignments=('left', 'right', 'right'),
        position=(0.75, 0.1),  # 右上角位置
        draggable=True,
        heading_text_colors=('#FFFFFF', '#FFFFFF', '#FFFFFF'),
        heading_background_colors=('rgba(100, 149, 237, 0.9)',) * 3
    )
    positions.new_row('AAPL', '100', '+$1,350')
    positions.new_row('MSFT', '50', '+$1,515')
    positions.new_row('TSLA', '30', '-$1,050')

    # 右下角：订单（自动调整大小）
    orders = chart.create_table(
        width=None,  # 自动宽度
        height=None,  # 自动高度
        headings=('Type', 'Symbol', 'Price', 'Status'),
        widths=(0.2, 0.25, 0.25, 0.3),
        alignments=('center', 'left', 'right', 'center'),
        position=(0.75, 0.6),  # 右下角位置
        draggable=True,
        heading_text_colors=('#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFFFF'),
        heading_background_colors=('rgba(255, 165, 0, 0.9)',) * 4
    )
    orders.new_row('BUY', 'NVDA', '850.00', 'Pending')
    orders.new_row('SELL', 'TSLA', '250.00', 'Filled')
    orders.new_row('BUY', 'AMD', '150.00', 'Pending')

    chart.show(wait=120)
    chart.exit()


if __name__ == '__main__':
    print("=" * 70)
    print(" Example 30: Table Component - 表格组件完整演示")
    print("=" * 70)
    print()
    print("表格组件功能：")
    print("  ✅ 自选股列表")
    print("  ✅ 持仓管理")
    print("  ✅ 动态更新")
    print("  ✅ 行点击回调")
    print("  ✅ 样式定制")
    print("  ✅ 多表格布局")
    print()
    print("=" * 70)

    # 依次运行各个演示
    demo_watchlist_table()
    demo_position_table()
    demo_dynamic_update()
    demo_multi_tables()

    print("\n✅ 所有表格组件演示完成！")
