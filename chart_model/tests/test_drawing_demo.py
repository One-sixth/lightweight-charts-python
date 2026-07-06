"""验证 drawing 示例的数据逻辑（不打开窗口）"""
import sys; sys.path.insert(0, '..')
import numpy as np
import pandas as pd
from chart_model import Model, Window, Chart, Series

np.random.seed(42)
dates = pd.date_range('2023-01-01', periods=120, freq='D')
prices = 100 + np.cumsum(np.random.randn(120) * 2)
df = pd.DataFrame({
    'time': dates.strftime('%Y-%m-%d'),
    'open': prices,
    'high': prices + np.abs(np.random.randn(120) * 2) + 0.5,
    'low': prices - np.abs(np.random.randn(120) * 2) - 0.5,
    'close': prices + np.random.randn(120) * 0.8,
})
candle_df = df[['time','open','high','low','close']]

model = Model(
    windows=[Window(name='main', display_name='Drawing 测试')],
    charts=[Chart(name='price', display_name='Price', window='main', interval='1day', precision=2)],
    series=[Series(name='candle', display_name='K线', chart='price', pane=0, type='candle')],
)
model['candle'].set(candle_df)

# 添加 5 种 drawing
model.drawing.add('阻力位', chart='price', pane=0, type='horizontal_line', price=115, color='#EF5350', text='阻力')
model.drawing.add('买入', chart='price', pane=0, type='vertical_line', time=df.iloc[20]['time'], color='#42A5F5', text='买入')
model.drawing.add('通道', chart='price', pane=0, type='trend_line',
    start_time=df.iloc[5]['time'], start_price=float(df.iloc[5]['close']),
    end_time=df.iloc[45]['time'], end_price=float(df.iloc[45]['close']))
model.drawing.add('射线', chart='price', pane=0, type='ray_line',
    start_time=df.iloc[60]['time'], value=float(df.iloc[60]['close']))
model.drawing.add('区间', chart='price', pane=0, type='box',
    start_time=df.iloc[70]['time'], start_price=float(df.iloc[70:95]['low'].min()) - 2,
    end_time=df.iloc[95]['time'], end_price=float(df.iloc[70:95]['high'].max()) + 2)

layout = model.build()
assert len(layout.drawings) == 5, f'应有 5 个 drawing，实际 {len(layout.drawings)}'

docs = layout.drawings_of('price')
assert len(docs) == 5

types = {d.type for d in docs}
assert types == {'horizontal_line', 'vertical_line', 'trend_line', 'ray_line', 'box'}, f'{types}'

print('===== drawing 数据验证通过 =====')
print(f'drawings: {len(layout.drawings)} 个')
for d in layout.drawings:
    print(f'  {d.name:8s}  type={d.type:16s}  pane={d.pane}')
print('OK')