"""验证 build(live=True) 后 drawing add/del"""
import sys; sys.path.insert(0, '..')
import numpy as np, pandas as pd
from chart_model import Model, Window, Chart, Series

np.random.seed(42)
dates = pd.date_range('2023-01-01', periods=30, freq='D')
prices = 100 + np.cumsum(np.random.randn(30) * 2)
candle_df = pd.DataFrame({
    'time': dates.strftime('%Y-%m-%d'),
    'open': prices, 'high': prices+2, 'low': prices-2, 'close': prices+0.5,
})

model = Model(
    windows=[Window(name='main', display_name='测试')],
    charts=[Chart(name='price', display_name='Price', window='main', interval='1day')],
    series=[Series(name='candle', display_name='K线', chart='price', pane=0, type='candle')],
)
model['candle'].set(candle_df)

# build(live=True)
layout = model.build(live=True)
assert model._sync_thread is not None

# live 后 add
model.drawing.add('hl1', chart='price', pane=0, type='horizontal_line', price=105, color='yellow')
assert 'hl1' in model.drawing

# live 后 del
del model.drawing['hl1']
assert 'hl1' not in model.drawing

# 批量 add 再部分 del
model.drawing.add('a', chart='price', pane=0, type='horizontal_line', price=100)
model.drawing.add('b', chart='price', pane=0, type='vertical_line', time=candle_df.iloc[5]['time'])
model.drawing.add('c', chart='price', pane=0, type='horizontal_line', price=110)
model.drawing.add('d', chart='price', pane=0, type='vertical_line', time=candle_df.iloc[10]['time'])
assert len(model.drawing) == 4
del model.drawing['a']
del model.drawing['c']
assert len(model.drawing) == 2
assert 'b' in model.drawing
assert 'd' in model.drawing

# verify layout drawing count
layout2 = model.build()
assert len(layout2.drawings) == 2

model.stop_sync()
print('live 场景 drawing add/del 验证通过')