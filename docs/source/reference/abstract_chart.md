
# `AbstractChart`

`````{py:class} AbstractChart(width, height)
Abstracted chart used to create child classes.

___



```{py:method} set(data: pd.DataFrame, keep_drawings: bool = False)
Sets the initial data for the chart.


Columns should be named:
: `time | open | high | low | close | volume`

Time can be given in the index rather than a column, and volume can be omitted if volume is not used. Column names are not case sensitive.

If `keep_drawings` is `True`, any drawings made using the `toolbox` will be redrawn with the new data. This is designed to be used when switching to a different timeframe of the same symbol.

`None` can also be given, which will erase all candle and volume data displayed on the chart.

You can also add columns to color the candles (https://tradingview.github.io/lightweight-charts/tutorials/customization/data-points)
```


___



```{py:method} update(series: pd.Series, keep_drawings: bool = False)
Updates the chart data from a bar.

Series labels should be akin to [`set`](#AbstractChart.set).

```


___


```{py:method} update_from_tick(series: pd.Series, cumulative_volume: bool = False)
Updates the chart from a tick.

Labels should be named:
: `time | price | volume`

As before, the `time` can also be named `date`, and the `volume` can be omitted if volume is not enabled. The `time` column can also be the name of the Series object.

The provided ticks do not need to be rounded to an interval (1 min, 5 min etc.), as the library handles this automatically.

If `cumulative_volume` is used, the volume data given will be added onto the latest bar of volume data.
```
___



```{py:method} create_line(name: str, color: COLOR, style: LINE_STYLE, width: int, price_line: bool, price_label: bool) -> Line

Creates and returns a Line object, representing a `LineSeries` object in Lightweight Charts and can be used to create indicators. As well as the methods described below, the `Line` object also has access to:

[`marker`](#marker), [`horizontal_line`](#AbstractChart.horizontal_line), [`hide_data`](#hide_data), [`show_data`](#show_data) and [`price_line`](#price_line).

Its instance should only be accessed from this method.
```
___



```{py:method} create_histogram(name: str, color: COLOR, price_line: bool, price_label: bool, scale_margin_top: float, scale_margin_bottom: float) -> Histogram

Creates and returns a Histogram object, representing a `HistogramSeries` object in Lightweight Charts and can be used to create indicators. As well as the methods described below, the object also has access to:

[`horizontal_line`](#AbstractChart.horizontal_line), [`hide_data`](#hide_data), [`show_data`](#show_data) and [`price_line`](#price_line).

Its instance should only be accessed from this method.
```
___



```{py:method} lines() -> List[Line]

Returns a list of all lines for the chart.

```
___



```{py:method} trend_line(start_time: str | datetime, start_value: NUM, end_time: str | datetime, end_value: NUM, color: COLOR, width: int, style: LINE_STYLE, round: bool) -> Line

Creates a trend line, drawn from the first point (`start_time`, `start_value`) to the last point (`end_time`, `end_value`).

```
___



```{py:method} ray_line(start_time: str | datetime, value: NUM, color: COLOR, width: int, style: LINE_STYLE, round: bool) -> Line

Creates a ray line, drawn from the first point (`start_time`, `value`) and onwards.

```
___



```{py:method} vertical_span(start_time: TIME | list | tuple, end_time: TIME = None, color: COLOR = 'rgba(252, 219, 3, 0.2)', round: bool = False)

Creates and returns a `VerticalSpan` object.

If `end_time` is not given, then a single vertical line will be placed at `start_time`.

If a list/tuple is passed to `start_time`, vertical lines will be placed at each time.

This should be used after calling [`set`](#AbstractChart.set).
```
___



```{py:method} set_visible_range(self, start_time: TIME, end_time: TIME)

Sets the visible range of the chart.
```
___



```{py:method} resize(self, width: float = None, height: float = None)

Resizes the chart within the window.

Dimensions should be given as a float between or equal to 0 and 1.

Both `width` and `height` do not need to be provided if only one axis is to be changed.
```
___



```{py:method} marker(time: datetime, position: MARKER_POSITION, shape: MARKER_SHAPE, color: COLOR, text: str) -> str

Adds a marker to the chart, and returns its id.

If the `time` parameter is not given, the marker will be placed at the latest bar.

When using multiple markers, they should be placed in chronological order or display bugs may be present.

```
___



```{py:method} marker_list(markers: list) -> List[str]

Creates multiple markers and returns a list of marker ids.

```


```{py:method} remove_marker(marker_id: str)

Removes the marker with the given id.

```
___



```{py:method} horizontal_line(price: NUM, color: COLOR, width: int, style: LINE_STYLE, text: str, axis_label_visible: bool, func: callable= None) -> HorizontalLine

Places a horizontal line at the given price, and returns a [`HorizontalLine`] object.

If a `func` is given, the horizontal line can be edited on the chart. Upon its movement a callback will also be emitted to the callable given, containing the HorizontalLine object. The toolbox should be enabled during its usage. It is designed to be used to update an order (limit, stop, etc.) directly on the chart.

```
___



```{py:method} clear_markers()

Clears the markers displayed on the data.
```
___



```{py:method} precision(precision: int)

Sets the precision of the chart based on the given number of decimal places.

```
___



```{py:method} price_scale(auto_scale: bool, mode: PRICE_SCALE_MODE, invert_scale: bool, align_labels: bool, scale_margin_top: float, scale_margin_bottom: float, border_visible: bool, border_color: COLOR, text_color: COLOR, entire_text_only: bool, visible: bool, ticks_visible: bool, minimum_width: float)

Price scale options for the chart.
```
___



```{py:method} time_scale(right_offset: int, min_bar_spacing: float, visible: bool, time_visible: bool, seconds_visible: bool, border_visible: bool, border_color: COLOR)

Timescale options for the chart.
```
___



```{py:method} layout(background_color: COLOR, text_color: COLOR, font_size: int, font_family: str)

Global layout options for the chart.
```
___



```{py:method} grid(vert_enabled: bool, horz_enabled: bool, color: COLOR, style: LINE_STYLE)

Grid options for the chart.
```
___



```{py:method} candle_style(up_color: COLOR, down_color: COLOR, wick_enabled: bool, border_enabled: bool, border_up_color: COLOR, border_down_color: COLOR, wick_up_color: COLOR, wick_down_color: COLOR)

Candle styling for each of the candle's parts (border, wick).
```
___



```{py:method} volume_config(scale_margin_top: float, scale_margin_bottom: float, up_color: COLOR, down_color: COLOR)

Volume config options.

```{important}
The float values given to scale the margins must be greater than 0 and less than 1.
```
___



```{py:method} crosshair(mode, vert_visible: bool, vert_width: int, vert_color: COLOR, vert_style: LINE_STYLE, vert_label_background_color: COLOR, horz_visible: bool, horz_width: int, horz_color: COLOR, horz_style: LINE_STYLE, horz_label_background_color: COLOR)

Crosshair formatting for its vertical and horizontal axes.
```
___



```{py:method} watermark(text: str, font_size: int, color: COLOR)

Overlays a watermark on top of the chart.
```
___



```{py:method} legend(visible: bool, ohlc: bool, percent: bool, lines: bool, color: COLOR, font_size: int, font_family: str, text: str, color_based_on_candle: bool)

Configures the legend of the chart.
```
___



```{py:method} spinner(visible: bool)

Shows a loading spinner on the chart, which can be used to visualise the loading of large datasets, API calls, etc.

```{important}
This method must be used in conjunction with the search event.
```
___



```{py:method} price_line(label_visible: bool, line_visible: bool, title: str)

Configures the visibility of the last value price line and its label.
```
___



```{py:method} fit()

Attempts to fit all data displayed on the chart within the viewport (`fitContent()`).
```
___



```{py:method} show_data()

Shows the hidden candles on the chart.
```
___



```{py:method} hide_data()

Hides the candles on the chart.
```
___



```{py:method} hotkey(modifier: 'ctrl' | 'alt' | 'shift' | 'meta' | None, key: 'str' | 'int' | 'tuple', func: callable)

Adds a global hotkey to the chart window, which will execute the method or function given.

If multiple key commands are needed for the same function, a tuple can be passed to `key`.
```
___



```{py:method} create_table(width: NUM, height: NUM, headings: Tuple[str], widths: Tuple[float], alignments: Tuple[str], position: FLOAT, draggable: bool, return_clicked_cells: bool, func: callable) -> Table

Creates and returns a [`Table`](https://lightweight-charts-python.readthedocs.io/en/latest/tables.html) object.

```
___



````{py:method} create_subchart(position: FLOAT, width: float, height: float, sync: bool | str, sync_crosshairs_only: bool, scale_candles_only: bool, toolbox: bool) -> AbstractChart 

Creates and returns a Chart object, placing it adjacent to the previous Chart. This allows for the use of multiple chart panels within the same window.

`position`
: specifies how the Subchart will float.

`height` | `width`
: Specifies the size of the Subchart, where `1` is the width/height of the window (100%)

`sync`
: If given as `True`, the Subchart's timescale and crosshair will follow that of the declaring Chart. If a `str` is passed, the Chart will follow the panel with the given id.  Chart ids  can be accessed from the `chart.id` attribute. 

`sync_crosshairs_only`
: If given as `True`, only the crosshairs will be synced and movement will remain independant.

```{important}
`width` and `height` should be given as a number between 0 and 1.
```

Charts are arranged horizontally from left to right. When the available space is no longer sufficient, the subsequent Chart will be positioned on a new row, starting from the left side.

[Subchart examples](../examples/subchart.md)

```{important}
Price axis scales vary depending on the precision of the data used, and there is no way to perfectly 'align' two seperate price scales if they contain differing price data.
```

````
`````

---

## 📊 网格布局与冲突处理

### position 参数详解

`position` 参数支持三种格式：

| 格式 | 示例 | 说明 |
|------|------|------|
| **字符串** | `'left'`, `'right'`, `'top'`, `'bottom'` | 快捷方式，自动转换为对应的网格布局（已弃用） |
| **整数** | `111`, `221`, `311` | 3位数字：`nrows` + `ncols` + `index` |
| **元组** | `(1, 1, 1)`, `(2, 2, 3)` | `(nrows, ncols, index)` |

**字符串到网格的转换规则：**

| 字符串 | 转换结果 | 网格规格 |
|--------|----------|----------|
| `'left'` | `121` | 1行2列，第1个位置 |
| `'right'` | `122` | 1行2列，第2个位置 |
| `'top'` | `211` | 2行1列，第1个位置 |
| `'bottom'` | `212` | 2行1列，第2个位置 |

---

### 网格冲突的触发条件

**当同一窗口中的图表使用不同的网格规格时，会触发 `ValueError` 异常。**

网格规格由 `(nrows, ncols)` 组成，表示布局的行数和列数：

```python
from lightweight_charts import Chart

# 第一个图表使用 2x2 网格
chart1 = Chart(position=221)  

# ❌ 冲突！第二个图表尝试使用 1x2 网格
chart2 = chart1.create_subchart(position=121)  
# ValueError: 网格规格冲突：当前窗口使用 2x2 网格，
# 但尝试创建 1x2 网格的图表。所有图表必须使用相同的网格规格。
```

#### 冲突场景示例

| 第一个图表 | 第二个图表 | 是否冲突 | 原因 |
|-----------|-----------|----------|------|
| `position=221` | `position=222` | ✅ 不冲突 | 同属 2x2 网格 |
| `position=221` | `position=121` | ❌ 冲突 | 2x2 vs 1x2 |
| `position='left'` | `position='right'` | ✅ 不冲突 | 都转换为 1x2 网格 |
| `position='left'` | `position=311` | ❌ 冲突 | 1x2 vs 3x1 |
| `position=(2, 2, 1)` | `position=(2, 2, 4)` | ✅ 不冲突 | 同属 2x2 网格 |

---

### 如何规避网格冲突

#### 方法1：统一使用相同的网格规格

```python
from lightweight_charts import Chart

# 方案：统一使用 2x2 网格
chart = Chart(position=221)           # 2行2列，位置1
subchart_right = chart.create_subchart(position=222)  # 2行2列，位置2
subchart_bottom = chart.create_subchart(position=223) # 2行2列，位置3
subchart_corner = chart.create_subchart(position=224) # 2行2列，位置4
```

#### 方法2：使用宽度/高度参数实现跨列/跨行

```python
from lightweight_charts import Chart

# 创建 2x2 网格布局
chart = Chart(position=221)  # 左上角
subchart_right = chart.create_subchart(position=222)  # 右上角

# bottom 图表跨两列显示
subchart_bottom = chart.create_subchart(
    position=223,  # 左下角位置
    width=2.0      # 宽度设为2.0，横跨两列
)
```

#### 方法3：使用字符串快捷方式（不推荐）

虽然字符串格式会发出弃用警告，但它们会自动转换为相同的网格规格：

```python
from lightweight_charts import Chart

# 'left' 和 'right' 都转换为 1x2 网格，不会冲突
chart_left = Chart(position='left')
chart_right = chart_left.create_subchart(position='right')  # ✅ 不冲突
```

---

### 复杂布局示例

#### 示例1：3图表布局（2行2列，底部跨列）

```python
from lightweight_charts import Chart

# 2x2 网格布局
chart = Chart(position=221, width=1200, height=800)  # 左上角
subchart_right = chart.create_subchart(position=222)  # 右上角

# 底部图表横跨两列
subchart_bottom = chart.create_subchart(
    position=223,
    width=2.0  # 跨两列
)
```

#### 示例2：垂直排列（3行1列）

```python
from lightweight_charts import Chart

# 3行1列布局
chart_top = Chart(position=311)      # 顶部
chart_middle = chart_top.create_subchart(position=312)  # 中间
chart_bottom = chart_top.create_subchart(position=313)  # 底部
```

#### 示例3：水平排列（1行3列）

```python
from lightweight_charts import Chart

# 1行3列布局
chart_left = Chart(position=131)     # 左侧
chart_middle = chart_left.create_subchart(position=132)  # 中间
chart_right = chart_left.create_subchart(position=133)   # 右侧
```

---

### 错误处理建议

```python
from lightweight_charts import Chart

chart = Chart(position=221)

try:
    subchart = chart.create_subchart(position=121)
except ValueError as e:
    print(f"⚠️  创建子图表失败: {e}")
    # 使用正确的规格重新创建
    subchart = chart.create_subchart(position=222)
```

---

### 关键要点

1. **同一窗口所有图表必须使用相同的网格规格**（`nrows` 和 `ncols` 必须相同）
2. **位置索引 `index` 可以不同**，表示在网格中的不同位置
3. **使用 `width` 和 `height` 参数**可以实现跨列/跨行布局
4. **字符串格式已弃用**，建议使用数字或元组格式
5. **冲突会立即抛出 `ValueError`**，需要在代码中处理或避免
