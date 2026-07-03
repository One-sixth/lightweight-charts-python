"""ind_sys 示例 — 声明式描述 + live 动态同步

结构：
  Window
  ├── Chart "price" (interval='1day', position=211)
  │   ├── pane 0: K线 + SMA50
  │   └── pane 1: Volume
  └── Chart "indicator" (interval='1day', position=212, sync_id='main')
      └── pane 0: SMA120

live 模式：build(live=True) 启动同步线程，
后续 sys_obj['name'].append() 自动同步到渲染层。
"""
import os
import threading
import time
import pandas as pd

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ind_sys import System, Window, Chart, Series, Adapter


def calculate_sma(df, period: int):
    return pd.DataFrame({
        'time': df['time'],
        'value': df['close'].rolling(window=period).mean()
    }).dropna()


if __name__ == '__main__':
    csv_path = os.path.join(os.path.dirname(__file__), '..', '4_line_indicators', 'ohlcv.csv')
    df = pd.read_csv(csv_path).rename(columns={'date': 'time'})

    sma50 = calculate_sma(df, 50)
    sma120 = calculate_sma(df, 120)
    candle_df = df[['time', 'open', 'high', 'low', 'close']]
    vol_df = df[['time', 'open', 'close']].copy()
    vol_df['value'] = df['volume']

    # ── 声明结构 ──
    sys_obj = System(
        windows=[Window(name='main', display_name='ind_sys Live Demo')],
        charts=[
            Chart(name='price', display_name='Price', window='main',
                  interval='1day', precision=2, position=211, sync_id='main'),
            Chart(name='indicator', display_name='SMA120', window='main',
                  interval='1day', precision=2, position=212, sync_id=None),
        ],
        series=[
            Series(name='candle', display_name='K线', chart='price', pane=0, type='candle'),
            Series(name='sma50', display_name='SMA 50', chart='price',
                   pane=0, type='line', color='#FF6F00', group='MA'),
            Series(name='vol', display_name='Volume', chart='price', pane=1, type='volume'),
            Series(name='sma120', display_name='SMA 120', chart='indicator',
                   pane=0, type='line', color='#00C853'),
        ],
    )

    # ── 设置数据 ──
    sys_obj['candle'].set(candle_df)
    sys_obj['sma50'].set(sma50)
    sys_obj['vol'].set(vol_df)
    sys_obj['sma120'].set(sma120)

    # ── 标记 ──
    sys_obj['candle'].add_marker(time=sma50.iloc[0]['time'], position='below',
                                 shape='arrow_up', color='#00C853', text='金叉')

    # ── build(live=True)：启动同步线程 ──
    layout = sys_obj.build(live=True)
    print(f'build(live=True) OK  sync_thread={sys_obj._sync_thread}')

    # ── 渲染 ──
    chart = Adapter.render(layout, width=1000, height=800)
    print(f'render OK  _render_chart set: {sys_obj._render_chart is not None}')

    # ── 后台动态追加：每 2 秒追加一根新 K 线 ──
    def live_feed():
        last_close = candle_df.iloc[-1]['close']
        last_time = pd.Timestamp(candle_df.iloc[-1]['time'])
        for i in range(1, 11):
            time.sleep(2)
            new_time = (last_time + pd.Timedelta(days=i)).strftime('%Y-%m-%d')
            new_close = last_close + i * 0.5
            sys_obj['candle'].append(pd.DataFrame({
                'time': [new_time],
                'open': [last_close + (i-1)*0.5],
                'high': [new_close + 1],
                'low': [new_close - 1],
                'close': [new_close],
            }))
            sys_obj['sma50'].append(pd.DataFrame({
                'time': [new_time], 'value': [new_close - 0.3],
            }))
            print(f'  append #{i}: time={new_time} close={new_close}  (version={sys_obj._version})')

    threading.Thread(target=live_feed, daemon=True).start()

    # ── 显示窗口 12 秒（2 秒后开始追加，共 3 次）──
    print('show(wait=12) — 观察 K 线每 2 秒自动追加...')
    chart.show(wait=12)

    sys_obj.stop_sync()
    chart.exit()
    print('done')
