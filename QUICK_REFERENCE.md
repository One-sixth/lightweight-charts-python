# lightweight-charts-python 快查文档


---

## 一、项目架构

```
lightweight-charts-python/
├── lightweight_charts/         ← Python 后端 (核心包)
│   ├── __init__.py             # 导出 AbstractChart, Chart, CrossProcessChart, JupyterChart,
│   │                           #        HTMLChart, HtmlTabChart, PolygonChart, ReflexChart,
│   │                           #        CandleSeries, VolumeSeries, OpenInterestSeries
│   ├── abstract.py             # 核心类: Window, AbstractChart
│   ├── series.py               # SeriesCommon, CandleSeries, VolumeSeries, OpenInterestSeries,
│   │                           #         Line, Histogram
│   ├── chart.py                # Chart (pywebview 桌面窗口实现) + CrossProcessChart (跨进程嵌入 Qt)
│   ├── widgets.py              # JupyterChart, HTMLChart, HtmlTabChart, QtChart, WxChart, StreamlitChart
│   ├── reflex_chart.py         # ReflexChart (Reflex 框架嵌入，iframe + postMessage 通信)
│   ├── toolbox.py              # ToolBox (绘图的保存/加载/导入/导出)
│   ├── topbar.py               # TopBar + Widget/Switcher/Menu/Button/TextWidget
│   ├── table.py                # Table + Row + Section
│   ├── drawings.py             # Drawing 基类 + HorizontalLine, TrendLine, Box, VerticalLine, RayLine, VerticalSpan
│   ├── polygon.py              # Polygon.io API 集成
│   ├── util.py                 # Pane, Events, Emitter, IDGen, BulkRunScript, 类型别名, 工具函数
│   └── js/                     # 构建后前端 (bundle.js, index.html, index_tab.html, styles.css)
├── src/                        ← TypeScript 前端 (由 rollup 构建到 js/)
│   ├── index.ts                # 入口
│   ├── plugin-base.ts          # 插件基类
│   ├── general/                # 通用 UI: handler, legend, menu, toolbox, topbar, table, global-params, styles.css
│   ├── drawing/                # 绘图引擎: data-source, drawing-tool, drawing, two-point-drawing, pane-renderer/view, options
│   ├── context-menu/           # 上下文菜单: context-menu, color-picker, style-picker
│   ├── trend-line/             # 趋势线
│   ├── horizontal-line/        # 水平线 + 射线
│   ├── vertical-line/          # 垂直线
│   ├── box/                    # 矩形框
│   └── helpers/                # canvas 渲染辅助, 时间处理, assertions, dimensions/
├── examples/                   # 35 个完整示例 (见下文)
├── test/                       # 单元测试 (8 个测试文件 + 2 个运行入口)
│   ├── run_tests.py            # 测试入口 (原始)
│   ├── run_new_tests.py        # 测试入口 (新增)
│   ├── test_cleanup.py         # 资源全链路创建/删除 + JS TOML 审计 + 多图表独立清理
│   ├── test_features.py        # 功能测试: 数据重命名/line追踪/截图/topbar事件
│   ├── test_candle_series.py   # CandleSeries 独立系列测试
│   ├── test_data_aggregation.py# 数据聚合/清洗测试
│   ├── test_position.py        # position 参数解析测试: 字符串转换/整数格式/元组格式/网格冲突检测
│   ├── test_reset_sub.py       # reset_sub 子图重置测试
│   ├── test_sync_debug.py      # 同步组调试测试
│   └── test_util.py            # 工具函数单元测试
├── docs/                       # Sphinx 文档源
│   ├── source/                 # 文档源文件 (reference/, examples/, tutorials/)
│   └── archive/                # 归档文档
└── js/                         # 构建后前端 (bundle.js + lightweight-charts.js) — 由 rollup 生成
```

---

## 二、Python 类层次

```
Pane (util.py)                          ← 所有组件的基类 (拥有 id, run_script)
├── Window (abstract.py)                ← JS 通信层: run_script(), run_script_and_get(), handlers
│
├── SeriesCommon (series.py)            ← 数据系列基类 (set/update/pop/clear_data/marker/marker_list/remove_marker/clear_markers)
│   ├── CandleSeries (series.py)        ← 独立K线系列 (无 volume, 可在任意 pane)
│   ├── VolumeSeries (series.py)        ← 成交量柱状图 (自动涨跌着色, self-managing)
│   ├── OpenInterestSeries (series.py)  ← 持仓量折线 (self-managing)
│   ├── Line (series.py)                ← 折线 (支持 marker)
│   └── Histogram (series.py)           ← 柱状图 (支持 marker)
│
├── AbstractChart (abstract.py)         ← 图表主类 (继承 Pane, 组合模式)
│   │   内部组件:
│   │     self.candle  → CandleSeries   ← 主 K 线 (始终存在, reset 后自动重建)
│   │     self.volume  → VolumeSeries   ← 独立成交量 (始终存在, reset 后自动重建)
│   │     self.oi      → OpenInterestSeries ← 独立持仓量 (始终存在, reset 后自动重建)
│   │   持有:
│   │     self._lines  → list[LineSeries|HistogramSeries]  ← 所有附加系列
│   │     self._drawing_series → dict[int, DrawingSeries]  ← 按 pane 管理绘图 (兼容: self.drawings 属性)
│   │     self._tables / self._price_lines ← 各类资源
│   │     self.topbar / self.toolbox    ← 顶栏和工具箱
│   │
│   ├── Chart (chart.py)                ← pywebview 桌面窗口
│   ├── CrossProcessChart (chart.py)    ← 跨进程嵌入 Qt (Windows + Linux/X11)
│   ├── HtmlTabChart (widgets.py)       ← 多策略 Tab 切换
│   ├── HTMLChart (widgets.py)          ← 静态 HTML 导出
│   ├── JupyterChart (widgets.py)       ← Jupyter Notebook
│   ├── QtChart (widgets.py)            ← PyQt5/6/PySide6 嵌入
│   ├── WxChart (widgets.py)            ← wxPython 嵌入
│   ├── StreamlitChart (widgets.py)     ← Streamlit 嵌入
│   └── ReflexChart (reflex_chart.py)   ← Reflex 框架嵌入 (iframe + postMessage)
│
├── PriceLine (drawings.py)             ← 价格线 (create_price_line 返回, 支持 update/delete)
├── DrawingSeries (drawing_series.py)   ← 每 pane 独立的绘图管理 (惰性创建不可见 JS LineSeries)
├── Drawing (drawings.py)               ← 绘图基类 (持有 drawing_series, detach + delete)
│   ├── TwoPointDrawing                 ← 两点绘图基类
│   ├── HorizontalLine / TrendLine / Box / VerticalLine / RayLine / VerticalSpan
├── TopBar + Widget 系列 (topbar.py)
│   ├── TextWidget / SwitcherWidget / MenuWidget / ButtonWidget
├── Table / Row / Section (table.py)
└── ToolBox (toolbox.py)
```

**设计模式说明：**
- **组合 > 继承**：`AbstractChart` 不再继承 `Candlestick`，而是通过 `self.candle` 组合持有。
  所有 Candlestick 方法（`set()`, `update()`, `marker()` 等）通过委托保持向后兼容。
- **self-managing 系列**：`VolumeSeries` / `OpenInterestSeries` / `CandleSeries` 各自维护
  `self.data` + `self._last_bar`，支持独立的 `set()` / `update()` / `update_bars()` / `delete()`。
- **marker 泛化**：`SeriesCommon` 上的 marker API 对所有系列类型均有效（Candlestick, Line, Histogram, CandleSeries 等）。

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
    position=111,                   # 图表位置 (网格格式)
    on_top=False, maximize=False,   # 窗口行为
    debug=False                     # 调试模式
)
```

**position 参数支持三种格式（类似 matplotlib 的 subplot）：**

| 格式 | 示例 | 说明 |
|------|------|------|
| 整数 | `111`, `221`, `311` | 3位数字：百位=行数、十位=列数、个位=位置索引 |
| 元组 | `(2, 2, 1)` | (行数, 列数, 位置索引)，推荐使用 |
| 字符串（已弃用） | `'left'`, `'right'` | 仅支持 1-2 个图表 |

**网格布局示例：**
```
2行2列布局 (221-224):
┌──────────┬──────────┐
│   221    │   222    │
├──────────┼──────────┤
│   223    │   224    │
└──────────┴──────────┘

3行1列布局 (311-313):
┌────────────────────────┐
│         311           │
├────────────────────────┤
│         312           │
├────────────────────────┤
│         313           │
└────────────────────────┘
```

- `111` = 1行1列，第1个位置（占满窗口）
- `121` = 1行2列，第1个位置（左半部分）
- `122` = 1行2列，第2个位置（右半部分）
- `221` = 2行2列，第1个位置（左上角）
- `311` = 3行1列，第1个位置（顶部三分之一）

**图表同步功能：**

通过 `sync_id` 组名实现多图表同步。同名组内的所有图表自动同步十字光标和/或时间范围：

```python
# 主图表加入同步组
chart = Chart(width=1200, height=800, position=(2, 2, 1), sync_id='main')
chart.set(df_main)

# 子图加入同一组 → 自动与主图同步
sub_right = chart.create_subchart(position=(2, 2, 2), sync_id='main')
sub_right.set(df_right)

# 另一个子图也加入同一组 → 三个图表互相同步
sub_bottom = chart.create_subchart(position=(2, 2, 3), sync_id='main', sync_crosshairs_only=True)
sub_bottom.set(df_bottom)

# 不同组名 → 独立同步
sub_independent = chart.create_subchart(position=(2, 2, 4), sync_id='group2')
sub_independent.set(df_ind)
```

**同步选项：**

| 参数 | 适用位置 | 说明 |
|------|---------|------|
| `Chart(sync_id=...)` | 主图表 | 主图表加入指定同步组 |
| `create_subchart(sync_id=...)` | 子图 | 子图加入指定同步组 |
| `create_subchart(sync_crosshairs_only=True)` | 子图 | 仅同步十字光标，不同步时间范围 |
| `join_sync_group(name, crosshair_only)` | 任意图表 | 运行时动态加入同步组 |

**组同步规则：**
- 同组内所有图表互相同步十字光标
- 时间范围同步仅在 `sync_crosshairs_only=False` 的图表之间生效
- 不同组名互不干扰
- `reset_sub()` 后同步自动恢复（组名保留在 `_syncGroup` 属性中）

**`join_sync_group()` — 运行时动态加入同步组：**

与 `Chart(sync_id=...)` 和 `create_subchart(sync_id=...)` 的区别：
- `sync_id` 参数在**创建时**指定，不可更改
- `join_sync_group()` 在**运行时**动态加入，可随时切换组

```python
chart1 = Chart(width=800, height=600)
chart2 = Chart(width=800, height=600)
chart3 = Chart(width=800, height=600)

# 运行时将 chart2 加入 chart1 的同步组
chart2.join_sync_group('group_a')

# 仅同步十字光标，不同步时间范围
chart3.join_sync_group('group_a', sync_crosshairs_only=True)

# 对已加入组的图表再次调用会更新同步模式
chart3.join_sync_group('group_a', sync_crosshairs_only=False)

# 也适用于子图
sub = chart1.create_subchart(position=122)
sub.join_sync_group('group_b')  # 子图加入不同组
```

### 3.2 HTMLChart (浏览器)

```python
from lightweight_charts import HTMLChart

chart = HTMLChart(
    width=1200, height=800,
    inner_height=-500,              # 子面板高度偏移
    toolbox=False,
    position=111,                   # 图表位置 (网格格式)
    pane_index=0,                   # 面板索引
    marker_auto_scale=True          # 标记是否自动缩放
)
# ... 设置数据 ...
chart.export('charts.html')         # 导出 HTML 文件
# 然后用 webbrowser.open('charts.html') 打开
```

### 3.3 HtmlTabChart (多策略 Tab 切换)

支持多策略切换、交易明细、绩效指标展示。改自 [smalinin/bn_lightweight-charts-python](https://github.com/smalinin/bn_lightweight-charts-python) 的 HtmlChart_BN。

```python
from lightweight_charts import HtmlTabChart

chart = HtmlTabChart(
    width=1200, height=800,
    position=111,                   # 图表位置 (网格格式)
    pane_index=0,                   # 面板索引
    marker_auto_scale=True          # 标记是否自动缩放
)

# 策略1
chart.set_name('均线交叉策略')
chart.set(df1)
chart.set_trades(trades1)
chart.set_performance_metrics(perf1, '均线交叉策略')
chart.set_parameters_list(params1)
chart.new_window()  # 切换到下一个策略

# 策略2
chart.set_name('布林带策略')
chart.set(df2)
chart.set_trades(trades2)
chart.set_performance_metrics(perf2, '布林带策略')
chart.set_parameters_list(params2)

chart.export('multi_charts.html')   # 导出 HTML 文件
```

#### HtmlTabChart iframe 嵌入

HtmlTabChart 生成的 HTML 文件可以通过 `<iframe>` 嵌入到其他网页中。
采用**双文件方案**：外壳 HTML + 图表内容 HTML，通过 `<iframe src="...">` 引用。

> **为什么不能用单文件方案？**
> 曾尝试 `srcdoc`、`data:base64`、`blob:`、Shadow DOM、`innerHTML` 等多种单文件方案，
> 均因浏览器安全策略或模板依赖 (`:root`/`html[data-theme]`/`document.documentElement`) 而无法正常工作。
> 只有 `<iframe src="file.html">` 引用外部文件的方式完全可靠。

```python
from lightweight_charts import HtmlTabChart

chart = HtmlTabChart(width=1200, height=800)
chart.set_name('策略1')
chart.set(df)

# 1. 导出图表内容文件
with open('chart_content.html', 'w', encoding='utf-8') as f:
    f.write(chart.get_html())

# 2. 创建外壳页面（通过 src 引用内容文件）
outer = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Embed</title></head>
<body style="margin:0">
<iframe src="chart_content.html" style="width:100%;height:100%;border:none"></iframe>
</body></html>'''
with open('chart_embed.html', 'w', encoding='utf-8') as f:
    f.write(outer)
```

两个文件放在同一目录，打开 `chart_embed.html` 即可。

### 3.4 CrossProcessChart (跨进程嵌入 Qt)

支持 Windows 和 Linux/X11。图表运行在独立子进程中（pywebview），通过原生窗口句柄嵌入到 Qt 布局中，类似 Chrome 多进程窗口嵌入。不支持 Wayland 和 macOS。所有 AbstractChart 方法（set, update, marker, create_line 等）均可用。

```python
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from lightweight_charts import CrossProcessChart

app = QApplication(sys.argv)
parent = QMainWindow()
central = QWidget()
layout = QVBoxLayout(central)

chart = CrossProcessChart(
    parent=central,
    width=800, height=600,
    title='AAPL',
    toolbox=True
)
layout.addWidget(chart.widget)      # 获取嵌入用的 QWidget

parent.setCentralWidget(central)
parent.show()
chart.set(df)                       # 所有 AbstractChart API 均可直接调用
chart.legend(visible=True)
app.exec()
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `parent` | `QWidget` | `None` | 父 Qt 控件 |
| `width` | `int` | `800` | 窗口宽度 |
| `height` | `int` | `600` | 窗口高度 |
| `inner_width` | `float` | `1.0` | 图表宽度占比 |
| `inner_height` | `float` | `1.0` | 图表高度占比 |
| `toolbox` | `bool` | `False` | 绘图工具箱 |
| `title` | `str` | `''` | 窗口标题 |
| `debug` | `bool` | `False` | 调试模式 |
| `position` | `int/tuple` | `111` | 图表位置（网格格式） |

**特有方法：**

| 方法 | 说明 |
|------|------|
| `chart.widget` | 返回嵌入用的 QWidget，添加到 Qt 布局中 |
| `chart.exit()` | 终止子进程并清理资源 |
| `chart.resize(w, h)` | 调整嵌入窗口大小 |

**平台说明：**
- **Windows**: 开箱即用
- **Linux/X11**: 需要安装 `PyGObject` (`pip install PyGObject`)，且不能在 Wayland 下运行
- **Linux/Wayland / macOS**: 不支持

### 3.5 其他 Widget 类型

| 类名 | 导入源 | 说明 |
|------|--------|------|
| `CrossProcessChart` | `lightweight_charts` | 跨进程嵌入 Qt (Windows + Linux/X11): pywebview 窗口通过原生句柄嵌入 QWidget |
| `JupyterChart` | `lightweight_charts` | Jupyter Notebook 内嵌 |
| `QtChart` | `lightweight_charts.widgets` | PyQt5/PyQt6/PySide6 嵌入（同进程） |
| `WxChart` | `lightweight_charts.widgets` | wxPython 嵌入 |
| `StreamlitChart` | `lightweight_charts.widgets` | Streamlit 嵌入 |
| `ReflexChart` | `lightweight_charts` | Reflex 嵌入（生成 HTML / 直接返回 rx.Component） |

### 3.6 数据方法 (Candlestick)

```python
chart.set(df, keep_drawings=False)
# 设置初始数据。df 列: time/open/high/low/close + 可选 volume/open_interest

chart.update(series)
# 更新最后一根 K 线

chart.update_tick(series)
# 从 tick 更新 K 线（旧名 update_from_tick，已废弃）

chart.pop(count=1)
# 从系列末尾移除指定数量的数据点

chart.update_bars(df)
# 批量 OHLCV 增量更新: 遍历df每行调用update()，JS命令合并为一条发送

chart.update_ticks(df)
# 批量 Tick 增量更新（旧名 update_from_ticks，已废弃）
# 输入: time, price, [volume], [open_interest]

chart.set_period(seconds)
# 锁定时间级别: set()时跳过自动推断，所有时间戳对齐到锁定间隔

# 数据访问属性
chart.data          # 合并 DataFrame: time, open, high, low, close, volume, open_interest（始终7列）
chart.candle_data   # K线原始: time, open, high, low, close
chart.vol_data      # 成交量原始: time, value
chart.oi_data       # 持仓量原始: time, value
```

### 3.6.1 `set()` vs `reset()` 对比

| 资源 | `chart.set(df)` | `chart.reset()` |
|------|----------------|-----------------|
| K 线数据 | ✅ 替换 | ✅ 清空（自动重建） |
| 成交量 | ✅ 替换 | ✅ 清空（自动重建） |
| 持仓量 | ✅ 替换 | ✅ 清空（自动重建） |
| **指标线 (Line/Histogram)** | ✅ **保留**，更新匹配列名的 | ❌ **全部删除** |
| **标记 (markers)** | ✅ **保留** | ❌ **全部清除** |
| **绘图 (drawings)** | ⚠️ 看 `keep_drawings` 参数 | ❌ **全部清除** |
| **PriceLine** | ✅ **保留** | ❌ **清除** |
| **Table** | ✅ **保留** | ❌ **清除** |
| **事件 handlers** | ✅ **保留** | ❌ **清除** |
| **TopBar** | ✅ 保留 | ✅ 保留 |
| **样式配置** | ✅ 保留 | ✅ 保留 |

**`set()` 行为：** 温和替换，只动 K 线/成交量/持仓量，其他一切不动。指标线只更新有匹配列名的，不匹配的保留旧数据。

**`reset()` 行为：** 彻底清空所有资源（K 线 + 指标线 + 标记 + 绘图 + PriceLine + Table + handlers），TopBar 和样式保留。candle/volume/oi 自动重建（始终存在），方便后续 `set()` 直接填充。

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

### 3.6.2 批量增量更新 — update_bars() / update_ticks()

批量增量更新，将多条 K 线或 tick 的 JS 命令合并为一条批量发送，大幅减少 JS 通信开销。

```python
# 批量 OHLCV 增量更新
chart.update_bars(df)
# df: DataFrame, 列: time/open/high/low/close + 可选 volume/open_interest
# 遍历每一行，复用 update() 的逻辑（覆盖/追加 + new_bar 事件）
# 所有 JS 命令合并为一条 run_script 发送

# 批量 Tick 增量更新
chart.update_ticks(df)
# df: DataFrame, 列: time/price + 可选 volume/open_interest
# 各系列各自聚合: candle(OHLC from price), volume(sum), OI(last)
# 所有 JS 命令合并为一条 run_script 发送
```

### 3.6.3 锁定时间级别 — set_period()

锁定 _interval，set() 时跳过自动推断，并将 DataFrame 中所有时间戳对齐到锁定间隔。

> **重要提示**: set_period() 后，需要重新调用 chart.set(df) 来使其生效，否则后续的各种标记可能会错乱。

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
- 锁定后，`_normal_df() → _time_to_bar_time()` 跳过 `_set_interval()`，`_interval` 保持不变
- 时间戳转换后执行：`time = interval * (time // interval)`，对齐到间隔边界
- **去重保护：** 对齐后按时间戳去重（保留每组最后一行），防止 JS `Value is null` 错误
  - 例如：10 根 30min K 线锁定到 1h → 对齐后得到 5 个唯一时间戳
  - 同级别数据（5min→5min）不受影响，不会去重
- `update()` / `update_from_tick()` 中的 `_single_datetime_format()` 使用锁定后的 `_interval` 对齐
- `marker()` 中的时间对齐也同样受锁定影响

### 3.6.4 标记 (Marker)

标记 API 在 `SeriesCommon` 上定义，**对所有系列类型均有效**（Candlestick、Line、Histogram、CandleSeries 等）。

```python
# ── 在 Candlestick（主图）上添加标记 ──
chart.marker(time='2024-01-15', position='above', shape='arrow_down',
             color='#FF0000', text='卖出')
chart.marker(time='2024-02-01', position='below', shape='arrow_up',
             color='#00FF00', text='买入')

# ── 在 Line/Histogram 上添加标记 ──
line20 = chart.create_line('SMA20', color='#2196F3')
line20.set(sma_df)
line20.marker(time='2024-01-20', position='below', shape='circle',
              color='#2196F3', text='SMA20 Cross')

hist = chart.create_histogram('Volume', color='rgba(100,100,200,0.5)', pane_index=1)
hist.set(vol_df)
hist.marker(time='2024-01-05', position='below', shape='square',
            color='#9C27B0', text='Vol Spike')

# ── 在 CandleSeries 上添加标记 ──
ref = chart.create_candle_series(name='参考K线', pane_index=1)
ref.set(df_ref)
ref.marker(time='2024-01-20', position='above', shape='arrow_down',
           color='#FF6B35', text='卖出信号')

# ── 批量标记 ──
line20.marker_list([
    {'time': '2024-02-10', 'position': 'below', 'shape': 'arrow_up',
     'color': '#00BCD4', 'text': 'Batch 1'},
    {'time': '2024-03-05', 'position': 'above', 'shape': 'arrow_down',
     'color': '#00BCD4', 'text': 'Batch 2'},
])

# ── 管理标记 ──
chart.marker_auto_scale(enable=True)   # 控制标记是否参与价格轴自动缩放
chart.remove_marker(marker_id)          # 按 ID 删除单个标记
chart.clear_markers()                   # 删除当前系列的所有标记

# ── 查看标记数量 ──
print(len(chart.markers))       # Candlestick 上的标记
print(len(line20.markers))      # Line 上的标记
print(len(hist.markers))        # Histogram 上的标记
```

### 3.7 折线与柱状图

```python
line = chart.create_line(
    name='SMA 50', color='rgba(..., 0.6)',
    style='solid', width=2,
    price_line=True, price_label=True,
    price_scale_id=None, pane_index=0
)
line.set(df)           # df 列: time + value
line.update(series)    # 逐点实时更新
line.update_bars(df)   # 批量追加数据点
line.marker(...)       # 在折线上添加标记 (见 §3.6.4)
line.marker_list([...])# 批量添加标记
line.delete()          # 删除 (JS + Python 双端清理)

hist = chart.create_histogram(
    name='volume', color='...',
    price_line=True, price_label=True,
    scale_margin_top=0.0, scale_margin_bottom=0.0,
    pane_index=0
)
hist.set(df)           # df 列: time + value + [color]
hist.update(series)
hist.update_bars(df)
hist.marker(...)
hist.scale(top=0.0, bottom=0.0)
hist.delete()

chart.lines()  # 返回所有已创建的 LineSeries/HistogramSeries/CandleSeries 列表

# 注意：Line/Histogram 不再由 chart.set() 自动填充数据
# 需要手动调用 line.set(df) 独立设置，df 必须包含 time 和 value 列
```

#### Histogram 任意颜色支持

Histogram 内置 color 列支持，DataFrame 中包含 `color` 列时每根柱子自动独立着色：

```python
import pandas as pd
from lightweight_charts import Chart

chart = Chart()
chart.set_period(60)

# 正负渐变色示例
df = pd.DataFrame({
    'time': [1, 2, 3, 4, 5],
    'value': [100, -200, 150, -50, 80],
    'color': ['#26a69a', '#ef5350', '#26a69a', '#ef5350', '#26a69a'],
})

hist = chart.create_histogram(name='Delta', pane_index=1)
hist.set(df)  # color 列自动携带到 JS 端
```

> ⚠️ **注意**：`chart.set()` 不会转发 color 列，如需 histogram 上任意颜色需要**单独 `hist.set()`**。

> **示例 35** (`examples/35_line_markers/line_markers.py`) 演示了在 Line、Histogram 和 CandleSeries 上使用 marker 和 marker_list 的完整用法。

### 3.7.1 独立 K 线系列 — CandleSeries

独立 K 线系列，**无 volume / open interest**，可在任意 pane 上绘制参考 K 线或对比品种。
与主 K 线（`Candlestick`）的区别：Candlestick 是图表固有组件（自带 volume + OI），
CandleSeries 是附加系列（仅 OHLC），通过 `create_candle_series()` 创建。

```python
from lightweight_charts import Chart

chart = Chart(width=1400, height=900, title='CandleSeries Demo')

# 主 K 线 (pane 0) — Candlestick，自带 volume
chart.set(df_main)

# 参考 K 线 (pane 1) — CandleSeries，仅 OHLC
ref = chart.create_candle_series(
    name='参考品种',
    pane_index=1,                   # 独立面板
    up_color='rgba(0, 150, 255, 0.8)',
    down_color='rgba(255, 100, 0, 0.8)',
    price_line=False,
    price_label=True,
    border_visible=True,
    wick_visible=True,
    price_scale_id=None,            # None = 独立价格轴
    crosshair_marker=True,
)
ref.set(df_ref)                     # 设置初始数据

# 支持所有 SeriesCommon 方法
ref.update(new_bar)                 # 更新最新 bar 或追加新 bar
ref.update_bars(df_more)            # 批量追加
ref.marker(time, position, shape, color, text)  # 添加标记
ref.marker_list([...])              # 批量标记
ref.clear_data()                    # 清空数据
ref.delete()                        # 删除系列
```

**create_candle_series() 参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | `''` | 系列名称，用于图例显示 |
| `pane_index` | `int` | `0` | 面板索引，0 = 与主 K 线同面板，>0 = 独立面板 |
| `up_color` | `str` | `'rgba(39,157,130,100)'` | 上涨 K 线颜色 |
| `down_color` | `str` | `'rgba(200,97,100,100)'` | 下跌 K 线颜色 |
| `border_visible` | `bool` | `True` | 是否显示 K 线边框 |
| `wick_visible` | `bool` | `True` | 是否显示影线 |
| `price_line` | `bool` | `False` | 是否显示价格线（右侧当前价格） |
| `price_label` | `bool` | `True` | 是否显示价格标签 |
| `price_scale_id` | `str\|None` | `None` | 价格刻度 ID，None = 独立价格轴 |
| `crosshair_marker` | `bool` | `True` | 十字光标是否显示标记 |

**CandleSeries vs Candlestick 对比：**

| 特性 | Candlestick（主 K 线） | CandleSeries（独立 K 线） |
|------|----------------------|--------------------------|
| 创建方式 | `chart.set(df)` 自动创建 | `chart.create_candle_series()` |
| volume/OI | ✅ 自动处理 | ❌ 不支持 |
| 数据要求 | time, O, H, L, C, [volume, OI] | time, O, H, L, C |
| pane 数量 | 固定 pane 0 | 任意 pane |
| 多实例 | ❌ 唯一 | ✅ 可创建多个 |
| marker | ✅ | ✅ |
| 样式配置 | `chart.candle_style()` | 构造函数参数 |

> **示例 34** (`examples/34_candle_series/`) 包含三个子示例：
> - `1_static.py` — 两组 K 线并排显示（主图 + pane 1 参考品种）
> - `2_live_update.py` — 实时更新 CandleSeries
> - `3_batch_update.py` — 批量增量更新

### 3.7.2 面积图系列 — AreaSeries

折线下方填充渐变色，适用于展示指标的 magnitude，如均线面积、波动率面积等。

```python
from lightweight_charts import Chart

chart = Chart(width=1200, height=800)
chart.set(df)  # 先设置 K 线数据

# 面积图叠加到主 K 线（pane 0）
area = chart.create_area_series(
    name='SMA 20',
    color='#2196F3',              # 线条颜色
    style='solid',                # 线条样式
    width=2,                      # 线条宽度
    top_color='rgba(33,150,243,0.35)',    # 面积顶部渐变色
    bottom_color='rgba(33,150,243,0.0)',  # 面积底部渐变色
    relative_gradient=False,      # 渐变是否相对于基准值
    invert_filled_area=False,     # 是否反转填充（填充线上方）
    price_line=False,
    price_label=False,
    pane_index=0,                 # 与主 K 线同面板
)
area.set(pd.DataFrame({'time': df['time'], 'value': sma20}).dropna())

# 面积图独立面板（pane 1）
area2 = chart.create_area_series(
    name='波动率',
    color='#FF9800',
    top_color='rgba(255,152,0,0.3)',
    bottom_color='rgba(255,152,0,0.0)',
    pane_index=1,
)
area2.set(pd.DataFrame({'time': df['time'], 'value': volatility}).dropna())
```

**create_area_series() 参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | `''` | 系列名称 |
| `color` | `str` | `'#2196F3'` | 线条颜色 |
| `style` | `LINE_STYLE` | `'solid'` | 线条样式 |
| `width` | `int` | `2` | 线条宽度 |
| `top_color` | `str` | `'rgba(33,150,243,0.4)'` | 面积顶部渐变色 |
| `bottom_color` | `str` | `'rgba(33,150,243,0)'` | 面积底部渐变色 |
| `relative_gradient` | `bool` | `False` | 渐变是否相对于基准值 |
| `invert_filled_area` | `bool` | `False` | 是否反转填充区域 |
| `price_line` | `bool` | `True` | 是否显示价格线 |
| `price_label` | `bool` | `True` | 是否显示价格标签 |
| `price_scale_id` | `str\|None` | `None` | 价格刻度 ID |
| `pane_index` | `int` | `0` | 面板索引 |

**数据格式**：与 LineSeries 完全一致 — `time` + `value` 列。

> **示例 37** (`examples/37_more_series_types/`) 演示了 AreaSeries、OHLCBarSeries、BaselineSeries 的完整用法。

### 3.7.3 美国线系列 — OHLCBarSeries

横向 OHLC 柱状图，与 K 线使用同一套数据，但用横向短横表示 open（左）和 close（右），无矩形实体。
继承自 `CandleSeries`，共享全部 OHLC 数据处理逻辑（set/update_bars/update_ticks），仅 JS 创建方法和样式配置不同。

```python
from lightweight_charts import Chart

chart = Chart(width=1200, height=800)
chart.set(df)  # 先设置主 K 线

# 美国线独立面板
bar = chart.create_ohlc_bar_series(
    name='美国线',
    up_color='#26a69a',           # 上涨颜色（close > open）
    down_color='#ef5350',         # 下跌颜色
    open_visible=True,            # 是否显示 open 横线
    thin_bars=False,              # 是否用细棒显示
    price_line=False,
    price_label=True,
    pane_index=1,                 # 独立面板
)
bar.set(df[['time', 'open', 'high', 'low', 'close']])

# 修改样式
bar.bar_style(up_color='#00BCD4', down_color='#FF5722', thin_bars=True)

# 所有 CandleSeries 方法均可用
bar.update(new_bar)               # 更新最新 bar
bar.update_bars(df_more)          # 批量追加
bar.marker(time, position, shape, color, text)  # 添加标记
bar.delete()                      # 删除系列
```

**create_ohlc_bar_series() 参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | `''` | 系列名称 |
| `up_color` | `str` | `'#26a69a'` | 上涨颜色 |
| `down_color` | `str` | `'#ef5350'` | 下跌颜色 |
| `open_visible` | `bool` | `True` | 是否显示 open 横线 |
| `thin_bars` | `bool` | `True` | 是否用细棒显示 |
| `price_line` | `bool` | `False` | 是否显示价格线 |
| `price_label` | `bool` | `True` | 是否显示价格标签 |
| `price_scale_id` | `str\|None` | `None` | 价格刻度 ID |
| `pane_index` | `int` | `0` | 面板索引 |

**数据格式**：与 CandleSeries 完全一致 — `time` + `open` + `high` + `low` + `close` 列。

**OHLCBarSeries vs CandleSeries 对比：**

| 特性 | CandleSeries | OHLCBarSeries |
|------|-------------|---------------|
| JS 系列类型 | CandlestickSeries | BarSeries |
| 数据格式 | time + OHLC | time + OHLC（完全一致） |
| 继承 | SeriesCommon | CandleSeries |
| 样式方法 | `candle_style()` | `bar_style()` |
| 视觉效果 | 矩形实体 + 影线 | 横向短横（open 左 / close 右） |
| `candle_style()` | ✅ 可用 | ❌ 抛 AttributeError |

**bar_style() 参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `up_color` | `str` | `''` | 上涨颜色（留空不变） |
| `down_color` | `str` | `''` | 下跌颜色（留空不变） |
| `open_visible` | `bool\|None` | `None` | 是否显示 open 横线（None 不变） |
| `thin_bars` | `bool\|None` | `None` | 是否用细棒显示（None 不变） |

### 3.7.4 基准线系列 — BaselineSeries

以某个基准值为界，上方/下方分别着色，适合展示相对于某个参考值的变化。

```python
from lightweight_charts import Chart

chart = Chart(width=1200, height=800)
chart.set(df)

# RSI 偏离零轴
rsi_dev = calculate_rsi_deviation(df, period=14)

baseline = chart.create_baseline_series(
    name='RSI 偏离',
    base_value=0,                             # 基准值
    top_fill_color1='rgba(38,166,154,0.3)',   # 上方渐变起始色
    top_fill_color2='rgba(38,166,154,0.0)',   # 上方渐变结束色
    top_line_color='rgba(38,166,154,1)',      # 上方线条颜色
    bottom_fill_color1='rgba(239,83,80,0.0)', # 下方渐变起始色
    bottom_fill_color2='rgba(239,83,80,0.3)', # 下方渐变结束色
    bottom_line_color='rgba(239,83,80,1)',    # 下方线条颜色
    line_width=2,
    line_style='solid',
    relative_gradient=False,
    price_line=False,
    price_label=False,
    pane_index=1,
)
baseline.set(pd.DataFrame({'time': df['time'], 'value': rsi_dev}).dropna())
```

**create_baseline_series() 参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | `''` | 系列名称 |
| `base_value` | `float` | `0` | 基准值 |
| `top_fill_color1` | `str` | `'rgba(38,166,154,0.28)'` | 上方渐变起始色 |
| `top_fill_color2` | `str` | `'rgba(38,166,154,0.05)'` | 上方渐变结束色 |
| `top_line_color` | `str` | `'rgba(38,166,154,1)'` | 上方线条颜色 |
| `bottom_fill_color1` | `str` | `'rgba(239,83,80,0.05)'` | 下方渐变起始色 |
| `bottom_fill_color2` | `str` | `'rgba(239,83,80,0.28)'` | 下方渐变结束色 |
| `bottom_line_color` | `str` | `'rgba(239,83,80,1)'` | 下方线条颜色 |
| `line_width` | `int` | `2` | 线条宽度 |
| `line_style` | `LINE_STYLE` | `'solid'` | 线条样式 |
| `relative_gradient` | `bool` | `False` | 渐变是否相对于基准值 |
| `price_line` | `bool` | `True` | 是否显示价格线 |
| `price_label` | `bool` | `True` | 是否显示价格标签 |
| `price_scale_id` | `str\|None` | `None` | 价格刻度 ID |
| `pane_index` | `int` | `0` | 面板索引 |

**数据格式**：与 LineSeries 完全一致 — `time` + `value` 列。value > base_value 显示上方颜色，value < base_value 显示下方颜色。

### 3.8 样式配置

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

### 3.9 子图表 (Multi-Pane)

```python
sub = chart.create_subchart(
    position=122,                   # 网格位置 (1行2列，第2个)
    width=1.0, height=1.0,          # 相对于网格单元的大小
    sync_id=None,                   # 同步滚动/光标
    scale_candles_only=False,
    sync_crosshairs_only=False,
    toolbox=False,
    autosize=True,                  # 是否自动调整大小
    pane_index=0,                   # 面板索引
    marker_auto_scale=True          # 标记是否自动缩放
)
# sub 是 AbstractChart 实例，有完整的 API
line = sub.create_line(...)
sub.set(df)
```

**width/height 参数说明：**
- `1.0`：占满网格单元
- `< 1.0`：向内缩，对齐左上角
- `> 1.0`：侵占其他网格空间

**运行时位置控制：**
```python
# 获取当前位置（show 前后均可调用）
x, y, w, h = chart.get_position()
print(f"位置: x={x}, y={y}, width={w}, height={h}")

# 动态设置位置（百分比 0-1，show 前后均可调用）
chart.set_position(0.0, 0.0, 0.5, 1.0)  # 左半部分
chart.set_position(0.5, 0.0, 0.5, 1.0)  # 右半部分

# 传入 None 恢复默认网格位置
chart.set_position(None, None, None, None)  # 全部恢复默认

# 单个参数传入 None，仅恢复该参数的默认值
chart.set_position(x=0.1, y=None, width=0.5, height=0.5)  # y 恢复默认
```

### 3.10 事件回调 (Events)

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

### 3.11 图表级高级选项 — chart_options()

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

### 3.12 TopBar

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

### 3.13 绘图工具 (ToolBox + Drawings)

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

### 3.14 表格 (Table)

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

### 3.15 成交量与持仓量 (VolumeSeries / OpenInterestSeries)

成交量和持仓量是**独立的 self-managing 系列**，在 `AbstractChart.__init__` 中自动创建，
各自维护 `self.data` + `self._last_bar`，支持独立的完整生命周期管理。

```python
# chart.volume 和 chart.oi 在 AbstractChart 创建时自动初始化
# chart.set(df) 中的 volume/open_interest 列会自动填充它们

df = pd.read_csv('data.csv')
# df 列: time, open, high, low, close, volume, open_interest
chart.set(df)  # volume → chart.volume，open_interest → chart.oi
```

**VolumeSeries API（chart.volume）：**

```python
vol = chart.volume  # 自动创建的成交量实例

# 设置数据
vol.set(df)                          # df 需含 time, value, open, close 列

# 实时更新
vol.update(series)                   # 更新最新 bar 或追加新 bar
vol.update_bars(df)                  # 批量更新（JS 命令合并发送）
vol.update_ticks(df)                 # tick 聚合后更新（volume 始终 sum）

# 样式配置
vol.config(
    scale_margin_top=0.8,            # 价格轴顶部边距
    scale_margin_bottom=0.0,         # 价格轴底部边距
    up_color='rgba(83,141,131,0.8)', # 上涨颜色（close > open）
    down_color='rgba(200,127,130,0.8)' # 下跌颜色
)

# 委托方法（在 chart 上直接调用）
chart.volume_config(scale_margin_top=0.7, up_color='green', down_color='red')

# 清理
vol.clear_data()                     # 清空数据
vol.delete()                         # 删除系列（JS + Python 双端清理）
```

**OpenInterestSeries API（chart.oi）：**

```python
oi = chart.oi  # 自动创建的持仓量实例（全部继承 SeriesCommon）

# 设置数据
oi.set(df)                           # df 需含 time + value 列

# 实时更新
oi.update(series)                    # 更新最新 bar 或追加新 bar
oi.update_bars(df)                   # 批量更新
oi.update_ticks(df)                  # tick 聚合后更新

# 样式配置
oi.config(
    color='#F5A623',                 # 线条颜色
    line_width=1,                    # 线宽
    scale_margin_top=0.8,            # 价格轴顶部边距
    scale_margin_bottom=0.0          # 价格轴底部边距
)

# 委托方法
chart.open_interest_config(color='#FF6600')

# 清理
oi.clear_data()
oi.delete()
```

**实现原理：**
- 成交量：`priceScaleId: 'volume_scale'`（HistogramSeries），`priceFormat: {type: "volume"}`
- 持仓量：`priceScaleId: 'oi_scale'`（LineSeries），`autoScale: true`
- 两者 `scaleMargins: {top: 0.8, bottom: 0}` 共享同一视觉区域，各自独立缩放
- OI series **默认隐藏**；有数据时自动显示，无数据时自动隐藏

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
| **图表核心** | `src/general/handler.ts` | `Handler` 类 — 前端总控，支持网格布局 |
| **图例** | `src/general/legend.ts` | 图例实现 |
| **顶栏** | `src/general/topbar.ts` | 顶栏 UI 组件 |
| **工具箱** | `src/general/toolbox.ts` | 绘图工具箱 UI |
| **菜单** | `src/general/menu.ts` | 右键/下拉菜单 |
| **表格** | `src/general/table.ts` | 数据表格渲染 |
| **全局参数** | `src/general/global-params.ts` | 全局参数 |
| **样式** | `src/general/styles.css` | 全局 CSS |
| **绘图引擎** | `src/drawing/drawing-tool.ts` | 绘图工具核心 |
| **绘图数据源** | `src/drawing/data-source.ts` | 绘图数据管理 |
| **绘图基类** | `src/drawing/drawing.ts` | 绘图基类定义 |
| **两点绘图** | `src/drawing/two-point-drawing.ts` | 趋势线/方框等两点绘图基类 |
| **绘图面板** | `src/drawing/pane-renderer.ts`, `pane-view.ts` | 绘图渲染器和视图 |
| **绘图选项** | `src/drawing/options.ts` | 绘图样式选项 |
| **上下文菜单** | `src/context-menu/context-menu.ts` | 右键上下文菜单 |
| **颜色选择器** | `src/context-menu/color-picker.ts` | 颜色选择器组件 |
| **样式选择器** | `src/context-menu/style-picker.ts` | 线条/填充样式选择器 |
| **趋势线** | `src/trend-line/` | 趋势线（trend-line.ts + pane-renderer + pane-view） |
| **水平线** | `src/horizontal-line/` | 水平线 + 射线（horizontal-line.ts + ray-line.ts + axis-view + renderers） |
| **垂直线** | `src/vertical-line/` | 垂直线（vertical-line.ts + axis-view + renderers） |
| **矩形** | `src/box/` | 矩形框（box.ts + pane-renderer + pane-view） |
| **辅助工具** | `src/helpers/` | canvas 渲染、时间处理、断言、dimensions/（crosshair-width, full-width, positions） |

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
| 18 | `18_hovered_series_on_top` | `hovered_series_on_top` — 鼠标悬停时系列是否浮到顶层（左右对比） | `hovered_series_on_top.py` |
| 19 | `19_timescale_options` | `time_scale()` 新参数 — 像素偏移 / 数据合并 (conflation) | `timescale_options.py` |
| 20 | `20_tick_mark_density` | `tick_mark_density` — 价格轴标签密度控制 (1.0 / 2.5 / 6.0) | `tick_mark_density.py` |
| 21 | `21_marker_auto_scale` | `marker_auto_scale()` — 标记是否参与价格轴自动缩放 | `marker_auto_scale.py` |
| 22 | `22_pop` | `pop(n)` — 从末尾移除 N 根 K 线 | `pop.py` |
| 23 | `23_crosshair_move` | `events.crosshair_move` — 鼠标悬停实时回调 (Hit Testing) | `crosshair_move.py` |
| 24 | `24_price_format` | `set_price_format(type='base')` — 基础价格格式，避免浮点精度问题 (v5.2.0+) | `price_format.py` |
| 25 | `25_screenshot_enhanced` | `screenshot(add_top_layer=True, include_crosshair=True)` — 增强截图 (v5.2.0+) | `screenshot_enhanced.py` |
| 26 | `26_series_batch_update` | 系列批量更新：`update_bars()` 用于 Line 和 Histogram 系列 | `series_batch_update.py` |
| 27 | `27_reflex_chart` | Reflex 嵌入：K线 + SMA 指标在 Reflex 应用中渲染 | `rx_chart.py` |
| 28 | `28_cross_process_chart` | CrossProcessChart：跨进程嵌入 PySide6 QWidget | `cross_process_chart.py` |
| 29 | `29_grid_layout` | 网格布局：position 参数三种格式 + get_position/set_position | `grid_layout.py` |
| 30 | `30_table_component` | 表格组件：自选股表格 + 动态更新 + 样式定制 | `table_component.py` |
| 31 | `31_chart_sync` | 图表同步：多图表时间轴同步 + 十字光标同步 | `chart_sync.py` |
| 32 | `32_html_tab_chart` | HtmlTabChart 多策略演示：2 子图 × 2 面板 + 交易明细 + 绩效指标 | `html_tab_chart_demo.py`, `html_chart_demo.py` |
| 33 | `33_reset_sub` | reset_sub 子图重置：2×2 网格中填充→清除→重填→验证独立性 | `reset_sub_demo.py` |
| 34 | `34_candle_series` | CandleSeries 独立 K 线：静态并排 + 实时更新 + 批量更新 | `1_static.py`, `2_live_update.py`, `3_batch_update.py` |
| 35 | `35_line_markers` | Line/Histogram marker：marker + marker_list 在各系列类型上的用法 | `line_markers.py` |

---

## 六、测试 (test/)

```
test/
├── run_tests.py              # 测试入口 (原始)
├── run_new_tests.py          # 测试入口 (新增)
├── test_cleanup.py           # 资源全链路创建/删除 + JS TOML 审计 + 多图表独立清理
├── test_features.py          # 功能测试: 数据重命名/line追踪/截图/topbar事件
├── test_candle_series.py     # CandleSeries 独立系列: 创建/设置/标记/清理
├── test_data_aggregation.py  # 数据聚合/清洗: normal_df/merge_value_by_time/时间对齐
├── test_position.py          # position 参数解析: 字符串转换/整数格式/元组格式/网格冲突检测
├── test_reset_sub.py         # reset_sub 子图重置: 13项清除/其他子图独立性/同步组恢复
├── test_sync_debug.py        # 同步组调试: syncCharts/syncChartsAll/级联防护
└── test_util.py              # 工具函数: IDGen/Position/parse_event_message/BulkRunScript
```

运行:
```bash
python -m pytest test/ -v                    # 运行所有测试 (需 pytest)
python -m pytest test/test_position.py -v    # 仅 position 解析测试
python test/test_cleanup.py                  # 资源清理测试 (需 GUI 环境)
python test/test_features.py                 # 功能测试
python test/run_tests.py                     # 原始测试入口
python test/run_new_tests.py                 # 新增测试入口
```

---

## 七、依赖与构建

### 核心依赖（必需）

| 依赖 | 用途 |
|------|------|
| `pandas` | 数据处理 |
| `pywebview>=5.0.5` | 桌面 WebView 窗口 |

### 可选依赖（按功能安装）

| 包名 | 安装方式 | 用途 |
|------|---------|------|
| `pyside6` | `pip install lightweight-charts-onesixth[pyside6]` | PySide6 嵌入 (QtChart) |
| `pyqt5` | `pip install lightweight-charts-onesixth[pyqt5]` | PyQt5 嵌入 |
| `pyqt6` | `pip install lightweight-charts-onesixth[pyqt6]` | PyQt6 嵌入 |
| `wxpython` | `pip install lightweight-charts-onesixth[wx]` | wxPython 嵌入 (WxChart) |
| `ipython` + `ipywidgets` | `pip install lightweight-charts-onesixth[jupyter]` | Jupyter Notebook (JupyterChart) |
| `reflex` | `pip install lightweight-charts-onesixth[reflex]` | Reflex 框架嵌入 (ReflexChart) |
| `PyGObject` | 系统包管理器 | Linux/X11 CrossProcessChart 支持 |
| `pytest` | `pip install lightweight-charts-onesixth[dev]` | 运行测试 |

### 前端构建

```bash
# 编译 TypeScript 前端 src/ → js/bundle.js
npx rollup -c rollup.config.js
# 注意：不是 npx tsc，使用 rollup 构建
```

---

## 八、常用模式摘要

```
初始化 → 设置数据 → 可选: 添加指标/绘图/事件 → show(block=True)

show() 三种模式:
  chart.show()           # 非阻塞，窗口显示后立即返回
  chart.show(block=True) # 阻塞，等待窗口关闭
  chart.show(wait=5)     # 等待 5 秒后自动关闭（截图/演示场景）

实时数据:
  chart.set(initial_df)
  chart.show()
  for each update:
    chart.update(new_bar)        # K线更新
    或 chart.update_from_tick(tick)  # Tick更新

多面板:
  sub = chart.create_subchart(position=122)
  line = sub.create_line(...)
  sub.set(data)

网格布局:
  chart1 = Chart(position=221)  # 2行2列，第1个
  chart2 = chart1.create_subchart(position=222)
  chart3 = chart1.create_subchart(position=223)
  chart4 = chart1.create_subchart(position=224)

动态位置控制:
  x, y, w, h = chart.get_position()
  chart.set_position(0.0, 0.0, 0.5, 1.0)  # 左半部分
  chart.set_position(None, None, None, None)  # 恢复默认网格位置

事件驱动:
  chart.events.search += handler
  chart.topbar.switcher('tf', options, func=handler)

CandleSeries 对比品种:
  ref = chart.create_candle_series(name='参考K线', pane_index=1)
  ref.set(df_ref)
  ref.marker(time, 'above', 'arrow_down', '#FF0000', '卖出')

Line/Histogram 标记:
  line = chart.create_line('SMA20', color='#2196F3')
  line.set(sma_df)
  line.marker(time, 'below', 'circle', '#2196F3', '信号')
  line.marker_list([{time, position, shape, color, text}, ...])

子图重置:
  sub.reset_sub()        # 清除子图全部内容（13类资源）
  sub.set(new_df)        # 重新填充，子图可继续使用

运行时同步组管理:
  chart.join_sync_group('group_a')                    # 动态加入同步组
  chart.join_sync_group('group_b', crosshair_only=True)  # 仅同步十字光标
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
self._html_chart_init = f'window.{self.id} = new Lib.Handler("{self.id}", {width}, {height}, {nrows}, {ncols}, {index}, ...)'
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
window.ReflexChart_1 = new Lib.Handler("window.ReflexChart_1", 1.0, 1.0, 1, 1, 1, true, 0, true);
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
# 网格布局保持不变
```

### 10.3 清理事件处理器

```python
chart.clear_handlers()
# 清空 Window 中累积的所有回调，防止嵌入场景下 handler 内存泄漏
```

> ⚠️ **`clear_handlers()` 多图表陷阱：**
> `handlers` 是 `Window` 实例属性，**所有图表共享**。`clear_handlers()` 是全量操作，
> 会清掉 ToolBox 的 `save_drawings` 回调、TopBar 控件回调、其他子图的事件回调等。
> 在多图表共存场景中**严禁使用**，会导致其他图表的回调找不到 handler → `KeyError` 崩溃。

**正确做法 — 使用 `_remove_my_handlers()` 精确清理：**

```python
# _remove_my_handlers() 按 salt（子字符串匹配）精确清理属于本图的 handler
# 例如图表 ID 为 window.AbstractChart_3，salt = '_AbstractChart_3'
# 只移除 key 中包含 '_AbstractChart_3' 的 handler，不影响其他图表
chart._remove_my_handlers()  # 安全：只清理自己的 handler
```

| 方法 | 行为 | 安全性 |
|------|------|--------|
| `chart.clear_handlers()` | 清空 Window 上**所有** handler | ⚠️ 多图表禁用 |
| `chart._remove_my_handlers()` | 只清理本图的 handler（salt 匹配） | ✅ 安全 |

### 10.3.1 重置子图 — reset_sub()

清除指定子图的**全部内容**，保留布局位置，不影响其他子图。清理后可重新填充数据，子图完全可重用。

```python
sub = chart.create_subchart(position=(2, 2, 2), sync_id='main')
sub.set(df)
# ... 添加各种资源 ...

sub.reset_sub()  # 一键清除子图全部内容
sub.set(new_df)  # 重新填充，子图可继续使用
```

**清除范围（13 项）：**

| # | 清除项 | 说明 |
|---|--------|------|
| 1 | K 线/成交量/持仓量 | `clear_data()` |
| 2 | Line/Histogram 系列 | 遍历 `_lines` 逐一 `delete()` |
| 3 | PriceLine | 遍历 `_price_lines` 逐一 `delete()` |
| 4 | 标记 (Markers) | `clear_markers()` |
| 5 | 绘图 (Drawings) | 遍历 `_drawings` 逐一 `delete()` |
| 6 | 表格 (Tables) | 遍历 `_tables` 逐一 `delete()` |
| 7 | ToolBox | JS cleanup + handler 移除（先移 handler 再调 JS，避免 KeyError） |
| 8 | TopBar | Widget 回调 + DOM 移除 |
| 9 | Legend | crosshair 订阅 + DOM 移除 |
| 10 | Events | JSEmitter 事件订阅清理 |
| 11 | syncCharts | 双向解关联 + 重建（恢复同步组） |
| 12 | handlers | 按 salt 精确清理（不影响其他子图） |
| 13 | Legend 重建 | 最后执行，恢复到初始隐藏状态 |

**关键特性：**
- **不影响其他子图**：每个子图有独立的 salt，handlers 清理只匹配自己的 salt
- **同步组自动恢复**：清理后 `_syncGroup` 属性保留，重建时自动恢复同步关系
- **ToolBox 清理顺序**：先移除 Python handler → 再调 JS `_cleanup()`，避免回调排队后 KeyError
- **Legend 重建**：`cleanup()` 移除 DOM 后，最后调用 `recreate()` 恢复到初始状态

> **示例 33** (`examples/33_reset_sub/reset_sub_demo.py`) 演示了 2x2 网格中 reset_sub 的完整流程：
> 填充 4 个子图 → 清除同步子图 → 重新填充 → 清除独立子图 → 重新填充 → 验证其他子图不受影响。

### 10.4 核心清理方法

| 方法 | 行为 |
|------|------|
| `chart.clear_data()` | 清空 OHLCV 数据，保留 series 对象 |
| `chart.reset()` | 重置主图：清空所有数据+标记+绘图+handlers，保留 TopBar 和样式 |
| `sub.reset_sub()` | 重置子图：清除 13 类资源（数据+系列+标记+绘图+表格+ToolBox+TopBar+Legend+Events+sync+handlers），不影响其他子图 |
| `chart.clear_handlers()` | 清空所有事件处理器 ⚠️ 多图表共存时禁用，会误删其他图表的 handler |
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

**根因：** `set()` 会通过 `_normal_df() → _time_to_bar_time()` → `_set_interval` 重新计算 `_interval`。Markers 的时间戳需要按新 `_interval` 对齐后重新发送到 JS 端，但 `set()` 中没有调用 `_update_markers()`。

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

**网格布局模式：**

```python
# 在同一窗口内创建多个子图表
chart = Chart(width=1000, height=800, position=221)
chart2 = chart.create_subchart(position=222)
chart3 = chart.create_subchart(position=223)
chart4 = chart.create_subchart(position=224)

# 每个子图表独立设置数据
chart.set(df1)
chart2.set(df2)
chart3.set(df3)
chart4.set(df4)
```

---

## 十二、OHLC Legend 增强

### 12.1 OI 显示在 Legend

当 DataFrame 包含 `open_interest` 列时，Legend 自动显示：

```
O 109.30 | H 111.38 | L 107.58 | C 110.12 | V 24.5K | OI 112.3K
```

### 12.2 persistent — 常驻模式

```python
chart.legend(visible=True, persistent=True)
# OHLC 鼠标移开也不消失
chart.legend(visible=True, persistent=False)
# 默认行为，鼠标离开图表后隐藏 OHLC
```

### 12.3 shorthand — 简写开关

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

### 14.1 核心差异

| 维度 | `update(series)` | `update_from_tick(series)` |
|------|-----------------|---------------------------|
| **输入** | OHLCV 完整 K 线 | 单条 Tick `{time, price, volume?}` |
| **聚合逻辑** | ❌ 无 — 直接作为 K 线 | ✅ 有 — 聚合为 OHLC |
| **触发 new_bar** | ✅ 时间变化时 | ✅ 时间变化时（通过 update 内部） |
| **典型场景** | 批量更新 / 实时 K 线推送 | 逐 Tick 实时聚合 K 线 |

### 14.2 `_interval` 时间对齐机制

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
