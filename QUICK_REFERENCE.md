# lightweight-charts-python 快查文档


---

## 一、项目架构

```
lightweight-charts-python/
├── lightweight_charts/         ← Python 后端 (核心包)
│   ├── __init__.py             # 导出 Chart, JupyterChart, HTMLChart, PolygonChart
│   ├── abstract.py             # 核心类: Window, AbstractChart, Candlestick, Line, Histogram, SeriesCommon
│   ├── chart.py                # Chart (pywebview 桌面窗口实现)
│   ├── widgets.py              # JupyterChart, HTMLChart, QtChart, WxChart, StreamlitChart
│   ├── toolbox.py              # ToolBox (绘图的保存/加载/导入/导出)
│   ├── topbar.py               # TopBar + Widget/Switcher/Menu/Button/TextWidget
│   ├── table.py                # Table + Row + Section
│   ├── drawings.py             # Drawing 基类 + HorizontalLine, TrendLine, Box, VerticalLine, RayLine, VerticalSpan
│   ├── polygon.py              # Polygon.io API 集成
│   └── util.py                 # Pane, Events, Emitter, IDGen, 类型别名, 工具函数
├── src/                        ← TypeScript 前端 (由 rollup 构建到 js/)
│   ├── index.ts                # 入口
│   ├── plugin-base.ts          # 插件基类
│   ├── general/                # 通用 UI: handler, legend, menu, toolbox, topbar, styles.css
│   ├── drawing/                # 绘图工具实现: data-source, drawing-tool, pane-renderer, options
│   ├── trend-line/             # 趋势线
│   ├── horizontal-line/        # 水平线 + 射线
│   ├── vertical-line/          # 垂直线
│   ├── box/                    # 矩形框
│   └── helpers/                # canvas 渲染辅助, 时间处理
├── examples/                   # 25 个完整示例 (见下文)
├── test/                       # 单元测试
│   ├── run_tests.py            # 测试入口
│   ├── test_cleanup.py         # 资源全链路创建/删除 + JS TOML 审计
│   └── test_features.py        # 功能测试: 数据重命名/line追踪/截图/topbar事件
└── js/                         # 构建后前端 (bundle.js + lightweight-charts.js)
```

---

## 二、Python 类层次

```
Pane (util.py)                      ← 所有组件的基类 (拥有 id, run_script)
├── Window (abstract.py)            ← JS 通信层: run_script(), run_script_and_get()
├── SeriesCommon (abstract.py)      ← 数据系列基类
│   ├── Candlestick                 ← K线 + 成交量
│   │   └── AbstractChart           ← 图表主类 (多重继承 Candlestick + Pane)
│   ├── Line                        ← 折线
│   └── Histogram                   ← 柱状图
├── Drawing (drawings.py)
│   ├── TwoPointDrawing
│   ├── HorizontalLine / TrendLine / Box / VerticalLine / RayLine / VerticalSpan
├── TopBar + Widget 系列 (topbar.py)
│   ├── TextWidget / SwitcherWidget / MenuWidget / ButtonWidget
├── Table / Row / Section (table.py)
└── ToolBox (toolbox.py)
```

---

## 三、核心 API 速查

### 3.1 Chart (桌面窗口)

```python
from lightweight_charts import Chart

chart = Chart(
    width=800, height=600,          # 窗口尺寸
    x=None, y=None,                 # 窗口位置 (None=居中)
    title='',                       # 窗口标题
    toolbox=False,                  # 是否启用绘图工具箱
    inner_width=1.0, inner_height=1.0,  # 图表在窗口中的占比
    scale_candles_only=False,       # 缩放时仅依据K线
    position='left',                # 图表位置
    on_top=False, maximize=False,   # 窗口行为
    debug=False                     # 调试模式
)
```

### 3.2 HTMLChart (浏览器)

```python
from lightweight_charts import HTMLChart

chart = HTMLChart(
    width=1200, height=800,
    inner_height=-500,              # 子面板高度偏移
    filename='charts.html',         # 输出的 HTML 文件名
    toolbox=False
)
# ... 设置数据 ...
chart.load()                        # 生成 HTML 文件
# 然后用 webbrowser.open(chart.filename) 打开
```

### 3.3 其他 Widget 类型

| 类名 | 导入源 | 说明 |
|------|--------|------|
| `JupyterChart` | `lightweight_charts` | Jupyter Notebook 内嵌 |
| `QtChart` | `lightweight_charts.widgets` | PyQt5/PyQt6/PySide6 嵌入 |
| `WxChart` | `lightweight_charts.widgets` | wxPython 嵌入 |
| `StreamlitChart` | `lightweight_charts.widgets` | Streamlit 嵌入 |
| `ReflexChart` | `lightweight_charts` | Reflex 嵌入（生成 HTML / 直接返回 rx.Component） |

### 3.4 数据方法 (Candlestick)

```python
chart.set(df, keep_drawings=False)
# 设置初始数据。df 列: time/open/high/low/close + 可选 volume

chart.update(series)
# 更新最后一根 K 线

chart.update_from_tick(series, cumulative_volume=False)
# 从 tick 更新 K 线

chart.pop(count=1)
# v5.0.9+ : 从系列末尾移除指定数量的数据点

chart.update_bars(df)
# 批量 OHLCV 增量更新: 遍历df每行调用update()，JS命令合并为一条发送

chart.update_from_ticks(df, cumulative_volume=False)
# 批量 Tick 增量更新: 遍历df每行调用update_from_tick()，JS命令合并为一条发送

chart.set_period(seconds)
# 锁定时间级别: set()时跳过自动推断，所有时间戳对齐到锁定间隔
```

### 3.4.1 `set()` vs `reset()` 对比

| 资源 | `chart.set(df)` | `chart.reset()` |
|------|----------------|-----------------|
| K 线数据 | ✅ 替换 | ✅ 清空 |
| 成交量 | ✅ 替换 | ✅ 清空 |
| 持仓量 | ✅ 替换 | ✅ 删除 |
| **指标线 (Line/Histogram)** | ✅ **保留**，更新匹配列名的 | ❌ **全部删除** |
| **标记 (markers)** | ✅ **保留** | ❌ **全部清除** |
| **绘图 (drawings)** | ⚠️ 看 `keep_drawings` 参数 | ❌ **全部清除** |
| **PriceLine** | ✅ **保留** | ❌ **清除** |
| **Table** | ✅ **保留** | ❌ **清除** |
| **事件 handlers** | ✅ **保留** | ❌ **清除** |
| **TopBar** | ✅ 保留 | ✅ 保留 |
| **样式配置** | ✅ 保留 | ✅ 保留 |

**`set()` 行为：** 温和替换，只动 K 线/成交量/持仓量，其他一切不动。指标线只更新有匹配列名的，不匹配的保留旧数据。

**`reset()` 行为：** 彻底清空所有资源（K 线 + 指标线 + 标记 + 绘图 + PriceLine + Table + handlers），TopBar 和样式保留。

```python
# 场景 1: 切换股票，保留指标线
chart.set(new_df)              # 指标线保留，K 线替换
# 注意: 如果新数据不含指标列，指标线仍显示旧数据

# 场景 2: 切换股票，全部重来
chart.reset()                  # 一键清空所有
chart.set(new_df)              # 重新设置

# 场景 3: 切换时间周期，保留绘图
chart.set(new_df, keep_drawings=True)  # 绘图重定位到时间轴

# 场景 4: 切换时间周期，全部重来
chart.reset()
chart.set(new_df)
```

### 3.4.2 批量增量更新 — update_bars() / update_from_ticks()

批量增量更新，将多条 K 线或 tick 的 JS 命令合并为一条批量发送，大幅减少 JS 通信开销。

```python
# 批量 OHLCV 增量更新
chart.update_bars(df)
# df: DataFrame, 列: time/open/high/low/close + 可选 volume/open_interest
# 遍历每一行，复用 update() 的逻辑（覆盖/追加 + new_bar 事件）
# 所有 JS 命令合并为一条 run_script 发送

# 批量 Tick 增量更新
chart.update_from_ticks(df, cumulative_volume=False)
# df: DataFrame, 列: time/price + 可选 volume
# 遍历每一行，复用 update_from_tick() 的 tick 聚合逻辑
# 所有 JS 命令合并为一条 run_script 发送
```

### 3.4.3 锁定时间级别 — set_period()

锁定 `_interval`，`set()` 时跳过自动推断，并将 DataFrame 中所有时间戳对齐到锁定间隔。

```python
chart.set_period(60)       # 锁定到 1 分钟 (60s)
chart.set_period(300)      # 锁定到 5 分钟 (300s)
chart.set_period(3600)     # 锁定到 1 小时 (3600s)
chart.set_period(None)     # 解锁，恢复自动推断

# 锁定后 set() 的行为:
chart.set_period(3600)     # 锁定为 1 小时
chart.set(df_30min)        # 传入 30 分钟数据 → 时间戳对齐到整点
print(chart._interval)     # 仍然是 3600
print(chart._period_locked)  # True

chart.set_period(None)     # 解锁
chart.set(df_15min)        # 自动推断为 15 分钟
print(chart._period_locked)  # False
```

**实现原理：**
- 锁定后，`_df_datetime_format()` 跳过 `_set_interval()`，`_interval` 保持不变
- 时间戳转换后执行：`time = interval * (time // interval)`，对齐到间隔边界
- **去重保护：** 对齐后按时间戳去重（保留每组最后一行），防止 JS `Value is null` 错误
  - 例如：10 根 30min K 线锁定到 1h → 对齐后得到 5 个唯一时间戳
  - 同级别数据（5min→5min）不受影响，不会去重
- `update()` / `update_from_tick()` 中的 `_single_datetime_format()` 使用锁定后的 `_interval` 对齐
- `marker()` 中的时间对齐也同样受锁定影响

### 3.4.4 标记 (Marker)

```python
chart.marker(text='标记文本', position='above', shape='arrow_up', color='...')
# 添加价格标记

chart.marker_auto_scale(enable=True)
# v5.0.9+ : 控制标记是否参与价格轴自动缩放

chart.remove_marker(marker_id)  # 按 ID 删除单个标记
chart.clear_markers()           # 删除所有标记
```

### 3.5 折线与柱状图

```python
line = chart.create_line(
    name='SMA 50', color='rgba(..., 0.6)',
    style='solid', width=2,
    price_line=True, price_label=True,
    price_scale_id=None, pane_index=0
)
line.set(df)           # df 列: time + name
line.update(series)    # 逐点实时更新，每次发送一条 JS 命令
line.update_batch(df)  # 批量追加数据点，所有 JS 命令合并为一次发送（性能优化）
line.delete()          # 删除 (JS + Python 双端清理)

hist = chart.create_histogram(
    name='volume', color='...',
    price_line=True, price_label=True,
    scale_margin_top=0.0, scale_margin_bottom=0.0,
    pane_index=0
)
hist.set(df)
hist.update(series)
hist.update_batch(df)                # 批量追加数据点（Histogram 同样支持）
hist.scale(top=0.0, bottom=0.0)     # 调整缩放边距
hist.delete()

chart.lines()  # 返回所有已创建的 Line 列表
```

### 3.6 样式配置

```python
# 全局布局
chart.layout(
    background_color='#000000', text_color='#FFFFFF',
    font_size=14, font_family='Arial'
)

# K线样式
chart.candle_style(
    up_color='rgba(39,157,130,100)', down_color='rgba(200,97,100,100)',
    wick_visible=True, border_visible=True,
    border_up_color='', border_down_color='',
    wick_up_color='', wick_down_color=''
)

# 成交量样式
chart.volume_config(
    scale_margin_top=0.8, scale_margin_bottom=0.0,
    up_color='rgba(83,141,131,0.8)', down_color='rgba(200,127,130,0.8)'
)

# 网格
chart.grid(
    vert_enabled=True, horz_enabled=True,
    color='rgba(29,30,38,5)', style='solid'
)

# 时间轴
chart.time_scale(
    right_offset=0, min_bar_spacing=0.5,
    visible=True, time_visible=True, seconds_visible=False,
    border_visible=True, border_color='rgba(..., 0.4)',
    right_offset_pixels=None,          # v5.0.9+ : 右侧像素偏移
    enable_conflation=None,            # v5.1.0+ : 大数据量自动合并
    conflation_threshold_factor=None,  # v5.1.0+ : 合并激活阈值
    precompute_conflation_on_init=None,# v5.1.0+ : 初始化时预计算
    precompute_conflation_priority=None# v5.1.0+ : 预计算优先级
)

# 价格轴
chart.price_scale(
    auto_scale=True, mode='normal', invert_scale=False,
    align_labels=True, scale_margin_top=0.2, scale_margin_bottom=0.2,
    border_visible=True, border_color=None, text_color=None,
    entire_text_only=False, visible=True, ticks_visible=False,
    tick_mark_density=None,            # v5.2.0+ : 刻度标签密度
    minimum_width=0, perm_width=0
)

# 十字光标
chart.crosshair(
    mode='normal',        # normal | magnet | hidden
    vert_color='#FFFFFF', vert_style='dotted', vert_width=1, vert_visible=True,
    horz_color='#FFFFFF', horz_style='dotted', horz_width=1, horz_visible=True,
    label_background_color='rgba(0,0,0,0.7)', label_text_color='#FFFFFF'
)

# 水印
chart.watermark(text='1D', color='rgba(180,180,240,0.7)', font_size=48)

# 截图（v5.2.0+ 增强）
img = chart.screenshot()                          # 默认行为（不含顶层和十字光标）
img = chart.screenshot(add_top_layer=True)       # 包含水印等顶层元素
img = chart.screenshot(include_crosshair=True)   # 包含十字光标
img = chart.screenshot(add_top_layer=True, include_crosshair=True)  # 两者都包含

# 价格格式 — 避免浮点精度问题（v5.2.0+）
chart.set_price_format(type='base', base=100, precision=2)
# 以 base 为基准值，所有价格显示为 (实际值 / base)，保留 precision 位小数
# 例如: 实际价格 100.00 → 显示 1.00

# 图例
chart.legend(visible=True, font_size=12, color='#FFFFFF',
             persistent=False,      # True: OHLC 常驻，鼠标移开不消失
             shorthand=True)        # True: V 24.5K; False: V 24500

# 自动适应视图
chart.fit()

# 设置可见时间范围
chart.set_visible_range(start_time, end_time)

# 缩放图表
chart.resize(width=0.8, height=0.6)  # 比例 0~1
```

### 3.7 子图表 (Multi-Pane)

```python
sub = chart.create_subchart(
    position='left',        # left | right
    width=0.5, height=0.5,  # 面板大小比例
    sync_id=None,           # 同步滚动/光标
    scale_candles_only=False,
    sync_crosshairs_only=False,
    toolbox=False
)
# sub 是 AbstractChart 实例，有完整的 API
line = sub.create_line(...)
sub.set(df)
```

### 3.8 事件回调 (Events)

```python
chart.events.search += on_search          # 用户搜索时触发
chart.events.range_change += on_range     # 时间范围变化
chart.events.click += on_click            # 鼠标点击
chart.events.crosshair_move += on_cross   # v5.2.0+ : 鼠标悬停移动
chart.events.horizontal_line_move += func # 水平线移动
# 另: new_bar (Candlestick.update 追加新 bar 时)
```

回调函数签名：

```python
def on_search(chart, searched_string): ...
def on_range(chart, start_time, end_time): ...
def on_click(chart, time, price): ...
def on_cross(chart, payload): ...          # payload: {time, price}
def on_horizontal_line_move(chart, line): ...
```

### 3.9 图表级高级选项 — chart_options() (v5.2.0+)

`chart_options()` 方法用于设置图表级别的行为，支持以下三个参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `hovered_series_on_top` | `bool` | `True` | 鼠标悬停时，被悬停的系列（K线或指标线）会立即移动到所有系列的最上层。`True` 时悬停的系列浮到顶端；`False` 时被悬停的系列保持在原有层级（不浮起）。 |
| `default_visible_price_scale_id` | `'left' \| 'right'` | `'right'` | 当左右价格轴都存在时，默认显示哪一个。 |
| `do_not_snap_to_hidden_series_indices` | `bool` | `False` | 十字光标是否忽略隐藏系列的索引（吸附行为）。 |

```python
chart.chart_options(
    hovered_series_on_top=True,                 # 悬停时该系列浮到顶层
    default_visible_price_scale_id='right',    # 默认显示右侧价格轴
    do_not_snap_to_hidden_series_indices=False # 十字光标仍吸附隐藏系列
)
```

**示例 18** (`examples/18_hovered_series_on_top/hovered_series_on_top.py`) 通过左右两个独立窗口对比展示了 `hovered_series_on_top` 的实际效果：
- **左侧窗口** (`hovered_series_on_top=False`)：鼠标悬停在黄色 SMA 线上时，线条**不会**浮到蜡烛上方，始终被蜡烛遮挡；悬停在蜡烛上时也不会发生 z-order 变化。
- **右侧窗口** (`hovered_series_on_top=True`)：鼠标悬停在黄色 SMA 线上时，线条**立即浮到最上层**，出现在蜡烛之上；悬停在蜡烛上时，蜡烛也会浮到线条之上。

### 3.10 TopBar

```python
# 文本框
chart.topbar.textbox('symbol', 'TSLA', align='left', func=on_search)

# 切换器
chart.topbar.switcher('timeframe', ('1min', '5min', '30min'), default='5min',
                      align='right', func=on_timeframe_selection)

# 菜单
chart.topbar.menu('menu1', ('opt1','opt2'), default='opt1',
                  align='right', separator=False, func=...)

# 按钮
chart.topbar.button('btn1', 'Click', align='left',
                    separator=False, toggle=False, func=...)

# 读取/设置值
chart.topbar['symbol'].value       # 当前值
chart.topbar['symbol'].set('AAPL') # 设置值

# 更新菜单项
chart.topbar['menu1'].update_items('opt3', 'opt4')
```

### 3.11 绘图工具 (ToolBox + Drawings)

```python
# 启用工具箱
chart = Chart(toolbox=True)

# 保存绘图关联 widget
chart.toolbox.save_drawings_under(chart.topbar['symbol'])

# 导入/导出绘图
chart.toolbox.import_drawings('drawings.json')
chart.toolbox.export_drawings('drawings.json')
chart.toolbox.load_drawings('tag_name')

# 绘制形状 (Python 端创建)
h_line = chart.horizontal_line(price=200, color='#1E80F0',
                                width=4, style='solid', text='',
                                axis_label_visible=True, func=on_move)
t_line = chart.trend_line(start_time, start_price, end_time, end_price,
                           round=True, color='#1E80F0', width=4, style='solid')
box = chart.box(start_time, start_price, end_time, end_price,
                round=True, color='#1E80F0', width=4, style='solid',
                filled=False, fill_color='rgba(30,128,240,0.2)')
v_line = chart.vertical_line(time, color='#1E80F0', width=4, style='solid')

# VerticalSpan — 高亮区域
v_span = chart.vertical_span(start_time, end_time,
                              color='rgba(30,128,240,0.2)')
# 单时间点/列表: 显示为细柱
# 起止时间: 连续区域填充

# PriceLine — 价格线
price_line = chart.create_price_line(price=100, color='#1E80F0',
                                      style='dashed', width=1,
                                      price_label=True, title='Pivot')
price_line.delete()   # 删除
price_line.update(price=105, color='#FF0000')  # 更新

# 通用操作
drawing.delete()                          # 删除
drawing.update(time1, price1, time2, price2)  # 更新点位 (TwoPointDrawing)
drawing.options(color='red', style='dashed', width=2)  # 更新样式
```

### 3.12 表格 (Table)

```python
table = chart.create_table(
    width=300, height=400,
    headings=('Symbol', 'Price', 'Change'),
    widths=(100, 100, 100),
    alignments=('left', 'right', 'right'),
    position='left',                        # left | right | top | bottom
    draggable=False,
    background_color='#121417',
    border_color='rgb(70,70,70)', border_width=1,
    heading_text_colors=..., heading_background_colors=...,
    return_clicked_cells=False,
    func=on_row_click
)

# 添加行
row = table.new_row({'Symbol': 'AAPL', 'Price': 150.0, 'Change': '+2.5%'})
row['Price'] = 151.0          # 更新单元格
row.background_color('Price', '#333')  # 设置背景色
row.text_color('Price', '#0f0')        # 设置文字色
row.delete()                          # 删除行

# 段落 (Section)
section = table.create_section('header')  # header | footer
section(3, func=...)     # 创建 3 个文本框
section[0] = 'Section Text'  # 设置文本
```

### 3.13 持仓量 (Open Interest)

`open_interest` 列可在成交量子图中叠加显示为折线，**其 Y 轴缩放与成交量完全解耦**。

```python
# 方式 1: 自动检测 (set() 中传入 open_interest 列)
df = pd.read_csv('data.csv')
# df 列: time, open, high, low, close, volume, open_interest
chart.set(df)  # 自动创建持仓量折线

# 方式 2: 实时更新
chart.update(series)  # series 中含 open_interest 时自动更新
```

**实现原理：**
- 成交量使用 `priceScaleId: 'volume_scale'`（HistogramSeries）
- 持仓量使用 `priceScaleId: 'oi_scale'`（LineSeries）
- 两者 `scaleMargins: {top: 0.8, bottom: 0}` 共享同一视觉区域
- 各自 `autoScale: true`，缩放互不影响
- OI series 在图表初始化时自动创建，**默认隐藏**；有数据时自动显示，无数据时自动隐藏

```python
from lightweight_charts import PolygonChart

chart = PolygonChart(
    api_key='YOUR_KEY', output='setting_data.png',
    width=1000, height=680
)
bars = chart.get_bar_data('AAPL', '5min', '2024-01-01', '2024-02-01')
chart.set(bars)
chart.show(block=True)

# 全局 API 函数 (polygon.py)
get_bar_data(ticker, timeframe, start_date, end_date, limit=5000)
async_get_bar_data(...)    # 异步版本
get_last_quote(ticker)
get_last_trade(ticker)
```

---

## 四、TypeScript 前端 (src/) 结构速览

| 模块 | 文件 | 说明 |
|------|------|------|
| **入口** | `src/index.ts` | 导出所有前端类 |
| **插件基类** | `src/plugin-base.ts` | `IPlugin` 接口定义 |
| **图表核心** | `src/general/handler.ts` | `Handler` 类 — 前端总控 |
| **图例** | `src/general/legend.ts` | 图例实现 |
| **顶栏** | `src/general/topbar.ts` | 顶栏 UI 组件 |
| **工具箱** | `src/general/toolbox.ts` | 绘图工具箱 UI |
| **菜单** | `src/general/menu.ts` | 右键/下拉菜单 |
| **表格** | `src/general/table.ts` | 数据表格渲染 |
| **全局参数** | `src/general/global-params.ts` | 全局参数 |
| **样式** | `src/general/styles.css` | 全局 CSS |
| **绘图引擎** | `src/drawing/drawing-tool.ts` | 绘图工具核心 |
| **绘图数据源** | `src/drawing/data-source.ts` | 绘图数据管理 |
| **绘图选项** | `src/drawing/options.ts` | 绘图样式选项 |
| **折线图** | `src/trend-line/` | 趋势线 |
| **水平线** | `src/horizontal-line/` | 水平线 + 射线 |
| **垂直线** | `src/vertical-line/` | 垂直线 |
| **矩形** | `src/box/` | 矩形框 |
| **示例** | `src/example/` | 前端示例页面 |
| **辅助工具** | `src/helpers/` | canvas 渲染维度、时间处理 |

---

## 五、示例速览 (examples/)

| # | 目录 | 说明 | 关键文件 |
|---|------|------|----------|
| 1 | `setting_data` | 基础: 从 CSV 读取并显示 K 线 | `setting_data.py` |
| 2 | `live_data` | 实时更新: 逐条更新 K 线 + 价格标记 | `live_data.py` |
| 3 | `tick_data` | Tick 数据: 从逐笔成交更新 K 线 | `tick_data.py` |
| 4 | `line_indicators` | 折线指标: SMA 叠加到 K 线图 | `line_indicators.py` |
| 5 | `styling` | 样式定制: 背景色/十字光标/水印/图例 | `styling.py` |
| 6 | `callbacks` | 事件回调: 搜索 + 时间切换 + 水平线移动 | `callbacks.py` |
| 7 | `multi_pane` | 多面板: K线 + 多个子面板叠加指标 | `multi_pane.py` |
| 8 | `volume_open_interest` | 成交量 + 持仓量叠加，独立缩放 | `volume_open_interest.py` |
| 9 | `multi_chart` | 多 Chart 实例同时运行 | `multi_chart.py` |
| 10 | `persistent_legend` | OHLC 常驻 + 简写开关示例 | `persistent_legend.py` |
| 11 | `vertical_span` | 区域高亮: 两日期区间 + 多点标记 | `vertical_span.py` |
| 12 | `audit` | 资源审计: 展示 Python/JS 侧审计用法 | `audit.py` |
| 13 | `batch_update` | 批量增量更新: `update_bars()` + `update_from_ticks()` | `batch_update.py` |
| 14 | `set_period` | 锁定时间级别: `set_period()` 演示 | `set_period.py` |
| 15 | `pyside6_simple` | PySide6 + QtChart 嵌入测试 | `pyside6_simple.py` |
| 16 | `pyside6_race` | PySide6 速度赛跑: update vs update_bars vs set 对比 | `pyside6_race.py` |
| 17 | `~~v520_new_features` | ~~v5.2.0 新功能集中示例~~ (已弃用，功能分散到 18-25 各独立示例) | ~~`v520_demo.py`~~ |
| 18 | `18_hovered_series_on_top` | `hovered_series_on_top` — 鼠标悬停时系列是否浮到顶层（左右对比） | `hovered_series_on_top.py` |
| 19 | `19_timescale_options` | `time_scale()` 新参数 — 像素偏移 / 数据合并 (conflation) | `timescale_options.py` |
| 20 | `20_tick_mark_density` | `tick_mark_density` — 价格轴标签密度控制 (1.0 / 2.5 / 6.0) | `tick_mark_density.py` |
| 21 | `21_marker_auto_scale` | `marker_auto_scale()` — 标记是否参与价格轴自动缩放 | `marker_auto_scale.py` |
| 22 | `22_pop` | `pop(n)` — 从末尾移除 N 根 K 线 | `pop.py` |
| 23 | `23_crosshair_move` | `events.crosshair_move` — 鼠标悬停实时回调 (Hit Testing) | `crosshair_move.py` |
| 24 | `24_price_format` | `set_price_format(type='base')` — 基础价格格式，避免浮点精度问题 (v5.2.0+) | `price_format.py` |
| 25 | `25_screenshot_enhanced` | `screenshot(add_top_layer=True, include_crosshair=True)` — 增强截图 (v5.2.0+) | `screenshot_enhanced.py` |
| 26 | `26_series_batch_update` | 系列批量更新：`update_batch()` 用于 Line 和 Histogram 系列 | `series_batch_update.py` |
| 27 | `27_reflex_chart` | Reflex 嵌入：K线 + SMA 指标在 Reflex 应用中渲染 | `rx_chart.py` |

---

## 六、测试 (test/)

```
test/
├── run_tests.py           # 简约运行器
├── test_cleanup.py        # 资源全链路创建/删除 + JS TOML 审计 + 多图表独立清理
└── test_features.py       # 独特功能测试: 数据重命名/line追踪/截图/topbar事件
```

运行:
```
python test/run_tests.py
python test/test_cleanup.py       # 资源清理测试 (需 GUI 环境)
python test/test_features.py      # 功能测试
```

---

## 七、依赖与构建

| 依赖 | 用途 |
|------|------|
| `pandas` | 数据处理 |
| `pywebview>=5.0.5` | 桌面 WebView 窗口 |
| `rollup` + TypeScript | 编译前端 src/ → js/ |

---

## 八、常用模式摘要

```
初始化 → 设置数据 → 可选: 添加指标/绘图/事件 → show(block=True)

实时数据:
  chart.set(initial_df)
  chart.show()
  for each update:
    chart.update(new_bar)        # K线更新
    或 chart.update_from_tick(tick)  # Tick更新

多面板:
  sub = chart.create_subchart(...)
  line = sub.create_line(...)
  sub.set(data)

事件驱动:
  chart.events.search += handler
  chart.topbar.switcher('tf', options, func=handler)
```

---

## 九、Reflex 集成 (ReflexChart)

### 9.1 快速开始

```python
from lightweight_charts import ReflexChart

# 模块级创建（仅执行一次）
chart = ReflexChart(width=1000, height=600, auto_flush=True)
chart.set(ohlcv_df)
chart.layout(background_color='#0c0d0f', text_color='#d8d9db')
chart.watermark('Reflex + LWC')

class ChartState(rx.State):
    def tick(self):
        bar = _next_bar()
        chart.update(bar)
        return chart.flush()   # → rx.call_script → postMessage → iframe eval

def index() -> rx.Component:
    return rx.vstack(
        rx.button('+1 Bar', on_click=ChartState.tick),
        chart.to_reflex(id='lwc-frame', width='100%'),
        rx.input(id='cb-buffer', on_change=ChartState.on_crosshair,
                 style={'opacity': 0, 'width': 0, 'height': 0}),
    )

app = rx.App()
app.add_page(index, on_load=ChartState.mount)
```

### 9.2 初始化幂等性 — 防重复创建

**问题：** Reflex 的编译进程和运行时进程分别导入模块。编译时 `to_reflex()` 清空 `_pending` 并生成 HTML；运行时进程的 `chart` 实例是 **新创建** 的，其 `_pending` 残留所有初始化脚本（`new Lib.Handler`、`setData`、`createLineSeries` 等）。若 `to_reflex()` 未被新实例调用，第一次 `flush()` 会把 init 脚本全部发送给 iframe，导致**重复创建图表和指标线**。

**根因位置：** `abstract.py:1207-1208`

```python
self._html_chart_init = f'window.{self.id} = new Lib.Handler("{self.id}", ...)'
self.run_script(self._html_chart_init + ';0')  # → 同时加入 _html 和 _pending
```

**解决（`reflex_chart.py:93-112`）：** 在 `run_script()` 中拦截 `new Lib.Handler` 的 init 脚本，自动包裹清理 IIFE：

```python
def run_script(self, script, run_last=False):
    short_id = self.id.replace('window.', '', 1)
    if script.startswith(f'window.{short_id} = ') and 'new Lib.Handler' in script:
        guard = (
            f';!function(){{'
            f'var h=window.{short_id};'
            f'if(h){{'
            f'Lib.Handler.removeHandlerFromAll({_json.dumps(self.id)});'
            f'try{{h.chart.remove()}}catch(e){{}}'
            f'try{{h.wrapper.remove()}}catch(e){{}}'
            f'delete window.{short_id};'
            f'}}'
            f'}}();'
        )
        script = guard + script
    super().run_script(script, run_last)
    if self._auto_flush:
        self._pending.append(script)
```

生成的 JS 效果：

```javascript
;!function(){
  var h=window.ReflexChart_1;
  if(h){
    Lib.Handler.removeHandlerFromAll("window.ReflexChart_1");
    try{h.chart.remove()}catch(e){}
    try{h.wrapper.remove()}catch(e){}
    delete window.ReflexChart_1;
  }
}();
window.ReflexChart_1 = new Lib.Handler("window.ReflexChart_1", 1.0, 1.0, "left", true, 0, true);
```

**原理：** 初始化前按名称搜索同名 Handler，存在则先销毁再重建，使 `new Lib.Handler` 调用幂等化。无论脚本来自 iframe HTML 还是 `flush()→postMessage`，都不会产生第二个图表示例。

### 9.3 双向通信架构

```
Python (State handler)                  iframe
┌─────────────────────┐          ┌──────────────────────┐
│ chart.update(bar)   │          │ Lib.Handler          │
│ chart.flush()       │ postMsg  │   chart (Lightweight)│
│   → rx.call_script ─┼────────► │   series             │
│                     │          │   wrapper (DOM)      │
│ cb-buffer input     │ callback │   legend / toolBox   │
│  on_change=handler ◄┼──────────│ callbackFunction(msg)│
└─────────────────────┘          └──────────────────────┘
```

- **下行（Python → JS）：** `flush()` → `rx.call_script(postMessage)` → iframe `eval()` 
- **上行（JS → Python）：** iframe `callbackFunction()` → `parent.postMessage` → Reflex 隐藏 input `on_change` → State handler

### 9.4 关键注意点

| 注意项 | 说明 |
|--------|------|
| `auto_flush=True` | 必须启用，否则 `run_script()` 不入 `_pending` 队列 |
| `_auto_flush` / `_pending` 在 `super().__init__()` 前设置 | `AbstractChart.__init__` 中会调用 `run_script()`，此时 `_pending` 必须已存在 |
| `to_reflex()` 清空 `_pending` | 初始化脚本已嵌入 iframe HTML，不需要再发送 |
| `win.loaded` 运行时为 False | Reflex 运行时进程重新导入模块，Window 是新实例，`loaded` 状态不共享 |
| `rx.script()` 不可用 | Reflex 0.9.2 用 Helmet 渲染 `<script>`，`innerHTML` 不执行内联脚本；改用 `rx.call_script` |
| Module `reload` | Reflex dev 模式的 hot-reload 会重新导入用户模块，每次创建新 `chart` 实例 |

### 9.5 相关文件

| 文件 | 职责 |
|------|------|
| `lightweight_charts/reflex_chart.py` | ReflexChart 类定义，`run_script`/`flush`/`to_reflex`/`_build_html` |
| `lightweight_charts/js/bundle.js` | 前端 `Lib.Handler` 类（`Handler._all`、`removeHandlerFromAll`、`chart.remove()`） |
| `lightweight_charts/abstract.py` | `AbstractChart.__init__` 中的 `_html_chart_init` 定义 |
| `examples/27_reflex_chart/rx_chart/rx_chart.py` | 完整示例：数据生成、State、mount、tick、crosshair 回调 |

---

## 十、清理与重置 API

### 10.1 清空 K 线数据

```python
chart.clear_data()
# 清空 OHLCV 数据，但保留 series 对象。可继续 chart.set(df)
```

### 10.2 重置图表到初始状态

```python
chart.reset()
# 执行后 chart 像刚创建时一样干净，WebView 不销毁
# 包括: 清空K线 + 删除附加系列 + 清空 markers + 清空 drawings + 清理 handlers
# TopBar widget 和样式配置保留
```

### 10.3 清理事件处理器

```python
chart.clear_handlers()
# 清空 Window 中累积的所有回调，防止嵌入场景下 handler 内存泄漏
```

### 10.4 核心清理方法

| 方法 | 行为 |
|------|------|
| `chart.clear_data()` | 清空 OHLCV 数据，保留 series 对象 |
| `chart.reset()` | 清空所有数据+标记+绘图+handlers，保留 TopBar 和样式 |
| `chart.clear_handlers()` | 清空所有事件处理器 |
| `line.delete()` / `histogram.delete()` | JS+Python 双端清理 |
| `drawing.delete()` / `span.delete()` | 从图表移除并清理 |

```python
# 典型场景: 切换股票/周期
chart.clear_data()           # 清空数据
chart.set(new_df)            # 重新设置
# 或
chart.reset()                # 一键清空
chart.set(new_df)            # 重新开始
```

### 10.5 资源审计

```python
# Python 侧审计 (零卡死风险, 返回 dict)
audit = chart.audit(use_js=False)
# 返回: {chart: {id, has_data, has_open_interest, ...},
#         lines: [{id, type, name, data_points}],
#         price_lines: [{id, type}],
#         drawings: [{id, type, price?}],
#         tables: [{id, type, headings}],
#         markers: [{id, time, text, shape, position}],
#         handlers_count: int}

# JS 侧审计 (TOML 格式, 返回解析后的 dict)
audit = chart.audit(use_js=True)
# 返回 TOML-parsed dict, 每个 window 全局变量独立成段:
# {
#   'Chart_1': {'id': 'Chart_1', 'type': 'Handler',
#               '_interval': 86400, 'scale': {'width': 1, 'height': 1},
#               'hasChart': True, 'hasSeries': True, 'hasOpenInterest': True,
#               'extraSeries': [{...}], 'candleDataPoints': 50,
#               'markersCount': 4, 'extraSeriesCount': 2},
#   'Line_3':  {'id': 'Line_3', 'type': 'object', 'color': '#ff0000'},
#   ...
# }
```

### 10.6 资源追踪与 Event Handler

Python 侧自动追踪资源，支持完整生命周期管理：

| 追踪列表 | 注册时机 | 注销时机 |
|----------|---------|---------|
| `chart._lines` | `create_line()` | `line.delete()` |
| `chart._drawings` | `Drawing.__init__()` | `drawing.delete()` |
| `chart._tables` | `chart.create_table()` | `table.delete()` |
| `chart.markers` | `chart.marker()` | `chart.remove_marker()` |
| `chart.win.handlers` | 自动注册 | `clear_handlers()` / `remove_handler()` |

```python
# Event Handler 管理
chart.events.search += handler       # 注册
chart.events.search -= handler       # 取消注册
chart.clear_handlers()               # 批量清理
```

### 10.7 窗口销毁保护

窗口关闭后，所有 `run_script` / `update` / `set` 抛出：`RuntimeError: Chart window has been destroyed. Cannot execute script.` 主进程检测死亡后自动排空队列、关闭并 join 线程，防止进程卡死。

### 10.8 Marker 漂移修复

**问题：** 调用 `chart.set(new_df)` 后，marker 位置可能偏移周围几根 K 线。

**根因：** `set()` 会通过 `_df_datetime_format` → `_set_interval` 重新计算 `_interval`。Markers 的时间戳需要按新 `_interval` 对齐后重新发送到 JS 端，但 `set()` 中没有调用 `_update_markers()`。

**修复：** 在 `AbstractChart.set()` 末尾和 `SeriesCommon.set()` 末尾，当 `self.markers` 非空时调用 `self._update_markers()`。

```python
# AbstractChart.set() 末尾（abstract.py）
if self.markers:
    self._update_markers()

# SeriesCommon.set() 末尾
if self.markers:
    self._update_markers()
```

这样 `set()` 后 markers 会以新的 `_interval` 重新对齐发送，不再漂移。

---

## 十一、多 Chart 实例

每个 `Chart()` 实例现在完全独立：

```python
chart1 = Chart(width=500, height=600, title='AAPL')
chart2 = Chart(width=500, height=600, title='TSLA')

chart1.set(df1)
chart2.set(df2)

# 用线程分别运行各自的 show_async
t1 = Thread(target=lambda: asyncio.run(chart1.show_async()), daemon=True)
t2 = Thread(target=lambda: asyncio.run(chart2.show_async()), daemon=True)
t1.start(); t2.start()
t1.join()
```

各自拥有独立的子进程、队列、回调 handlers，互不干扰。

---

## 十二、OHLC Legend 增强

### 11.1 OI 显示在 Legend

当 DataFrame 包含 `open_interest` 列时，Legend 自动显示：

```
O 109.30 | H 111.38 | L 107.58 | C 110.12 | V 24.5K | OI 112.3K
```

### 11.2 persistent — 常驻模式

```python
chart.legend(visible=True, persistent=True)
# OHLC 鼠标移开也不消失
chart.legend(visible=True, persistent=False)
# 默认行为，鼠标离开图表后隐藏 OHLC
```

### 11.3 shorthand — 简写开关

```python
chart.legend(visible=True, shorthand=True)
# V 24.5K | OI 112.3K  （≥1000 → K，≥1,000,000 → M）
chart.legend(visible=True, shorthand=False)
# V 24500 | OI 112345   （完整数字）
```

---

## 十三、十字浮标时间格式

自定义 UTC 格式，日/周级别隐藏时分：

| 数据级别 | 显示格式 |
|----------|----------|
| 日线/周线 | `2025-03-01` |
| 分钟线   | `2025-03-01 09:30` |

---

## 十四、update / update_from_tick 内部流程简要说明

本节仅保留关键机制，原详细调用链分析已移除。

### 13.1 核心差异

| 维度 | `update(series)` | `update_from_tick(series)` |
|------|-----------------|---------------------------|
| **输入** | OHLCV 完整 K 线 | 单条 Tick `{time, price, volume?}` |
| **聚合逻辑** | ❌ 无 — 直接作为 K 线 | ✅ 有 — 聚合为 OHLC |
| **触发 new_bar** | ✅ 时间变化时 | ✅ 时间变化时（通过 update 内部） |
| **典型场景** | 批量更新 / 实时 K 线推送 | 逐 Tick 实时聚合 K 线 |

### 13.2 `_interval` 时间对齐机制

所有时间戳对齐到 `_interval` 秒的整数倍：
```python
# abstract.py:250
arg = self._interval * (arg.timestamp() // self._interval) + self.offset
```

| 操作 | `_interval` 重算 |
|------|-----------------|
| `set(df)` (未锁定) | ✅ 从数据 diff 推断 |
| `set(df)` (已锁定) | ❌ 用 `set_period()` 值 |
| `update()` / `update_from_tick()` | ❌ 不变 |

⚠️ **精度不匹配陷阱**: 15min 图表传入 5min K 线 → 时间对齐后覆盖，3 根变 1 根。先用 `chart.set()` 切换周期再 `update()`。
