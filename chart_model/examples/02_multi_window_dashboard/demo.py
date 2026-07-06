"""chart_model 复杂示例 — 2 Window × 多 pane × EMA 均线 × 动态更新

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

from chart_model import Model, Window, Chart, Series, Adapter


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


def live_feed():
    """只更新数据层，渲染由同步线程自动完成。所有指标从全量数据正确计算。"""
    # 自动更新

    # 追踪主图全量数据（含 volume），用于正确计算指标
    main_data = df.copy()
    # 追踪 4 个品种的 K线数据
    stock_data = [s['candle'].copy() for s in stocks]

    for n in range(1, 31):
        time.sleep(1)
        t = (lt + pd.Timedelta(days=n)).strftime('%Y-%m-%d')

        # ── 生成新 K线（随机红绿）──
        last = main_data.iloc[-1]
        nc = last['close'] + np.random.randn() * 2
        vol = int(max(50000, last['volume'] + np.random.randn() * 50000))
        up = np.random.rand() < 0.5
        body = abs(np.random.rand() * 2)
        if np.random.rand() < 0.5:
            o, c = nc - body, nc  # 阳线（close > open）
        else:
            o, c = nc + body, nc - body  # 阴线（close < open）
        h = max(o, c) + abs(np.random.rand() * 2)
        l = min(o, c) - abs(np.random.rand() * 2)

        new_bar = pd.DataFrame([{
            'time': t, 'open': o, 'high': h, 'low': l, 'close': nc, 'volume': vol
        }])
        main_data = pd.concat([main_data, new_bar], ignore_index=True)

        # ── 更新数据层（K线 + 成交量）──
        model['candle'].append(new_bar[['time', 'open', 'high', 'low', 'close']])
        model['volume'].append(new_bar[['time', 'open', 'close']].assign(value=vol))

        # ── 从全量 close 数据正确计算 SMA50 / SMA200 / SMA100 ──
        close_all = main_data['close']
        s50 = close_all.tail(50).mean()
        s200 = close_all.tail(200).mean()
        sa = close_all.tail(100).mean()

        # ── 从全量数据正确计算 RSI(14) ──
        delta = close_all.diff()
        gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
        loss = (-delta.clip(upper=0)).rolling(14).mean().iloc[-1]
        if loss != 0:
            rs = gain / loss
            r = 100 - 100 / (1 + rs)
        else:
            r = 50.0

        model['sma50'].append(pd.DataFrame({'time': [t], 'value': [s50]}))
        model['sma200'].append(pd.DataFrame({'time': [t], 'value': [s200]}))
        model['sma_area'].append(pd.DataFrame({'time': [t], 'value': [sa]}))
        model['rsi'].append(pd.DataFrame({'time': [t], 'value': [r]}))

        # ── 更新 4 个品种的 K线、均线和 MACD（全量数据正确计算）──
        for i in range(4):
            idx = i + 1
            sc_df = stock_data[i]
            last_sc = sc_df.iloc[-1]
            sc_base = last_sc['close'] + np.random.randn() * 2

            body = abs(np.random.rand() * 2)
            if np.random.rand() < 0.5:
                so, sc = sc_base - body, sc_base  # 阳线
            else:
                so, sc = sc_base + body, sc_base - body  # 阴线
            sh = max(so, sc) + abs(np.random.rand() * 2)
            sl = min(so, sc) - abs(np.random.rand() * 2)
            new_sc_bar = pd.DataFrame([{
                'time': t, 'open': so, 'high': sh, 'low': sl, 'close': sc
            }])
            stock_data[i] = pd.concat([sc_df, new_sc_bar], ignore_index=True)

            # 品种 K线
            if idx <= 2:
                model[f'candle{idx}'].append(new_sc_bar[['time', 'open', 'high', 'low', 'close']])
            else:
                model[f'candle{idx}'].append(pd.DataFrame({'time': [t], 'value': [sc]}))

            # 从全量数据正确计算 EMA12 / EMA26 / MACD
            s_close = stock_data[i]['close']
            e12 = s_close.ewm(span=12, adjust=False).mean().iloc[-1]
            e26 = s_close.ewm(span=26, adjust=False).mean().iloc[-1]
            macd_line = s_close.ewm(span=12, adjust=False).mean() - s_close.ewm(span=26, adjust=False).mean()
            signal = macd_line.ewm(span=9, adjust=False).mean()
            hist_val = (macd_line - signal).iloc[-1]

            model[f'ema12_{idx}'].append(pd.DataFrame({'time': [t], 'value': [e12]}))
            model[f'ema26_{idx}'].append(pd.DataFrame({'time': [t], 'value': [e26]}))
            model[f'macd_{idx}'].append(pd.DataFrame({'time': [t], 'value': [hist_val]}))

            # stock2 (idx=2) 和 stock3 (idx=3) 的 volume/oi 更新
            if idx == 2 or idx == 3:
                s_vol = int(max(30000, abs(np.random.randn() * 150000 + 150000)))
                s_oi  = int(max(2000, abs(np.random.randn() * 8000 + 8000)))
                model[f'volume{idx}'].append(pd.DataFrame({
                    'time': [t], 'value': [s_vol], 'open': [so], 'close': [sc]
                }))
                model[f'oi{idx}'].append(pd.DataFrame({'time': [t], 'value': [s_oi]}))

        print(f'  [{n:2d}/30] t={t} close={nc:.2f} RSI={r:.1f}')

    print('live_feed: 数据更新完成')



if __name__ == '__main__':
    # ═══ 初始数据生成 ═══
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
    model = Model(
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
            # stock1: Candle, stock2: Candle+Volume+OI, stock3: Line+Volume+OI, stock4: Line
            Series(name='candle1',  display_name='K线',   chart='stock1', pane=0, type='candle',
                   up_color='rgba(39,157,130,100)', down_color='rgba(200,97,100,100)'),
            # stock2 — 主序列：candle + volume + oi（均映射到 chart.candle/volume/oi）
            Series(name='candle2',  display_name='K线', chart='stock2', pane=0, type='candle',
                   up_color='rgba(39,157,130,100)', down_color='rgba(200,97,100,100)'),
            Series(name='volume2',  display_name='Volume', chart='stock2', pane=0, type='volume'),
            Series(name='oi2',      display_name='OI',     chart='stock2', pane=0, type='open_interest'),
            # stock3 — 主序列：volume + oi（line 类型非主序列，走 create_line）
            Series(name='volume3',  display_name='Volume', chart='stock3', pane=0, type='volume'),
            Series(name='oi3',      display_name='OI',     chart='stock3', pane=0, type='open_interest'),
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
    model['candle'].set(candle_df)
    for name, data in [('sma50', sma50_data), ('sma200', sma200_data),
                       ('volume', vol_df), ('sma_area', sma_area_data), ('rsi', rsi_data)]:
        model[name].set(data)

    for i, s in enumerate(stocks, 1):
        if i <= 2:  # stock1=candle, stock2=candle — 传完整 OHLC
            model[f'candle{i}'].set(s['candle'])
        else:  # stock3, stock4: line — 传收盘价
            model[f'candle{i}'].set(s['candle'][['time']].assign(value=s['candle']['close']))
        model[f'ema12_{i}'].set(s['ema12'])
        model[f'ema26_{i}'].set(s['ema26'])
        macd_df = s['macd'][['time']].copy()
        macd_df['value'] = s['macd']['histogram']
        model[f'macd_{i}'].set(macd_df)

    # stock2 的 volume/oi 初始数据
    s2 = stocks[1]
    vol2_df = s2['candle'][['time', 'open', 'close']].copy()
    vol2_df['value'] = np.random.randint(80000, 400000, len(s2['candle']))
    model['volume2'].set(vol2_df)
    model['oi2'].set(s2['candle'][['time']].assign(value=np.random.randint(5000, 20000, len(s2['candle']))))

    # stock3 的 volume/oi 初始数据
    s3 = stocks[2]
    vol3_df = s3['candle'][['time', 'open', 'close']].copy()
    vol3_df['value'] = np.random.randint(80000, 400000, len(s3['candle']))
    model['volume3'].set(vol3_df)
    model['oi3'].set(s3['candle'][['time']].assign(value=np.random.randint(5000, 20000, len(s3['candle']))))

    model['candle'].add_marker(time=sma50_data.iloc[0]['time'], position='below',
                                 shape='arrow_up', color='#00C853', text='金叉')

    # ═══ 构建 + 渲染 ═══
    layout = model.build(live=True)
    print(f'build(live=True) OK  sync_thread={model._sync_thread}')
    print(f'  总 Window: {len(layout.windows)}')
    print(f'  总 Chart:  {len(layout.charts)}')
    print(f'  总 Series: {len(layout.series)}')
    for c_name, panes in layout.pane_info.items():
        print(f'  {c_name}: { {k: len(v) for k, v in panes.items()} }')

    chart = Adapter.render(layout, width=1000, height=800)
    print(f'render OK — 类型: {type(chart).__name__}')

    # ═══ 动态更新（只用同步线程，不直连渲染层）═══
    lt = pd.Timestamp(candle_df.iloc[-1]['time'])
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

    model.stop_sync()
    feed_thread.join()
    print(f'done — 最终版本: candle={model._series_versions.get("candle")}')
