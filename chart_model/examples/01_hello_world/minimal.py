"""chart_model 最小示例 — 1 Chart × 2 pane（candle + volume），同步线程动态更新

验证同步线程从数据层到渲染层的完整通路。
"""
import os
import sys
import threading
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from chart_model import Model, Window, Chart, Series, Adapter


def generate_kline(n=100, seed=42):
    np.random.seed(seed)
    dates = pd.date_range('2023-01-01', periods=n, freq='D')
    prices = 100 + np.random.randn(n) * 2
    df = pd.DataFrame({
        'time': dates.strftime('%Y-%m-%d'),
        'open': prices,
        'high': prices + 5 + np.abs(np.random.randn(n) * 2),
        'low':  prices - 5 - np.abs(np.random.randn(n) * 2),
        'close': prices + np.random.randn(n) * 2,
        'volume': np.random.randint(100000, 500000, n),
    })
    return df


if __name__ == '__main__':
    # ═══ 数据生成 ═══
    df = generate_kline(100)
    candle_df = df[['time', 'open', 'high', 'low', 'close']]
    vol_df = pd.DataFrame({
        'time': df['time'],
        'value': df['volume'],
        'open': df['open'],
        'close': df['close'],
    })

    # ═══ 系统声明：一个 Chart 两个 pane ═══
    model = Model(
        windows=[Window(name='main', display_name='主窗口')],
        charts=[
            Chart(name='price', display_name='价格', window='main',
                  interval='1day', precision=2, position=111),
        ],
        series=[
            # pane 0: K线（主系列）
            Series(name='candle', display_name='K线', chart='price',
                   pane=0, type='candle'),
            # pane 1: 成交量
            Series(name='volume', display_name='Volume', chart='price',
                   pane=1, type='volume'),
        ],
    )

    # ═══ 设置初始数据 ═══
    model['candle'].set(candle_df)
    model['volume'].set(vol_df)

    # ═══ 构建 + 渲染 ═══
    layout = model.build(live=True)
    print(f'build(live=True) OK  sync_thread={model._sync_thread}')

    chart = Adapter.render(layout, width=1000, height=600)
    print(f'render OK')

    # ═══ 动态更新线程（只更新数据层，不碰渲染层）═══
    lt = pd.Timestamp(candle_df.iloc[-1]['time'])
    last_close = candle_df.iloc[-1]['close']
    last_vol = int(df.iloc[-1]['volume'])

    def live_feed():
        lc = last_close
        lv = last_vol
        for n in range(1, 241):
            time.sleep(0.25)
            t = (lt + pd.Timedelta(days=n)).strftime('%Y-%m-%d')
            nc = lc + np.random.randn() * 2
            lc = nc
            vol_val = int(max(50000, lv + np.random.randn() * 50000))
            lv = vol_val

            o, h, l, c_ = nc - np.random.randn(), nc + np.random.randn() + 2, \
                           nc - np.random.randn() - 2, nc

            # 只更新数据层，同步线程自动检测变化并推送渲染层
            model['candle'].append(pd.DataFrame({
                'time': [t], 'open': [o], 'high': [h], 'low': [l], 'close': [c_],
            }))
            model['volume'].append(pd.DataFrame({
                'time': [t], 'value': [vol_val], 'open': [o], 'close': [c_],
            }))

            print(f'  [{n:3d}/240] t={t} close={nc:.2f}')

        print('live_feed: 数据更新完成')

    feed_thread = threading.Thread(target=live_feed)
    feed_thread.start()

    print('show(block=True) — 同步线程自动推送，约 60 秒...')
    chart.show(block=True)  # 阻塞直到窗口关闭，同步线程在此期间持续工作

    model.stop_sync()
    feed_thread.join()
    print(f'done — 最终版本: candle={model._series_versions.get("candle")}')
