"""验证 drawing 错误提示信息"""
import sys; sys.path.insert(0, '..')
from chart_model import Model, Window, Chart, Series, DrawingManager

model = Model(
    windows=[Window(name='main', display_name='测试')],
    charts=[Chart(name='price', display_name='Price', window='main', interval='1day')],
    series=[Series(name='candle', display_name='K线', chart='price', pane=0, type='candle')],
)

# 1. help 查询
print('=== help 示例 ===')
print(DrawingManager.help('trend_line'))
print()
print(DrawingManager.help('horizontal_line'))
print()

# 2. 错误 type
print('=== 错误 type 提示 ===')
try:
    model.drawing.add('bad', chart='price', type='unknown_type')
except ValueError as e:
    print(e)
print()

# 3. 缺少参数
print('=== 缺少必选参数提示 ===')
try:
    model.drawing.add('missing', chart='price', type='trend_line')
except ValueError as e:
    print(e)
print()

# 4. 未知参数
print('=== 未知参数提示 ===')
try:
    model.drawing.add('unknown', chart='price', type='horizontal_line',
                          price=100, bad_param=1)
except ValueError as e:
    print(e)
print()

# 5. 重复 name
print('=== 重复 name 提示 ===')
try:
    model.drawing.add('dup', chart='price', type='horizontal_line', price=100)
    model.drawing.add('dup', chart='price', type='vertical_line', time=100)
except ValueError as e:
    print(e)
print()

# 6. chart 不存在
print('=== chart 不存在提示 ===')
try:
    model.drawing.add('bad_chart', chart='not_exist', type='horizontal_line', price=100)
except ValueError as e:
    print(e)
print()

print('=== 全部提示信息验证通过 ===')