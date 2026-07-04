"""ind_sys 复杂示例 — 2 Window × 多 pane × EMA 均线 × 动态更新

Window 1: 主窗口（1 chart × 4 pane）
  ├── pane 0: K线 (candle) + SMA50 + SMA200
  ├── pane 1: Volume
  ├── pane 2: SMA 面积图
  └── pane 3: RSI

Window 2: 多 chart 窗口（4 chart × 2 pane，仅声明不渲染）
  ├── Chart "stock1":  pane 0=EMA12/26  pane 1=MACD
  ├── Chart "stock2":  pane 0=EMA12/26  pane 1=MACD
  ├── Chart "stock3":  pane 0=EMA12/26  pane 1=MACD
  └── Chart "stock4":  pane 0=EMA12/26  pane 1=MACD
"""
import os
import sys
import threading
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from ind_sys import System, Window, Chart, Series, Adapter


def generate_kline(n=200, seed=42):
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

def sma(df, period):
    return df[['time']].assign(value=df['close'].rolling(period).mean()).dropna()

def ema(df, period):
    return df[['time']].assign(value=df['close'].ewm(span=period, adjust=False).mean()).dropna()

def rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_ = 100 - 100 / (1 + rs)
    return df[['time']].assign(value=rsi_).dropna()

def macd(df, fast=12, slow=26, signal=9):
    e1 = df['close'].ewm(span=fast, adjust=False).mean()
    e2 = df['close'].ewm(span=slow, adjust=False).mean()
    m = e1 - e2
    s = m.ewm(span=signal, adjust=False).mean()
    h = m - s
    return df[['time']].assign(macd=m, signal=s, histogram=h).dropna()


if __name__ == '__main__':
    # ═══ 数据生成 ═══
    df = generate_kline(200)

    sma50_data = sma(df, 50)
    sma200_data = sma(df, 200)
    sma_area_data = sma(df, 100)
    rsi_data = rsi(df, 14)
    macd_data = macd(df, 12, 26, 9)

    candle_df = df[['time', 'open', 'high', 'low', 'close']]
    vol_df = df[['time', 'open', 'close']].copy()
    vol_df['value'] = df['volume']

    # 4 品种数据
    def build_stock(seed):
        d = generate_kline(200, seed)
        return {'candle': d[['time', 'open', 'high', 'low', 'close']],
                'ema12': ema(d, 12), 'ema26': ema(d, 26),
                'macd': macd(d, 12, 26, 9)}

    stocks = [build_stock(s) for s in [43, 44, 45, 46]]

    # ═══ 系统声明 ═══
    sys_obj = System(
        windows=[Window(name='main', display_name='主窗口'),
                 Window(name='multi', display_name='多品种')],
        charts=[
            Chart(name='main', display_name='主图', window='main',
                  interval='1day', precision=2, position=111),
            *[Chart(name=f'stock{i}', display_name=f'品种{i}', window='multi',
                    interval='1day', precision=2, position=220+i)
              for i in range(1, 5)],
        ],
        series=[
            # Window 1: 4 pane
            Series(name='candle',   display_name='K线',    chart='main', pane=0, type='candle'),
            Series(name='sma50',    display_name='SMA50',  chart='main', pane=0, type='line', color='#FF6F00', group='SMA'),
            Series(name='sma200',   display_name='SMA200', chart='main', pane=0, type='line', color='#E040FB', group='SMA'),
            Series(name='volume',   display_name='Volume', chart='main', pane=1, type='volume'),
            Series(name='sma_area', display_name='SMA100', chart='main', pane=2, type='area',
                   color='#2196F3', top_color='rgba(33,150,243,0.3)', bottom_color='rgba(33,150,243,0)'),
            Series(name='rsi',      display_name='RSI',    chart='main', pane=3, type='line', color='#9C27B0'),
            # Window 2: 4 品种 × 2 pane
            # stock1: Candle, stock2: OHLCBar, stock3/4: Line（收盘价线）
            Series(name='candle1',  display_name='K线',   chart='stock1', pane=0, type='candle',
                   up_color='rgba(39,157,130,100)', down_color='rgba(200,97,100,100)'),
            Series(name='candle2',  display_name='美国线', chart='stock2', pane=0, type='ohlc_bar',
                   up_color='rgba(39,157,130,100)', down_color='rgba(200,97,100,100)'),
            *[Series(name=f'candle{i}',  display_name=f'K线{i}',  chart=f'stock{i}', pane=0, type='line',
                     color='#666666', price_scale_id=None) for i in range(3, 5)],
            *[Series(name=f'ema12_{i}', display_name=f'EMA12', chart=f'stock{i}', pane=0, type='line',
                     color='#FF6F00', group=f'MA{i}') for i in range(1, 5)],
            *[Series(name=f'ema26_{i}', display_name=f'EMA26', chart=f'stock{i}', pane=0, type='line',
                     color='#E040FB', group=f'MA{i}') for i in range(1, 5)],
            *[Series(name=f'macd_{i}',  display_name=f'MACD',  chart=f'stock{i}', pane=1, type='histogram',
                     color='#2196F3') for i in range(1, 5)],
        ],
    )

    # ═══ 设置数据 ═══
    sys_obj['candle'].set(candle_df)
    for name, data in [('sma50', sma50_data), ('sma200', sma200_data),
                       ('volume', vol_df), ('sma_area', sma_area_data), ('rsi', rsi_data)]:
        sys_obj[name].set(data)

    for i, s in enumerate(stocks, 1):
        if i <= 2:  # stock1=candle, stock2=ohlc_bar — 传完整 OHLC
            sys_obj[f'candle{i}'].set(s['candle'])
        else:  # stock3, stock4: line — 传收盘价
            sys_obj[f'candle{i}'].set(s['candle'][['time']].assign(value=s['candle']['close']))
        sys_obj[f'ema12_{i}'].set(s['ema12'])
        sys_obj[f'ema26_{i}'].set(s['ema26'])
        macd_df = s['macd'][['time']].copy()
        macd_df['value'] = s['macd']['histogram']
        sys_obj[f'macd_{i}'].set(macd_df)

    sys_obj['candle'].add_marker(time=sma50_data.iloc[0]['time'], position='below',
                                 shape='arrow_up', color='#00C853', text='金叉')

    # ═══ 构建 + 渲染 ═══
    layout = sys_obj.build(live=True)
    print(f'build(live=True) OK  sync_thread={sys_obj._sync_thread}')
    print(f'  总 Window: {len(layout.windows)}')
    print(f'  总 Chart:  {len(layout.charts)}')
    print(f'  总 Series: {len(layout.series)}')
    for c_name, panes in layout.pane_info.items():
        print(f'  {c_name}: { {k: len(v) for k, v in panes.items()} }')

    chart = Adapter.render(layout, width=1000, height=800)
    print(f'render OK — 类型: {type(chart).__name__}')

    # ═══ 动态更新（只用同步线程，不直连渲染层）═══
    lt = pd.Timestamp(candle_df.iloc[-1]['time'])

    def live_feed():
        """只更新数据层，渲染由同步线程自动完成"""
        np.random.seed(int(time.time()))
        last_c = candle_df.iloc[-1]['close']
        last_v = df.iloc[-1]['volume']
        # 4 个品种的收盘价追踪
        stock_seeds = [43, 44, 45, 46]
        stock_closes = []
        np.random.seed(42)
        for seed in stock_seeds:
            np.random.seed(seed)
            d = generate_kline(200, seed)
            stock_closes.append(d['close'].iloc[-1])

        for n in range(1, 31):
            time.sleep(1)
            t = (lt + pd.Timedelta(days=n)).strftime('%Y-%m-%d')
            nc = last_c + np.random.randn() * 2
            last_c = nc
            vol_val = int(max(50000, last_v + np.random.randn() * 50000))
            last_v = vol_val

            o, h, l, c_ = nc - np.random.rand(), nc + np.random.rand(), nc - np.random.rand(), nc
            s50 = nc + np.random.randn() * 0.3
            s200 = nc + np.random.randn() * 0.5
            sa = nc + np.random.randn() * 0.4
            r = 50 + np.random.randn() * 10

            # 只更新数据层，同步线程自动检测变化并推送渲染层
            sys_obj['candle'].append(pd.DataFrame({'time':[t],'open':[o],'high':[h],'low':[l],'close':[c_]}))
            sys_obj['sma50'].append(pd.DataFrame({'time':[t],'value':[s50]}))
            sys_obj['sma200'].append(pd.DataFrame({'time':[t],'value':[s200]}))
            sys_obj['sma_area'].append(pd.DataFrame({'time':[t],'value':[sa]}))
            sys_obj['rsi'].append(pd.DataFrame({'time':[t],'value':[r]}))
            sys_obj['volume'].append(pd.DataFrame({'time':[t],'value':[vol_val],'open':[o],'close':[c_]}))

            # 更新 4 个品种的收盘价、均线和 MACD
            for i in range(4):
                sc = stock_closes[i] + np.random.randn() * 2
                stock_closes[i] = sc
                idx = i + 1
                ema12_val = sc + np.random.randn() * 0.5
                ema26_val = sc + np.random.randn() * 0.8
                macd_val = np.random.randn() * 5

                if idx <= 2:  # stock1=candle, stock2=ohlc_bar — OHLC
                    o = sc - np.random.rand()
                    h = sc + np.random.rand()
                    l = sc - np.random.rand()
                    c = sc
                    sys_obj[f'candle{idx}'].append(pd.DataFrame({
                        'time':[t], 'open':[o], 'high':[h], 'low':[l], 'close':[c]
                    }))
                else:  # stock3, stock4: line
                    sys_obj[f'candle{idx}'].append(pd.DataFrame({'time':[t], 'value':[sc]}))

                sys_obj[f'ema12_{idx}'].append(pd.DataFrame({'time':[t],'value':[ema12_val]}))
                sys_obj[f'ema26_{idx}'].append(pd.DataFrame({'time':[t],'value':[ema26_val]}))
                sys_obj[f'macd_{idx}'].append(pd.DataFrame({'time':[t],'value':[macd_val]}))

            print(f'  [{n:2d}/30] t={t} close={nc:.2f}')

        print('live_feed: 数据更新完成')

    feed_thread = threading.Thread(target=live_feed)
    feed_thread.start()

    if isinstance(chart, tuple):
        print(f'多窗口模式: {len(chart)} 个窗口，显示中...')
        for c in chart:
            c.show(block=False)
        try:
            while any(c.wv.wv_process.is_alive() for c in chart):
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        for c in chart:
            c.exit()
    else:
        print('show(block=True) — 同步线程自动推送，约 30 秒...')
        chart.show(block=True)

    sys_obj.stop_sync()
    feed_thread.join()
    print(f'done — 最终版本: candle={sys_obj._series_versions.get("candle")}')
