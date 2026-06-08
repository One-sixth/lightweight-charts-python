"""
示例 33: reset_sub — 子图内容重置

演示 reset_sub() 功能：
- 4 个子图 (2x2 网格)，其中 3 个同步十字光标，1 个不同步
- reset_sub() 清除指定子图的全部内容
- 清除后重新填充数据，验证子图可重用
- 其他子图不受影响
- sub_c 的 TopBar 实时显示当前步骤

布局：
  图表1 (main)  |  sub_a (茅台)
  ─────────────────────────────
  sub_b (宁德时代) |  sub_c (比亚迪) ← 不同步

Usage:
    python examples/33_reset_sub/reset_sub_demo.py
"""

import time
import pandas as pd
import numpy as np
from lightweight_charts import Chart


def generate_stock_data(name, base_price, days=60, seed=42):
    """生成模拟股票数据"""
    np.random.seed(seed)
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    price = base_price
    rows = []
    for i, date in enumerate(dates):
        open_p = price
        high_p = price + abs(np.random.normal(0, 1.5))
        low_p = price - abs(np.random.normal(0, 1.5))
        close_p = price + np.random.normal(0, 1)
        volume = int(np.random.randint(2000, 20000))
        rows.append({
            'time': date,
            'open': round(open_p, 2),
            'high': round(high_p, 2),
            'low': round(low_p, 2),
            'close': round(close_p, 2),
            'volume': volume,
        })
        price = close_p
    return pd.DataFrame(rows)


def add_full_resources(chart, bars, prefix, line_color):
    """给子图添加完整资源集"""
    chart.set(bars)
    chart.legend(visible=True, ohlc=True, lines=True)

    # 技术指标线
    chart.create_line(f'{prefix} MA5', color=line_color, width=2)

    # 标记
    chart.marker(bars['time'].iloc[10], 'above', 'circle', '#ff4444', f'{prefix} 卖出')
    chart.marker(bars['time'].iloc[30], 'below', 'arrow_up', '#44ff44', f'{prefix} 买入')

    # 价格线
    chart.create_price_line(price=bars['close'].mean(), title=f'{prefix} 均价',
                            color='rgba(255,255,0,0.5)', style='large_dashed')

    # 表格
    tbl = chart.create_table(
        width=180, height=80,
        headings=('指标', '值'),
        widths=(90, 90),
        position=(0, 0),
    )
    tbl.new_row('品种', prefix)
    tbl.new_row('最新价', f"{bars['close'].iloc[-1]:.2f}")


def main():
    print("=" * 60)
    print("  示例 33: reset_sub — 子图内容重置")
    print("=" * 60)

    # 创建 2x2 网格布局
    chart = Chart(
        width=1400, height=900,
        title='reset_sub Demo — 2x2 Grid',
        position=(2, 2, 1),
        toolbox=True,
    )

    # 创建 3 个同步子图（使用 sync_id 与主图同步十字光标和时间轴）
    sub_a = chart.create_subchart(position=(2, 2, 2), toolbox=True, sync_id=chart.id)
    sub_b = chart.create_subchart(position=(2, 2, 3), sync_id=chart.id)

    # sub_c 不同步——独立运行，作为"观察者"
    sub_c = chart.create_subchart(position=(2, 2, 4), toolbox=True)

    # sub_c 的 TopBar 显示当前步骤
    sub_c.topbar.textbox('step', '准备开始...', align='left')
    step_label = sub_c.topbar['step']

    try:
        chart.show(block=False)
        chart.clear_handlers()

        # ============================================================
        #  第 1 步：填充所有子图
        # ============================================================
        step_label.set('步骤 1/8: 填充 4 个子图...')
        time.sleep(2)

        bars_main = generate_stock_data('沪深300', 3500, seed=10)
        bars_a = generate_stock_data('茅台', 1800, seed=20)
        bars_b = generate_stock_data('宁德时代', 200, seed=30)
        bars_c = generate_stock_data('比亚迪', 280, seed=40)

        add_full_resources(chart, bars_main, '沪深300', '#ff6b6b')
        add_full_resources(sub_a, bars_a, '茅台', '#ffd93d')
        add_full_resources(sub_b, bars_b, '宁德时代', '#6bcb77')
        add_full_resources(sub_c, bars_c, '比亚迪', '#4d96ff')

        time.sleep(3)
        print("[1] 4 个子图已填充完毕")
        print("    同步组: main + sub_a + sub_b（十字光标联动）")
        print("    独立: sub_c（十字光标独立）")

        # ============================================================
        #  第 2 步：reset_sub 清除 sub_b（同步子图）
        # ============================================================
        step_label.set('步骤 2/8: reset_sub(sub_b) 清除「宁德时代」...')
        time.sleep(2)

        sub_b.reset_sub()
        time.sleep(2)

        assert sub_b.candle_data.empty
        assert len(sub_b._lines) == 0
        assert len(sub_b._price_lines) == 0
        assert len(sub_b.markers) == 0
        assert len(sub_b._tables) == 0
        assert not chart.candle_data.empty
        assert not sub_a.candle_data.empty
        assert not sub_c.candle_data.empty
        print("[2] sub_b 已清除，其他子图不受影响")

        step_label.set('步骤 2/8: ✅ sub_b 已清空')
        time.sleep(3)

        # ============================================================
        #  第 3 步：重新填充 sub_b
        # ============================================================
        step_label.set('步骤 3/8: 重新填充 sub_b →「特斯拉」...')
        time.sleep(2)

        bars_tesla = generate_stock_data('特斯拉', 250, seed=99)
        add_full_resources(sub_b, bars_tesla, '特斯拉', '#e056fd')
        time.sleep(3)

        assert not sub_b.candle_data.empty
        assert len(sub_b._lines) > 0
        print("[3] sub_b 重新填充成功")

        step_label.set('步骤 3/8: ✅ sub_b →「特斯拉」')
        time.sleep(3)

        # ============================================================
        #  第 4 步：reset_sub 清除 sub_a（同步子图）
        # ============================================================
        step_label.set('步骤 4/8: reset_sub(sub_a) 清除「茅台」...')
        time.sleep(2)

        sub_a.reset_sub()
        time.sleep(2)

        assert sub_a.candle_data.empty
        assert len(sub_a._lines) == 0
        print("[4] sub_a 已清除")

        step_label.set('步骤 4/8: ✅ sub_a 已清空')
        time.sleep(3)

        # ============================================================
        #  第 5 步：重新填充 sub_a
        # ============================================================
        step_label.set('步骤 5/8: 重新填充 sub_a →「腾讯」...')
        time.sleep(2)

        bars_tencent = generate_stock_data('腾讯', 380, seed=77)
        add_full_resources(sub_a, bars_tencent, '腾讯', '#f8a5c2')
        time.sleep(3)

        assert not sub_a.candle_data.empty
        assert len(sub_a._lines) > 0
        print("[5] sub_a 重新填充成功")

        step_label.set('步骤 5/8: ✅ sub_a →「腾讯」')
        time.sleep(3)

        # ============================================================
        #  第 6 步：reset_sub 清除主图（同步组核心）
        # ============================================================
        step_label.set('步骤 6/8: reset_sub(chart) 清除「沪深300」...')
        time.sleep(2)

        chart.reset_sub()
        time.sleep(2)

        assert chart.candle_data.empty
        assert len(chart._lines) == 0
        assert len(chart._price_lines) == 0
        assert len(chart.markers) == 0
        assert len(chart._tables) == 0
        print("[6] 主图已清除")
        print("    验证: sub_a/sub_b/sub_c 数据完好")

        step_label.set('步骤 6/8: ✅ 主图已清空，子图完好')
        time.sleep(3)

        # ============================================================
        #  第 7 步：重新填充主图
        # ============================================================
        step_label.set('步骤 7/8: 重新填充主图 →「上证指数」...')
        time.sleep(2)

        bars_sse = generate_stock_data('上证指数', 3200, seed=55)
        add_full_resources(chart, bars_sse, '上证指数', '#ff9f43')
        time.sleep(3)

        assert not chart.candle_data.empty
        assert len(chart._lines) > 0
        print("[7] 主图重新填充成功")

        step_label.set('步骤 7/8: ✅ 主图 →「上证指数」')
        time.sleep(3)

        # ============================================================
        #  第 8 步：最终状态验证
        # ============================================================
        step_label.set('步骤 8/8: 验证最终状态...')
        time.sleep(2)

        print("\n[8] 最终状态:")
        print(f"      上证指数 (main): {len(chart._lines)} lines, {len(chart.markers)} markers, table={len(chart._tables)}")
        print(f"      腾讯 (sub_a):    {len(sub_a._lines)} lines, {len(sub_a.markers)} markers, table={len(sub_a._tables)}")
        print(f"      特斯拉 (sub_b):  {len(sub_b._lines)} lines, {len(sub_b.markers)} markers, table={len(sub_b._tables)}")
        print(f"      比亚迪 (sub_c):  {len(sub_c._lines)} lines, {len(sub_c.markers)} markers, table={len(sub_c._tables)}")

        step_label.set('✅ 全部完成! 4 个子图均正常')
        time.sleep(2)

        print("\n" + "=" * 60)
        print("  ALL TESTS PASSED")
        print("=" * 60)
        print("\n  布局:")
        print("    上证指数 (main) | 腾讯 (sub_a)     ← 同步十字光标")
        print("    ─────────────────────────────────")
        print("    特斯拉 (sub_b)  | 比亚迪 (sub_c)   ← sub_b 同步, sub_c 独立")
        print("\n  请在浏览器中验证:")
        print("    1. 移动 main/sub_a/sub_b 的十字光标 → 三者联动")
        print("    2. 移动 sub_c 的十字光标 → 仅 sub_c 移动")
        print("    3. 三个图表的 reset + 重填均已完成")
        print("\n关闭窗口退出 ...")
        chart.show(True)

    except Exception as e:
        step_label.set(f'❌ 错误: {type(e).__name__}')
        print(f"\n  [ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        time.sleep(5)


if __name__ == '__main__':
    main()
