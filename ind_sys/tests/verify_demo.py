"""验证 demo 的 build + render 路径 — 不打开窗口"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from ind_sys import System, Window, Chart, Series, Adapter
import numpy as np, pandas as pd

def generate_kline(n=200, seed=42):
    np.random.seed(seed)
    dates = pd.date_range('2023-01-01', periods=n, freq='D')
    prices = 100 + np.cumsum(np.random.randn(n) * 2)
    return pd.DataFrame({
        'time': dates.strftime('%Y-%m-%d'),
        'open': prices, 'high': prices + np.abs(np.random.randn(n) * 2) + 0.5,
        'low': prices - np.abs(np.random.randn(n) * 2) - 0.5,
        'close': prices + np.random.randn(n) * 0.8,
        'volume': np.random.randint(100000, 500000, n),
    })

def sma(df, period): return df[['time']].assign(value=df['close'].rolling(period).mean()).dropna()
def ema(df, period): return df[['time']].assign(value=df['close'].ewm(span=period, adjust=False).mean()).dropna()
def rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_ = 100 - 100 / (1 + rs)
    return df[['time']].assign(value=rsi_).dropna()

df = generate_kline(200)
candle_df = df[['time', 'open', 'high', 'low', 'close']]
vol_df = df[['time', 'open', 'close']].copy(); vol_df['value'] = df['volume']

sma50_data = sma(df, 50); sma200_data = sma(df, 200)
sma_area_data = sma(df, 100); rsi_data = rsi(df, 14)

sys_obj = System(
    windows=[Window(name='main', display_name='主窗口'),
             Window(name='multi', display_name='多品种')],
    charts=[
        Chart(name='main', display_name='主图', window='main',
              interval='1day', precision=2, position=111),
        *[Chart(name=f'stock{i}', display_name=f'品种{i}', window='multi',
                interval='1day', precision=2, position=410+i) for i in range(1, 5)],
    ],
    series=[
        Series(name='candle', display_name='K线', chart='main', pane=0, type='candle'),
        Series(name='sma50', display_name='SMA50', chart='main', pane=0, type='line', color='#FF6F00', group='SMA'),
        Series(name='sma200', display_name='SMA200', chart='main', pane=0, type='line', color='#E040FB', group='SMA'),
        Series(name='volume', display_name='Volume', chart='main', pane=1, type='volume'),
        Series(name='sma_area', display_name='SMA100', chart='main', pane=2, type='area',
               color='#2196F3', top_color='rgba(33,150,243,0.3)', bottom_color='rgba(33,150,243,0)'),
        Series(name='rsi', display_name='RSI', chart='main', pane=3, type='line', color='#9C27B0'),
        *[Series(name=f'candle{i}', display_name=f'K线{i}', chart=f'stock{i}', pane=0, type='line',
                 color='#666666', price_scale_id=None) for i in range(1, 5)],
        *[Series(name=f'ema12_{i}', display_name=f'EMA12', chart=f'stock{i}', pane=0, type='line',
                 color='#FF6F00', group=f'MA{i}') for i in range(1, 5)],
        *[Series(name=f'ema26_{i}', display_name=f'EMA26', chart=f'stock{i}', pane=0, type='line',
                 color='#E040FB', group=f'MA{i}') for i in range(1, 5)],
        *[Series(name=f'macd_{i}', display_name=f'MACD', chart=f'stock{i}', pane=1, type='histogram',
                 color='#2196F3') for i in range(1, 5)],
    ],
)

sys_obj['candle'].set(candle_df)
for name, data in [('sma50',sma50_data),('sma200',sma200_data),('volume',vol_df),('sma_area',sma_area_data),('rsi',rsi_data)]:
    sys_obj[name].set(data)

def build_stock(seed):
    d = generate_kline(200, seed)
    return {
        'close_line': d[['time']].assign(value=d['close']),
        'ema12': ema(d, 12), 'ema26': ema(d, 26),
    }

stocks = [build_stock(s) for s in [43, 44, 45, 46]]
for i, s in enumerate(stocks, 1):
    sys_obj[f'candle{i}'].set(s['close_line'])
    sys_obj[f'ema12_{i}'].set(s['ema12'])
    sys_obj[f'ema26_{i}'].set(s['ema26'])

layout = sys_obj.build(live=True)
print(f'build OK — {len(layout.windows)} Window, {len(layout.charts)} Chart, {len(layout.series)} Series')

# 验证所有 series 数据完整性
for name in ['candle','sma50','sma200','volume','sma_area','rsi']:
    d = sys_obj.get_data(name)
    assert d is not None and not d.empty, f'{name} 数据为空'
for i in range(1,5):
    for n in [f'candle{i}', f'ema12_{i}', f'ema26_{i}']:
        d = sys_obj.get_data(n)
        assert d is not None and not d.empty, f'{n} 数据为空'

print('数据完整性验证通过 OK')

# 测试 render 调用（不显示窗口）
result = Adapter.render(layout, width=1000, height=800)
if isinstance(result, tuple):
    print(f'多 Window 渲染: {len(result)} 个 chart 实例')
else:
    print(f'单 Window 渲染: 1 个 chart 实例')

print(f'_series_map 条目数: {len(sys_obj._series_map)}')
print(f'_render_ready: {sys_obj._render_ready}')

sys_obj.stop_sync()
print('全部验证通过！')