"""chart_model 示例 3 — drawing（画线）功能展示 + live 动态增删

展示 5 种 drawing 类型 + 动态 add/del 同步到渲染层。

静态部分（build 前添加）：
  - 水平线：阻力位 / 支撑位
  - 垂直线：买入 / 加仓 / 卖出 / 止损
  - 趋势线：上升通道
  - 射线：趋势射线
  - 方框：震荡区间

动态部分（live 线程每 3 秒）：
  - 删除旧的一组 live_* drawing
  - 在新位置重建水平线 + 垂直线
  - 观察图表上 drawing 的实时增删效果
"""
import os
import sys
import threading
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from chart_model import Model, Window, Chart, Series, Adapter, DrawingManager


def generate_kline(n=120, seed=42):
    """生成模拟 K 线数据"""
    np.random.seed(seed)
    dates = pd.date_range('2023-01-01', periods=n, freq='D')
    prices = 100 + np.cumsum(np.random.randn(n) * 2)
    return pd.DataFrame({
        'time': dates.strftime('%Y-%m-%d'),
        'open': prices,
        'high': prices + np.abs(np.random.randn(n) * 2) + 0.5,
        'low': prices - np.abs(np.random.randn(n) * 2) - 0.5,
        'close': prices + np.random.randn(n) * 0.8,
        'volume': np.random.randint(100000, 500000, n),
    })


if __name__ == '__main__':
    # ═══ 数据生成 ═══
    df = generate_kline(120)
    candle_df = df[['time', 'open', 'high', 'low', 'close']]
    sma_short = pd.DataFrame({
        'time': df['time'],
        'value': df['close'].rolling(10, min_periods=1).mean(),
    })
    sma_long = pd.DataFrame({
        'time': df['time'],
        'value': df['close'].rolling(30, min_periods=1).mean(),
    })

    # ═══ 系统声明 ═══
    model = Model(
        windows=[Window(name='main', display_name='Drawing 示例 -- 静态 5 种 + 动态增删')],
        charts=[
            Chart(name='price', display_name='价格', window='main',
                  interval='1day', precision=2, position=111),
        ],
        series=[
            Series(name='candle', display_name='K线', chart='price',
                   pane=0, type='candle',
                   up_color='#EF5350', down_color='#26A69A'),
            Series(name='sma10', display_name='SMA10', chart='price',
                   pane=0, type='line', color='#FF9800', line_width=1),
            Series(name='sma30', display_name='SMA30', chart='price',
                   pane=0, type='line', color='#9C27B0', line_width=1),
        ],
    )

    # ═══ 设置初始数据 ═══
    model['candle'].set(candle_df)
    model['sma10'].set(sma_short)
    model['sma30'].set(sma_long)

    # ═══════════════════════════════════════════════════════
    #  静态 Drawing（build 前添加，首次渲染即出现）
    # ═══════════════════════════════════════════════════════

    # 1. horizontal_line
    model.drawing.add('阻力位1', chart='price', pane=0,
                         type='horizontal_line', price=115,
                         color='#EF5350', width=2, text='阻力')
    model.drawing.add('阻力位2', chart='price', pane=0,
                         type='horizontal_line', price=110,
                         color='#EF5350', width=1, style='dashed', text='次级阻力')
    model.drawing.add('支撑位1', chart='price', pane=0,
                         type='horizontal_line', price=92,
                         color='#66BB6A', width=2, text='支撑')
    model.drawing.add('支撑位2', chart='price', pane=0,
                         type='horizontal_line', price=97,
                         color='#66BB6A', width=1, style='dashed', text='次级支撑')

    # 2. vertical_line
    model.drawing.add('买入', chart='price', pane=0,
                         type='vertical_line', time=df.iloc[20]['time'],
                         color='#42A5F5', width=2, text='买入')
    model.drawing.add('加仓', chart='price', pane=0,
                         type='vertical_line', time=df.iloc[50]['time'],
                         color='#42A5F5', width=1, style='dashed', text='加仓')
    model.drawing.add('卖出', chart='price', pane=0,
                         type='vertical_line', time=df.iloc[80]['time'],
                         color='#FFA726', width=2, text='卖出')
    model.drawing.add('止损', chart='price', pane=0,
                         type='vertical_line', time=df.iloc[100]['time'],
                         color='#EF5350', width=1, style='dashed', text='止损')

    # 3. trend_line
    model.drawing.add('上升通道', chart='price', pane=0,
                         type='trend_line',
                         start_time=df.iloc[5]['time'],
                         start_price=float(df.iloc[5]['close']),
                         end_time=df.iloc[45]['time'],
                         end_price=float(df.iloc[45]['close']),
                         color='#AB47BC', width=2, style='dashed')

    # 4. ray_line
    model.drawing.add('趋势射线', chart='price', pane=0,
                         type='ray_line',
                         start_time=df.iloc[60]['time'],
                         value=float(df.iloc[60]['close']),
                         color='#26A69A', width=2, text='趋势射线')

    # 5. box
    bx1_price = float(df.iloc[70:95]['low'].min()) - 2
    bx2_price = float(df.iloc[70:95]['high'].max()) + 2
    model.drawing.add('震荡区间', chart='price', pane=0,
                         type='box',
                         start_time=df.iloc[70]['time'],
                         start_price=bx1_price,
                         end_time=df.iloc[95]['time'],
                         end_price=bx2_price,
                         color='#78909C', fill_color='rgba(120, 144, 156, 0.15)',
                         width=1, style='dashed')

    print(f'静态 drawing 已添加 {len(model.drawing)} 个')
    for name in model.drawing.names:
        d = model.drawing._sys._drawings[name]
        print(f'  {name:10s} -> type={d.type:16s}')

    # ═══ 构建（启用 live 模式）═══
    layout = model.build(live=True)
    print(f'build(live=True) OK  --  layout.drawings={len(layout.drawings)} 个')

    chart = Adapter.render(layout, width=1200, height=700)
    print('render() OK')

    # ═══ 动态更新线程（K 线 + drawing）═══
    colors = ['#FFEB3B', '#FF4081', '#00BCD4', '#CDDC39', '#FF6F00']

    lt = pd.Timestamp(candle_df.iloc[-1]['time'])
    last_close = candle_df.iloc[-1]['close']

    def live_feed():
        """每 0.25 秒更新 K 线数据"""
        lc = last_close
        for n in range(1, 241):
            if model._stop_event and model._stop_event.is_set():
                break
            time.sleep(0.25)
            t = (lt + pd.Timedelta(days=n)).strftime('%Y-%m-%d')
            nc = lc + np.random.randn() * 2
            lc = nc
            o = nc + np.random.randn() * 1.5   # open 可在 close 上下波动
            h = max(o, nc) + abs(np.random.randn()) * 1.5  # 最高价 >= open 和 close
            l = min(o, nc) - abs(np.random.randn()) * 1.5  # 最低价 <= open 和 close
            c_ = nc
            model['candle'].append(pd.DataFrame([{
                'time': t, 'open': o, 'high': h, 'low': l, 'close': c_,
            }]))

    import random as rnd

    def live_drawing():
        """每 2 秒随机增删一个 drawing：50% 添加 / 50% 删除"""
        counter = 0
        draw_types = ['horizontal_line', 'vertical_line', 'trend_line', 'ray_line', 'box']

        while not (model._stop_event and model._stop_event.is_set()):
            time.sleep(2)
            if not model._render_ready:
                continue

            df_now = model['candle'].data
            if df_now is None or df_now.empty:
                continue

            r = rnd.random()
            if r < 0.5 and len(model.drawing) > 0:
                # ── 随机删除一个已有的 drawing ──
                all_names = list(model.drawing.names)
                if all_names:
                    name = rnd.choice(all_names)
                    del model.drawing[name]
                    print(f'  [live] 删除: {name}   剩余 {len(model.drawing)} 个')

            else:
                # ── 随机添加一个 type 的 drawing ──
                dtype = rnd.choice(draw_types)
                color = rnd.choice(colors)
                name = f'live_{counter}'
                counter += 1

                try:
                    if dtype == 'horizontal_line':
                        price = float(df_now['close'].iloc[-1]) + rnd.uniform(-10, 10)
                        model.drawing.add(name, chart='price', pane=0,
                                            type='horizontal_line', price=round(price, 1),
                                            color=color, width=2,
                                            text=f'R{counter}')

                    elif dtype == 'vertical_line':
                        idx = rnd.randint(0, len(df_now) - 1)
                        t = str(df_now.iloc[idx]['time'])
                        model.drawing.add(name, chart='price', pane=0,
                                            type='vertical_line', time=t,
                                            color=color, width=2,
                                            text=f'R{counter}')

                    elif dtype == 'trend_line':
                        i1 = rnd.randint(0, len(df_now) - 5)
                        i2 = rnd.randint(i1 + 1, len(df_now) - 1)
                        model.drawing.add(name, chart='price', pane=0,
                                            type='trend_line',
                                            start_time=str(df_now.iloc[i1]['time']),
                                            start_price=round(float(df_now.iloc[i1]['close']), 1),
                                            end_time=str(df_now.iloc[i2]['time']),
                                            end_price=round(float(df_now.iloc[i2]['close']), 1),
                                            color=color, width=2, style='dashed')

                    elif dtype == 'ray_line':
                        idx = rnd.randint(0, len(df_now) - 1)
                        p = float(df_now['close'].iloc[idx]) + rnd.uniform(-10, 10)
                        model.drawing.add(name, chart='price', pane=0,
                                            type='ray_line',
                                            start_time=str(df_now.iloc[idx]['time']),
                                            value=round(p, 1),
                                            color=color, width=2,
                                            text=f'R{counter}')

                    elif dtype == 'box':
                        i1 = rnd.randint(0, len(df_now) - 5)
                        i2 = rnd.randint(i1 + 1, len(df_now) - 1)
                        p1 = float(df_now.iloc[i1]['close']) + rnd.uniform(-5, 5)
                        p2 = float(df_now.iloc[i2]['close']) + rnd.uniform(-5, 5)
                        lo, hi = min(p1, p2), max(p1, p2)
                        model.drawing.add(name, chart='price', pane=0,
                                            type='box',
                                            start_time=str(df_now.iloc[i1]['time']),
                                            start_price=round(lo, 1),
                                            end_time=str(df_now.iloc[i2]['time']),
                                            end_price=round(hi, 1),
                                            color=color,
                                            fill_color=f'rgba({rnd.randint(0,255)}, {rnd.randint(0,255)}, {rnd.randint(0,255)}, 0.15)',
                                            width=1, style='dashed')

                    print(f'  [live] 新增: {name:10s} type={dtype:16s}  总计 {len(model.drawing)} 个')
                except Exception as e:
                    print(f'  [live] 添加失败: {e}')

    # 启动线程
    tf = threading.Thread(target=live_feed, daemon=True)
    tf.start()
    td = threading.Thread(target=live_drawing, daemon=True)
    td.start()

    # ═══ 显示 ═══
    print()
    print('=' * 60)
    print('  窗口已打开，60 秒后自动关闭')
    print('  - 静态 5 种 drawing 类型已显示')
    print('  - K 线每 0.25 秒动态更新')
    print('  - drawing 每 2 秒随机增删一个')
    print('    50% 概率添加（5 种类型随机）')
    print('    50% 概率删除已有 drawing')
    print('=' * 60)

    try:
        chart.show(wait=60)
    except KeyboardInterrupt:
        pass
    finally:
        model.stop_sync()
    print('done')