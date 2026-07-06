"""多 Window 渲染测试（不打开窗口，只验证代码逻辑）"""
import pandas as pd
from chart_model import Model, Window, Chart, Series, Adapter

# ── 单 Window → 返回单个 Chart ──
model = Model(
    windows=[Window(name='main', display_name='主窗口')],
    charts=[Chart(name='price', display_name='Price', window='main', interval='1day', precision=2, position=111)],
    series=[Series(name='candle', display_name='', chart='price', pane=0, type='candle')],
)
model['candle'].set(pd.DataFrame({'time': [1, 2, 3], 'open': [10, 11, 12],
                                     'high': [12, 13, 14], 'low': [9, 10, 11],
                                     'close': [11, 12, 13]}))
layout = model.build(live=True)
r = Adapter.render(layout, width=800, height=600)
assert not isinstance(r, tuple), f"单 Window 应返回 Chart，不是 tuple: {type(r)}"
print(f'✓ 单 Window: type={type(r).__name__}')

# ── 双 Window → 返回 tuple[Chart, Chart] ──
model2 = Model(
    windows=[Window(name='a', display_name='A'), Window(name='b', display_name='B')],
    charts=[
        Chart(name='ca', display_name='A', window='a', interval='1day', precision=2, position=111),
        Chart(name='cb', display_name='B', window='b', interval='1day', precision=2, position=111),
    ],
    series=[
        Series(name='sa', display_name='', chart='ca', pane=0, type='candle'),
        Series(name='sb', display_name='', chart='cb', pane=0, type='candle'),
    ],
)
model2['sa'].set(pd.DataFrame({'time': [1, 2, 3], 'open': [10, 11, 12],
                                  'high': [12, 13, 14], 'low': [9, 10, 11],
                                  'close': [11, 12, 13]}))
model2['sb'].set(pd.DataFrame({'time': [1, 2, 3], 'open': [10, 11, 12],
                                  'high': [12, 13, 14], 'low': [9, 10, 11],
                                  'close': [11, 12, 13]}))
layout2 = model2.build(live=True)
r2 = Adapter.render(layout2, width=800, height=600)
assert isinstance(r2, tuple), f"双 Window 应返回 tuple，不是: {type(r2)}"
assert len(r2) == 2, f"双 Window 应返回 2 个 Chart，不是 {len(r2)}"
print(f'✓ 双 Window: type={type(r2).__name__} len={len(r2)}')

# ── 验证 _render_ready 标志 ──
assert model._render_ready == True, "单 Window _render_ready 应为 True"
assert model2._render_ready == True, "双 Window _render_ready 应为 True"
print('✓ _render_ready 标志正确')

# ── 清理 ──
model.stop_sync()
model2.stop_sync()

print('\n全部验证通过！')