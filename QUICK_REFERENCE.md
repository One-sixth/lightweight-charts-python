# lightweight-charts-python 快查文档

> Python 封装 TradingView Lightweight Charts 的框架 v2.2  
> 作者: louisnw | GitHub: [louisnw01/lightweight-charts-python](https://github.com/louisnw01/lightweight-charts-python)  
> PyPI: `pip install lightweight-charts` | 需 Python ≥3.8 + pandas + pywebview

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
├── examples/                   # 7 个完整示例 (见下文)
├── test/                       # 单元测试 (unittest)
│   ├── run_tests.py            # 测试入口
│   ├── test_chart.py           # 图表核心测试
│   ├── test_returns.py         # 截图/保存绘图测试
│   ├── test_table.py           # 表格测试
│   ├── test_toolbox.py         # 绘图工具测试
│   ├── test_topbar.py          # 顶栏组件测试
│   └── util.py                 # 测试工具 (Tester 基类, BARS 数据)
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

### 3.4 数据方法 (Candlestick)

```python
chart.set(df, keep_drawings=False)
# 设置初始数据。df 列: time/open/high/low/close + 可选 volume
# 支持大小写不敏感列名 (自动 rename)

chart.update(series)
# 更新最后一根 K 线 (time 相同时覆盖，不同时追加)
# series: pd.Series, 列同 set()

chart.update_from_tick(series, cumulative_volume=False)
# 从 tick 更新 K 线。series 列: time/price + 可选 volume
# 自动计算 high/low/close

chart.marker(text='标记文本', position='above', shape='arrow_up', color='...')
# 添加价格标记

chart.remove_marker(marker_id)  # 按 ID 删除单个标记
chart.clear_markers()           # 删除所有标记
```

### 3.4.1 `set()` vs `reset()` 对比 [2026-05-04]

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

### 3.4.2 批量增量更新 — update_bars() / update_from_ticks() [2026-05-06 新增]

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

### 3.4.3 锁定时间级别 — set_period() [2026-05-06 新增]

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

### 3.5 折线与柱状图

```python
line = chart.create_line(
    name='SMA 50', color='rgba(..., 0.6)',
    style='solid', width=2,
    price_line=True, price_label=True,
    price_scale_id=None, pane_index=0
)
line.set(df)        # df 列: time + name
line.update(series) # 实时更新
line.delete()       # 删除 (JS + Python 双端清理)

hist = chart.create_histogram(
    name='volume', color='...',
    price_line=True, price_label=True,
    scale_margin_top=0.0, scale_margin_bottom=0.0,
    pane_index=0
)
hist.set(df)
hist.update(series)
hist.scale(top=0.0, bottom=0.0)  # 调整缩放边距
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
    border_visible=True, border_color='rgba(..., 0.4)'
)

# 价格轴
chart.price_scale(
    auto_scale=True, mode='normal', invert_scale=False,
    align_labels=True, scale_margin_top=0.2, scale_margin_bottom=0.2,
    border_visible=True, border_color=None, text_color=None,
    entire_text_only=False, visible=True, ticks_visible=False,
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
chart.events.horizontal_line_move += func # 水平线移动
# 另: new_bar (Candlestick.update 追加新 bar 时)
```

回调函数签名：

```python
def on_search(chart, searched_string): ...
def on_range(chart, start_time, end_time): ...
def on_horizontal_line_move(chart, line): ...
```

### 3.9 TopBar

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

### 3.10 绘图工具 (ToolBox + Drawings)

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

# VerticalSpan — 高亮区域 (v2.1 修复: 改用 AreaSeries/HistogramSeries)
v_span = chart.vertical_span(start_time, end_time,
                              color='rgba(30,128,240,0.2)')
# 单时间点/列表: 显示为细柱
# 起止时间: 连续区域填充

# PriceLine — 价格线 (v2.1 新增)
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

### 3.11 表格 (Table)

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

### 3.12 持仓量 (Open Interest) — 新增

`open_interest` 列可在成交量子图中叠加显示为折线，**其 Y 轴缩放与成交量完全解耦**。

```python
# 方式 1: 自动检测 (set() 中传入 open_interest 列)
df = pd.read_csv('data.csv')
# df 列: time, open, high, low, close, volume, open_interest
chart.set(df)  # 自动创建持仓量折线

# 方式 2: 独立设置
chart.set(ohlcv_df)
chart.set_open_interest(oi_df)  # oi_df 列: time, open_interest

# 方式 3: 实时更新
chart.update(series)  # series 中含 open_interest 时自动更新

# 方式 4: 手动更新持仓量
chart.update_open_interest(series)
```

**实现原理：**
- 成交量使用 `priceScaleId: 'volume_scale'`（HistogramSeries）
- 持仓量使用 `priceScaleId: 'oi_scale'`（LineSeries）
- 两者 `scaleMargins: {top: 0.8, bottom: 0}` 共享同一视觉区域
- 各自 `autoScale: true`，缩放互不影响

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

## 九、新增: 清理与重置 API (v2.2 定制版)

### 9.1 清空 K 线数据

```python
chart.clear_data()
# 清空 OHLCV 数据，但保留 series 对象。可继续 chart.set(df)
```

### 9.2 重置图表到初始状态

```python
chart.reset()
# 执行后 chart 像刚创建时一样干净，WebView 不销毁
# 包括: 清空K线 + 删除附加系列 + 清空 markers + 清空 drawings + 清理 handlers
# TopBar widget 和样式配置保留
```

### 9.3 清理事件处理器

```python
chart.clear_handlers()
# 清空 Window 中累积的所有回调，防止嵌入场景下 handler 内存泄漏
```

### 9.4 Series 删除 (已修复)

每个系列在 JS 和 Python 双端都正确清理：

| 系列类型 | JS `delete` | Python `removeSeries` | Python 列表清理 |
|----------|-------------|----------------------|-----------------|
| `line.delete()` | ✅ `delete {self.id}` | ✅ `removeSeries()` | ✅ 从 `_lines` 移除 |
| `histogram.delete()` | ✅ `delete {self.id}` | ✅ `removeSeries()` | ✅ 从 `_lines` 移除 |
| `chart.clear_data()` | ✅ `setData([])` | ✅ 保留 series | ✅ `candle_data` 清空 |
| `drawing.delete()` | ✅ 新增 `delete {self.id}` | ✅ `.detach()` | N/A |
| `vertical_span.delete()` | ✅ 新增 `delete {self.id}` | ✅ `removeSeries()` | N/A |

### 9.5 精细控制流程

```python
# 典型场景: 切换股票/时间周期
chart.clear_data()           # 先清空老数据
chart.set(new_df)            # 再塞新数据

# 典型场景: 清除所有指标重新画
chart.reset()                # 一键回归初始
chart.set(new_df)            # 重新开始
line = chart.create_line(...)
line.set(sma_data)

# 典型场景: 嵌入长期运行防泄漏
# 每次切换时调用 reset() 避免 handler 和 series 堆积
```

### 9.7 资源审计 (v2.2 TOML 格式)

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

### 9.8 资源追踪列表

Python 侧自动追踪所有可创建资源：

| 追踪列表 | 注册时机 | 注销时机 |
|----------|---------|---------|
| `chart._lines` | `create_line()` / `create_histogram()` | `line.delete()` / `histogram.delete()` |
| `chart._price_lines` | `PriceLine.__init__()` | `price_line.delete()` |
| `chart._drawings` | `Drawing.__init__()` / `VerticalSpan.__init__()` | `drawing.delete()` / `span.delete()` |
| `chart._tables` | `chart.create_table()` | `table.delete()` |
| `chart.markers` (dict) | `chart.marker()` / `chart.marker_list()` | `chart.remove_marker()` / `chart.clear_markers()` |
| `chart.subcharts` (list) | `create_subchart()` | `remove_subchart()` |
| `chart.win.handlers` (dict) | 自动注册 | `clear_handlers()` / `remove_handler()` |

### 9.5 Event Handler 逐个清理

```python
# Emitter (Python 端事件)
chart.events.new_bar += my_handler
chart.events.new_bar -= my_handler   # 新增: 取消注册

# JSEmitter (JS 端事件)
chart.events.search += my_handler
chart.events.search -= my_handler    # 新增: 从 Window.handlers 移除

# Window handler
chart.win.handlers['test'] = lambda: None
chart.win.remove_handler('test')     # 新增: 按 ID 移除

# 批量清理
chart.clear_handlers()   # 清空所有 handlers
```

### 9.6 窗口销毁保护

窗口关闭后，所有 `run_script` / `update` / `set` 等操作会抛出：

```
RuntimeError: Chart window has been destroyed. Cannot execute script.
```

清理逻辑：
- 主进程检测到子进程死亡 → 排空队列 → `close()` + `join_thread()` → 抛异常
- 不会产生 `ObjectDisposedException` 或进程卡死

### 9.9 Marker 漂移修复 [2026-05-06]

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

## 十、多 Chart 实例 (v2.2 定制版)

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

## 十一、OHLC Legend 增强 (v2.2 定制版)

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

## 十二、十字浮标时间格式

自定义 UTC 格式，日/周级别隐藏时分：

| 数据级别 | 显示格式 |
|----------|----------|
| 日线/周线 | `2025-03-01` |
| 分钟线   | `2025-03-01 09:30` |

---

## 十三、update / update_from_tick 内部流程深度分析 [2026-05-04]

### 13.1 Candlestick.update(series) 完整调用链

```
用户调用: chart.update(series)   # series 是 pd.Series

┌─────────────────────────────────────────────────────────┐
│ 1. Candlestick.update(series, _from_tick=False)         │
│    ── abstract.py:790                                    │
│                                                          │
│  series = self._series_datetime_format(series)          │
│  (if _from_tick=True, 跳过此步)                          │
│                                                          │
│  if series['time'] != self._last_bar['time']:            │
│      → 把旧的最后一条写入 self.candle_data DataFrame       │
│      → pd.concat 追加新数据                               │
│      → 触发 self._chart.events.new_bar._emit(self)       │
│                                                          │
│  self._last_bar = series                                 │
│  self.run_script(f'{self.id}.series.update({js_data})') │
│  → 发送 JS 命令: candlestickSeries.update({time,open,...})│
│                                                          │
│  if 'volume' in series:                                  │
│      → 构造 volume series (time + value + color)         │
│      → volumeSeries.update(...)                          │
│                                                          │
│  if 'open_interest' in series:                           │
│      → _update_open_interest(series)                     │
│      → openInterestSeries.update(...)                    │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│ 2. _series_datetime_format(series)                      │
│    ── abstract.py:232                                    │
│                                                          │
│  series = series.copy()                                  │
│  series.index = self._format_labels(series, ...)        │
│    → 列名转小写 (如果不含 date/time)                      │
│    → 'date' → 'time'                                    │
│  series['time'] = self._single_datetime_format(...)     │
│    → 转 datetime → Unix 秒时间戳                         │
│    → 对齐到时间间隔: interval * (ts // interval) + offset│
│  return series                                          │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│ 3. js_data(series)                                      │
│    ── util.py:91                                         │
│                                                          │
│  d = series.to_dict()                                    │
│  filtered = {k:v for k,v in d.items()}                  │
│  → 去掉 None/NaN 值                                      │
│  return json.dumps(filtered)                             │
│  → 输出: '{"time":1700000000,"open":100,...}'            │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│ 4. run_script(...)                                      │
│    ── Window.run_script (abstract.py)                   │
│                                                          │
│  → 通过 pywebview 的 js_api 调用                         │
│  → 执行 JS: candlestickSeries.update({time,open,...})   │
│  → TradingView Lightweight Charts 内部更新最后一根K线     │
└─────────────────────────────────────────────────────────┘
```

### 13.2 update_from_tick(series) 完整调用链

```
用户调用: chart.update_from_tick(tick)  # tick 是 pd.Series {time, price, volume?}

┌─────────────────────────────────────────────────────────┐
│ 1. update_from_tick(series, cumulative_volume=False)    │
│    ── abstract.py:813                                    │
│                                                          │
│  series = self._series_datetime_format(series)          │
│  → time 转为 Unix 秒时间戳                                │
│                                                          │
│  if series['time'] < self._last_bar['time']:             │
│      → raise ValueError (tick 时间不能早于最后一根K线)     │
│                                                          │
│  bar = pd.Series(dtype='float64')                        │
│                                                          │
│  if series['time'] == self._last_bar['time']:            │
│      → 同一根K线内更新:                                    │
│         bar['high'] = max(last_bar.high, tick.price)     │
│         bar['low']  = min(last_bar.low,  tick.price)     │
│         bar['close']= tick.price                         │
│         bar['volume'] = cumulative ? last+new : new      │
│  else:                                                   │
│      → 新K线:                                            │
│         bar['open'] = bar['high'] = bar['low']          │
│         bar['close']= tick.price                         │
│         bar['volume'] = tick.volume                      │
│                                                          │
│  self.update(bar, _from_tick=True)                      │
│  → 进入 update() 流程（跳过 _series_datetime_format）     │
└─────────────────────────────────────────────────────────┘
```

### 13.3 核心差异对比

| 维度 | `update(series)` | `update_from_tick(series)` |
|------|-----------------|---------------------------|
| **输入** | OHLCV 完整 K 线 `{time, open, high, low, close, volume}` | 单条 Tick `{time, price, volume?}` |
| **时间格式化** | ✅ 执行 `_series_datetime_format` | ✅ 执行 `_series_datetime_format` |
| **Tick 聚合逻辑** | ❌ 无 — 直接作为 K 线 | ✅ 有 — 聚合为 OHLC |
| **同时间处理** | 覆盖最后一根 K 线 | 更新 high/low/close，可能追加 volume |
| **新时间处理** | 追加为新 K 线 | 创建新 K 线（open=price） |
| **触发 new_bar** | ✅ 时间变化时 | ✅ 时间变化时（通过 update 内部） |
| **典型场景** | 批量更新 / 实时 K 线推送 | 逐 Tick 实时聚合 K 线 |

### 13.4 `_interval` 时间对齐机制（重要！）

**`_interval` 的作用：** 所有时间戳都会对齐到 `_interval` 秒的整数倍。

```python
# _single_datetime_format 核心公式 (abstract.py:250)
arg = self._interval * (arg.timestamp() // self._interval) + self.offset
# 例如: _interval=900 (15min), ts=10:05 → 对齐到 10:00
```

**`_interval` 的确定时机：**

| 操作 | `_interval` 是否重算 | 来源 |
|------|---------------------|------|
| `set(df)` (未锁定) | ✅ 是 | 从 `df['time'].diff().value_counts()` 推断最常见间隔 |
| `set(df)` (已锁定) | ❌ 否 | 使用 `set_period()` 设定的值 |
| `set_period(seconds)` | ✅ 设为指定值 | 手动锁定 |
| `set_period(None)` | ❌ 保持 | 解锁，下次 `set()` 会重算 |
| `update(series)` | ❌ 否 | 使用已有的 `_interval` |
| `update_from_tick(tick)` | ❌ 否 | 使用已有的 `_interval` |
| `set(None)` 清空 | ❌ 不变 | 下次 `set()` 会重算 |

**`_set_interval` 逻辑 (abstract.py:180-204)：**
```python
# 1. 从数据 diff 推断间隔秒数
self._interval = common_interval.index[0].total_seconds()

# 2. 计算 offset (微秒/秒/分/时的偏移量)
# 用于处理非整点起始的数据 (如 9:15 开盘)
```

### 13.5 ⚠️ 精度不匹配陷阱

**场景：15 分钟图表 + 传入 5 分钟 K 线**

```
初始: chart.set(df_15min) → _interval = 900 (15min)

update(10:05 5min K线):
  → time 对齐: 900 * (10:05_ts // 900) = 10:00
  → 10:00 == _last_bar.time → 覆盖最后一根 K 线

update(10:10 5min K线):
  → time 对齐: 10:00
  → 又覆盖！

update(10:15 5min K线):
  → time 对齐: 10:15
  → 新 K 线 → 触发 new_bar 事件
```

**结果：3 根 5 分钟 K 线 → 只有最后 1 根生效（显示为 10:00 的 K 线）**

**正确做法：**
| 场景 | 正确方式 |
|------|---------|
| 15min 图表 | 先聚合为 15min K 线再 `update()` |
| 实时 Tick → K 线 | 用 `update_from_tick()`，它逐 Tick 聚合 |
| 切换时间周期 | 用 `chart.set(new_df)` 重新设置，`_interval` 会重新计算 |

### 13.6 类继承中的 `_interval` 传递

```
Chart
  └─ Candlestick (self._interval 在 set() 时确定)
  └─ Line 1 (self._interval = chart._interval，从 chart 复制)
  └─ Line 2 (同上)
  └─ Histogram (同上)
```

`SeriesCommon.__init__` (abstract.py:155-166)：
```python
if hasattr(chart, '_interval'):
    self._interval = chart._interval   # ← 从 chart 复制
else:
    self._interval = 1                  # ← 默认 1 秒
```

**注意：** 每个 Series 有自己的 `_interval` 副本，`set()` 时 Candlestick 的 `_interval` 被更新，但已创建的 Line/Histogram 不会自动同步（不过它们用 `format_cols=False`，不走 `_df_datetime_format`，所以不受影响）。
