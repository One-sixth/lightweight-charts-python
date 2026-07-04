"""多 Window 渲染测试（不打开窗口，只验证代码逻辑）"""
import pandas as pd
from ind_sys import System, Window, Chart, Series, Adapter

# ── 单 Window → 返回单个 Chart ──
sys_obj = System(
    windows=[Window(name='main', display_name='主窗口')],
    charts=[Chart(name='price', interval='1day', precision=2, position=111)],
    series=[Series(name='candle', chart='price', pane=0, type='candle')],
)
sys_obj['candle'].set(pd.DataFrame({'time': [1, 2, 3], 'open': [10, 11, 12],
                                     'high': [12, 13, 14], 'low': [9, 10, 11],
                                     'close': [11, 12, 13]}))
layout = sys_obj.build(live=True)
r = Adapter.render(layout, width=800, height=600)
assert not isinstance(r, tuple), f"单 Window 应返回 Chart，不是 tuple: {type(r)}"
print(f'✓ 单 Window: type={type(r).__name__}')

# ── 双 Window → 返回 tuple[Chart, Chart] ──
sys_obj2 = System(
    windows=[Window(name='a'), Window(name='b')],
    charts=[
        Chart(name='ca', window='a', interval='1day', precision=2, position=111),
        Chart(name='cb', window='b', interval='1day', precision=2, position=111),
    ],
    series=[
        Series(name='sa', chart='ca', pane=0, type='candle'),
        Series(name='sb', chart='cb', pane=0, type='candle'),
    ],
)
sys_obj2['sa'].set(pd.DataFrame({'time': [1, 2, 3], 'open': [10, 11, 12],
                                  'high': [12, 13, 14], 'low': [9, 10, 11],
                                  'close': [11, 12, 13]}))
sys_obj2['sb'].set(pd.DataFrame({'time': [1, 2, 3], 'open': [10, 11, 12],
                                  'high': [12, 13, 14], 'low': [9, 10, 11],
                                  'close': [11, 12, 13]}))
layout2 = sys_obj2.build(live=True)
r2 = Adapter.render(layout2, width=800, height=600)
assert isinstance(r2, tuple), f"双 Window 应返回 tuple，不是: {type(r2)}"
assert len(r2) == 2, f"双 Window 应返回 2 个 Chart，不是 {len(r2)}"
print(f'✓ 双 Window: type={type(r2).__name__} len={len(r2)}')

# ── 验证 _render_ready 标志 ──
assert sys_obj._render_ready == True, "单 Window _render_ready 应为 True"
assert sys_obj2._render_ready == True, "双 Window _render_ready 应为 True"
print('✓ _render_ready 标志正确')

# ── 清理 ──
sys_obj.stop_sync()
sys_obj2.stop_sync()

print('\n全部验证通过！')