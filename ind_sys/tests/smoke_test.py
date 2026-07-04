"""ind_sys 冒烟测试"""
import pandas as pd
from ind_sys import System, Window, Chart, Series, SeriesType, SystemLayout, parse_interval

# ── parse_interval 测试 ──
assert parse_interval(60) == 60
assert parse_interval('1day') == 86400
assert parse_interval('5min') == 300
assert parse_interval('15sec') == 15
assert parse_interval('1h') == 3600
assert parse_interval('2d') == 172800
try:
    parse_interval('abc')
    print('ERROR')
except ValueError:
    pass
print('=== parse_interval 验证通过 ===')
print(f"  '1day'={parse_interval('1day')} '5min'={parse_interval('5min')} '15sec'={parse_interval('15sec')}")
print()

# 构造测试数据
df_candle = pd.DataFrame({'time':[1,2,3], 'open':[10,11,12], 'high':[12,13,14], 'low':[9,10,11], 'close':[11,12,13]})
df_sma = pd.DataFrame({'time':[1,2,3], 'value':[10.5,11.5,12.5]})
df_vol = pd.DataFrame({'time':[1,2,3], 'value':[100,200,150], 'open':[10,11,12], 'close':[11,12,13]})
df_rsi = pd.DataFrame({'time':[1,2,3], 'value':[55,45,60]})

# ── 正常构建（interval 字符串）──
sys_obj = System(
    windows=[Window(name='main', display_name='主窗口')],
    charts=[
        Chart(name='price', display_name='价格', window='main', interval='1hour', precision=2, position=211),
        Chart(name='ind', display_name='指标', window='main', interval='15min', precision=4, position=212),
    ],
    series=[
        Series(name='candle', display_name='K线', chart='price', pane=0, type='candle'),
        Series(name='sma20', display_name='SMA20', chart='price', pane=0, type='line', color='#FF9800', group='MA'),
        Series(name='vol', display_name='成交量', chart='price', pane=1, type='volume'),
        Series(name='rsi', display_name='RSI', chart='ind', pane=0, type='line', color='#9C27B0'),
    ],
)

# ── 链式 API ──
sys_obj['candle'].set(df_candle)
sys_obj['sma20'].set(df_sma)
sys_obj['vol'].set(df_vol)
sys_obj['rsi'].set(df_rsi)

# ── build(live=True) 测试 ──
layout = sys_obj.build(live=True)
print('=== build(live=True) 成功 ===')
print(f'primary_charts: {layout.primary_charts}')
assert layout._system is sys_obj
assert sys_obj._sync_thread is not None
print(f'sync_thread: {sys_obj._sync_thread}')

# ── 数据操作 + 系列版本号 ──
v0 = sys_obj._series_versions.get('rsi', 0)
sys_obj['rsi'].append(pd.DataFrame({'time':[4,5], 'value':[65,70]}))
assert sys_obj._series_versions.get('rsi', 0) == v0 + 1
assert len(layout.get_data('rsi')) == 5
print(f'=== append + 版本号: {v0} -> {sys_obj._series_versions.get("rsi", 0)} ===')

sys_obj['rsi'].pop(2)
assert sys_obj._series_versions.get('rsi', 0) == v0 + 2
print(f'=== pop + 版本号: {sys_obj._series_versions.get("rsi", 0)} ===')

# ── Marker ──
sys_obj['candle'].add_marker(time=2, position='below', shape='arrow_up', color='#00FF00', text='买入')
sys_obj['candle'].add_markers([{'time':3, 'position':'above', 'shape':'arrow_down', 'color':'#FF0000'}])
assert len(layout.get_markers('candle')) == 2
print('=== add_marker + add_markers: 2 markers ===')

# ── stop_sync ──
sys_obj.stop_sync()
assert sys_obj._sync_thread is None
print('=== stop_sync 成功 ===')
print()

# ── Indicator 约束 ──
try:
    System(
        windows=[Window(name='w', display_name='w')],
        charts=[Chart(name='c', display_name='c', window='w', interval='1min')],
        series=[
            Series(name='k1', display_name='K1', chart='c', pane=0, type='candle'),
            Series(name='k2', display_name='K2', chart='c', pane=0, type='ohlc_bar'),
        ],
    ).build()
    print('ERROR')
except ValueError as e:
    print(f'=== Indicator 约束通过 ===\n  {e}')

# ── Chart 属性验证 ──
c = Chart(name='t', display_name='t', window='w', interval='5min', precision=4,
          position=221, xy=(0.1, 0.2), sync_id='g')
assert c.interval == '5min' and c.xy == (0.1, 0.2) and c.sync_id == 'g'
print(f'=== Chart 属性: interval={c.interval} xy={c.xy} sync_id={c.sync_id} ===')

# ── Series 无 data 字段 ──
import dataclasses
assert 'data' not in {f.name for f in dataclasses.fields(Series)}
assert 'period' not in {f.name for f in dataclasses.fields(Chart)}
print(f'=== Series 无 data 字段 + Chart 无 period 字段 ===')

print('\n全部测试通过!')
