"""chart_model drawing 功能测试"""
import sys; sys.path.insert(0, '..')
from chart_model import Model, Window, Chart, Series, DrawingManager

# ── 测试 1: drawing.add + len + contains + names ──
model = Model(
    windows=[Window(name='main', display_name='测试')],
    charts=[Chart(name='price', display_name='Price', window='main', interval='1day')],
    series=[Series(name='candle', display_name='K线', chart='price', pane=0, type='candle')],
)
print('=== System 创建成功 ===')

model.drawing.add('阻力位', chart='price', pane=0,
                     type='horizontal_line', price=5200, color='#FF0000', text='阻力')
model.drawing.add('支撑位', chart='price', pane=0,
                     type='horizontal_line', price=4800, color='#00FF00', text='支撑')
model.drawing.add('入场点', chart='price', pane=0,
                     type='vertical_line', time=1700000000, color='#2196F3', text='入场')

assert '阻力位' in model.drawing, 'contains 失败'
assert len(model.drawing) == 3, f'len 应为 3，实际 {len(model.drawing)}'
print(f'drawing names: {model.drawing.names}')
print('=== drawing.add + contains + len + names 验证通过 ===')

# ── 测试 2: delete 两种方式 ──
model.drawing.delete('阻力位')
assert '阻力位' not in model.drawing
assert len(model.drawing) == 2
print(f'delete 后 names: {model.drawing.names}')

del model.drawing['支撑位']
assert '支撑位' not in model.drawing
assert len(model.drawing) == 1
print(f'del 后 names: {model.drawing.names}')
print('=== drawing.delete + __delitem__ 验证通过 ===')

# ── 测试 3: build() 注入 drawings ──
layout = model.build()
assert len(layout.drawings) == 1, f'layout.drawings 应为 1，实际 {len(layout.drawings)}'
print(f'layout.drawings: {[(d.name, d.chart, d.type) for d in layout.drawings]}')
drawings_of_price = layout.drawings_of('price')
assert len(drawings_of_price) == 1
print(f'drawings_of price: {[(d.name, d.type, d.time) for d in drawings_of_price]}')
print('=== build() drawing 注入 + drawings_of() 验证通过 ===')

# ── 测试 4: 参数校验 ──
try:
    model.drawing.add('bad', chart='price', pane=0, type='unknown_type', price=100)
    assert False, '应抛出 type 错误'
except ValueError as e:
    print(f'type 校验通过: {e}')

try:
    model.drawing.add('dup1', chart='price', pane=0, type='horizontal_line', price=100)
    model.drawing.add('dup1', chart='price', pane=0, type='vertical_line', time=100)
    assert False, '应抛出 name 重复错误'
except ValueError as e:
    print(f'name 重复校验通过: {e}')

try:
    model.drawing.add('missing', chart='price', pane=0, type='trend_line')
    assert False, '应抛出缺少参数错误'
except ValueError as e:
    print(f'缺失参数校验通过: {e}')

try:
    model.drawing.add('unknown', chart='price', pane=0, type='horizontal_line',
                          price=100, unknown_param='test')
    assert False, '应抛出未知参数错误'
except ValueError as e:
    print(f'未知参数校验通过: {e}')

try:
    model.drawing.add('bad_chart', chart='not_exist', pane=0, type='horizontal_line', price=100)
    assert False, '应抛出 chart 不存在错误'
except ValueError as e:
    print(f'chart 引用校验通过: {e}')

# ── 测试 5: build(live=True) 后的 _chart_map ──
sys2 = Model(
    windows=[Window(name='main', display_name='测试')],
    charts=[Chart(name='price', display_name='Price', window='main', interval='1day')],
    series=[Series(name='candle', display_name='K线', chart='price', pane=0, type='candle')],
)
# 确认 _chart_map 和 _render_drawings 字段存在
assert hasattr(sys2, '_chart_map'), '_chart_map 字段不存在'
assert hasattr(sys2, '_render_drawings'), '_render_drawings 字段不存在'
assert hasattr(sys2, '_drawing_version'), '_drawing_version 字段不存在'
assert hasattr(sys2, '_sync_last_drawing_version'), '_sync_last_drawing_version 字段不存在'
print('=== System drawing 字段验证通过 ===')

print()
print('✅ 全部 drawing 测试通过!')