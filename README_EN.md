# 📊lightweight-charts-python **v3.0** 🚀

# [MIT License](LICENSE)

![cover1](images/29_grid_layout.png)
![cover2](images/12_audit.png)

**lightweight-charts-python v3.0** — A **forked & enhanced version** based on the original v2.1 by the upstream author, with significant feature expansions.

> From the initial fork point (v2.5.1) to **v3.0**, it has undergone **15 sub-version iterations** and **21 days of intensive development**, achieving **~85% core API coverage**.

> ✅ 7 Series types · TimeScaleApi · PriceScaleApi · 40 examples · 8 test suites  
> 📖 [Migration Guide v2.5→v3.0](MIGRATION_v2.5_to_v3.0.md) | [Quick Reference](QUICK_REFERENCE.md) | [Changelog](CHANGELOG.md)

中文版 ReadMe: [README.md](README.md)

---

# 🛠️Attempting to Continue Maintenance
I have relatively limited knowledge of TypeScript and mainly rely on DeepSeek AI for maintenance assistance. After comparing numerous K-line charting libraries, I found lightweight-charts-python to be the only one with sufficient features, strong performance, and easy embedding into Qt UI, with essential features that have real demand. Thus, I'm attempting to continue its maintenance.

Currently, bugs have been mostly eliminated, and all examples have been tested successfully on Windows. The lightweight-charts main library has been updated to v5.2.0, and some v5 new features have been added.

My primary usage environment is Windows + Python 3.13 + PySide6 + WebView. Other environments may have issues.

---

# 🫡Other Active Similar Repositories with Unique New Features Worth Trying (I also referenced their code)

https://github.com/gopalparashar421/lightweight-charts-python  
https://github.com/smalinin/bn_lightweight-charts-python  
https://github.com/EsIstJosh/lightweight-charts-python  


## 🤣 If I were to mention the obvious advantages of my project, it would be the fine-grained resource reclamation added for long-running scenarios, with virtually no memory leaks.
Additionally, there's support for figure-like Grid layout, making layout adjustments easier and more precise. There's also a batch update API that supports multiple data points at once, significantly improving batch update performance.

Other repositories are also welcome to use the code as needed.

# ⬇️ More example galleries below

---


## 🚀 New Features / Changes / Enhancements vs. Original v2.1

> The list below compares this forked version against the original upstream v2.1.

### 🔄 Architecture Changes

| Change | Original v2.1 | This Fork v3.0 | Notes |
|--------|---------------|----------------|-------|
| Composition | CandleSeries with attached volume/OI | Volume/OI independent, AbstractChart manages | Auto-rebuild after reset |
| Series management | `candle.attach_volume()` | `chart.volume` / `chart.oi` auto-managed | Set-and-forget |
| Input columns | Inconsistent across series | Unified `time` + `value` | Standardized column names |
| normal_df | Auto lowercase + date→time | No auto conversion | Column names must match exactly |
| Sync | `sync=chart.id` pair sync | `sync_id='group'` group sync | Main chart can also sync |
| `_lines` linking | `chart.set()` auto-fills lines | No auto-forward to _lines | Manual `line.set(df)` required |

### 📝 API Renames

| Original v2.1 | This Fork v3.0 | Notes |
|---------------|----------------|-------|
| `marker()` | `add_marker()` | Add single marker |
| `markers()` | `add_markers()` | Batch add markers |
| `markers` (method) | `markers` (property) | Use `chart.markers` to view marker list |
| `update()` | `update_bar()` | Single bar update |
| `update_from_tick()` | `update_tick()` | Single tick update |
| `update_from_ticks()` | `update_ticks()` | Batch tick update |
| `Line` / `Histogram` class | `LineSeries` / `HistogramSeries` | Unified naming |
| `toolbox.save_drawings_under()` | `toolbox.on_change += func` | Callback registration |
| `price_scale(perm_width=N)` | Removed | No replacement |

---

### ✨ New Features

#### New Series Types
- **AreaSeries** — Area chart (line + gradient fill)
- **OHLCBarSeries** — OHLC bar chart
- **BaselineSeries** — Baseline chart (split color above/below)
- **CandleSeries** — Independent K-line series (any pane, no volume/OI)

#### New APIs
- **TimeScaleApi** — `chart.time_scale_api()` full time axis control (14 methods)
- **PriceScaleApi** — `chart.price_scale_api(scale_id)` full price axis control (6 methods)
- **`chart.fit()` / `chart.set_visible_range()`** — View control
- **`chart.show(wait=N)`** — Auto-close after N seconds
- **`chart.chart_options()`** — Advanced chart options

#### New Chart Types
- **HtmlTabChart** — Multi-strategy Tab switching, init snapshot replay
- **CrossProcessChart** — Cross-process Qt embedding (Windows + Linux/X11)
- **ReflexChart** — Reflex framework embedding
- **HTMLChart / JupyterChart / StreamlitChart / QtChart / WxChart** — Multiple embedding options

#### Drawing System
- **ToolBox Cross-Pane Drawing** — Auto-detect target pane
- **Pane Primitive Architecture** — Drawing attaches directly to pane
- **ToolBox on_change Callback** — `+=` / `-=` register/unregister
- **DrawingInfo Enhanced** — Added pane_index/time/price fields
- **Legend OHLC Support** — Bar/Candlestick shows O H L C
- **Legend Grouping** — Group toggle for one-click visibility

#### Batch & Performance
- **`update_bars(df)`** — Batch OHLCV incremental update
- **`update_ticks(df)`** — Batch tick incremental update
- **`update_bars()` for Line/Histogram** — Series batch update
- **Message loop exception protection** — Single message failure won't crash

#### Other Enhancements
- **Histogram Per-Bar Colors** — Independent coloring via `color` column
- **reset_sub()** — Subchart content reset, layout preserved
- **Grid Layout System** — `position` parameter: integer/tuple formats
- **Runtime Position Control** — `get_position()` / `set_position()`
- **8 Test Suites** — Resource cleanup / features / data aggregation / position / etc.
- **40 Examples** — From basic to advanced cross-pane drawing
- **Fine-grained resource reclamation** — Near zero memory leaks in long runs
- **`_remove_my_handlers()`** — Precise handler cleanup, multi-chart safe

> 🧰 **Primary Supported Environments** — PySide6, PyQt6, wxPython

---

## ⚠️ Breaking Changes (v2.5.1 → v3.0)

> v3.0 is the first official major release. All breaking changes are consolidated below.  
> See the complete [Migration Guide v2.5→v3.0](MIGRATION_v2.5_to_v3.0.md) for step-by-step migration and verification checklist.

### Sync: `sync=chart.id` → `sync_id='group'`

```python
# ❌ Old way — pair sync via chart.id
chart = Chart(...)
sub = chart.create_subchart(sync=chart.id)

# ✅ New way — group sync, main chart participates
chart = Chart(..., sync_id='main')
sub = chart.create_subchart(sync_id='main')
```

### Function Renames

| Old Name | New Name |
|----------|----------|
| `update_from_tick()` | `update_tick()` |
| `update_from_ticks()` | `update_ticks()` |
| `update()` / `update_bar()` | Unified `update_bar()` / `update_bars()` |
| `marker()` | `add_marker()` |
| `markers()` | `add_markers()` |
| `markers` (method) | `markers` (property) |
| `Line` / `Histogram` class | `LineSeries` / `HistogramSeries` |

### AbstractChart no longer auto-fills _lines

`chart.set(df)` no longer forwards data to Line/Histogram series. Manual `line.set(df)` required.

### normal_df: no auto lowercase or date→time

Column names must match exactly (`time`, `open`, `high`, `low`, `close`, `value`).

### VolumeSeries / OI use `value` column

Use `value` column directly. Auto-forwarded when calling through `chart.set()`.

### Removed Parameters

| Parameter | Notes |
|-----------|-------|
| `price_scale(perm_width=N)` | Removed, no replacement |
| `cumulative_volume` | Removed, VolumeSeries auto-sums |
| `toolbox.save_drawings_under()` | Replace with `toolbox.on_change += func` |
| `toolbox.load_drawings()` etc. | Removed, use `on_change` |


---

# 🤖Suggestion: Let AI Programming Assistants Read QUICK_REFERENCE.md First for Quick Project Overview

---

# Installation with PYPI

```bash
pip install lightweight-charts-onesixth
```

# Installation with Source Code

```bash
pip install https://github.com/One-sixth/lightweight-charts-python
```

# Building

Building this package requires a Node.js environment with npm commands available.

First, build the JS bundle library.

### Download Node Package Dependencies
```
npm install @rollup/plugin-typescript --save-dev
npm audit fix --force
```

### Build and Copy Artifacts to Python Source Directory
```
npx rollup -c rollup.config.js
cp dist/bundle.js lightweight_charts/js/bundle.js
```

### Build Wheel Package
```
python -m build
```

The built wheel package will be in the dist directory.

---


## Core API Quick Reference

| Method | Description |
|--------|-------------|
| `chart.set(df)` | Set K-line data |
| `chart.update_bar(series)` | Update the last K-line |
| `chart.update_tick(series)` | Update K-line from tick data |
| `chart.add_marker(time, ...)` | Add price marker |
| `chart.marker_auto_scale(enable)` | Control whether markers participate in price axis scaling |
| `chart.pop(count)` | Remove N data points from the end |
| `chart.create_line(name, ...)` | Create line indicator (returns LineSeries) |
| `chart.create_histogram(name, ...)` | Create histogram indicator (returns HistogramSeries) |
| `chart.create_area_series(name, ...)` | Create area series |
| `chart.create_ohlc_bar_series(name, ...)` | Create OHLC bar series |
| `chart.create_baseline_series(name, ...)` | Create baseline series |
| `chart.create_subchart(...)` | Create sub-panel |
| `chart.create_price_line(price, ...)` | Create price line |
| `chart.horizontal_line(price, ...)` | Create horizontal line |
| `chart.vertical_span(start, end, ...)` | Create vertical highlight span |
| `chart.get_position()` | Get chart render position (x, y, width, height) |
| `chart.set_position(x, y, width, height)` | Dynamically set chart render position |
| `chart.audit(use_js=False)` | Resource audit (Python side) |
| `chart.audit(use_js=True)` | Resource audit (JS side, TOML format) |
| `chart.reset()` | Reset chart to initial state |
| `chart.screenshot(...)` | Screenshot (supports add_top_layer and include_crosshair) |
| `chart.price_scale(price_format=...)` | Configure price scale |
| `chart.time_scale_api()` | Time axis API (scroll/range/event subscription) |
| `chart.price_scale_api(scale_id)` | Price axis API (options/range/size) |

---

## 🎯 Advanced API: TimeScaleApi & PriceScaleApi

For basic usage (configuration, data setting), the Python functions above are sufficient.  
For **event callbacks** or **finer control**, use these APIs:

```python
# Time Scale API
chart.time_scale_api().scroll_to_real_time()
chart.time_scale_api().subscribe_visible_logical_range_change(handler)

# Price Scale API (default: right)
chart.price_scale_api().width()
chart.price_scale_api().set_auto_scale(True)

# Price Scale API (specified: left)
chart.price_scale_api('left').apply_options(scale_margin_top=0.1)
```

| API | Method | Description |
|-----|--------|-------------|
| **TimeScaleApi** | `scroll_position()` | Get scroll position |
| | `scroll_to_position(pos)` | Scroll to position |
| | `scroll_to_real_time()` | Scroll to real-time data |
| | `fit_content()` | Fit data to viewport |
| | `get_visible_range()` | Get visible range |
| | `set_visible_range(range)` | Set visible range |
| | `width()` | Get width |
| | `subscribe_visible_logical_range_change(handler)` | **Subscribe to logical range change** |
| | `subscribe_visible_time_range_change(handler)` | **Subscribe to time range change** |
| | `subscribe_size_change(handler)` | **Subscribe to size change** |
| **PriceScaleApi** | `apply_options(**kwargs)` | Apply options |
| | `options()` | Get options |
| | `width()` | Get width |
| | `set_auto_scale(on)` | Set auto scale |

> 📖 See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) sections 3.8.1 and 3.8.2

---

## Documentation and Support

Learning through examples is recommended. There is extensive reference code and galleries below in the README. For complete functionality, refer to the QUICK_REFERENCE.md file, which I've tried to include detailed explanations and example code for all features.

---

**Disclaimer:** This package is independently developed and is not endorsed, sponsored, or approved by TradingView. The author has no official relationship with TradingView, and this package does not represent TradingView's views or positions.

---

## Complete Example Directory

| No. | Example Name | Description |
|-----|--------------|-------------|
| 1 | `1_setting_data` | Basic data setup |
| 2 | `2_live_data` | Real-time K-line updates |
| 3 | `3_tick_data` | Tick data updates |
| 4 | `4_line_indicators` | Line indicator SMA |
| 5 | `5_styling` | Style customization |
| 6 | `6_callbacks` | Callback events |
| 7 | `7_multi_pane` | Multi-panel charts |
| 8 | `8_volume_open_interest` | Volume + Open Interest |
| 9 | `9_multi_chart` | Multiple Chart instances |
| 10 | `10_persistent_legend` | Persistent legend |
| 11 | `11_vertical_span` | Vertical span highlighting |
| 12 | `12_audit` | Resource audit |
| 13 | `13_batch_update` | Batch update API |
| 14 | `14_set_period` | Time period locking |
| 15 | `15_pyside6_simple` | PySide6 integration |
| 16 | `16_pyside6_race` | PySide6 performance test |
| 18 | `18_hovered_series_on_top` | Hovered series on top |
| 19 | `19_timescale_options` | Timescale options |
| 20 | `20_tick_mark_density` | Tick mark density control |
| 21 | `21_marker_auto_scale` | Marker auto-scale |
| 22 | `22_pop` | Remove data points |
| 23 | `23_crosshair_move` | Crosshair move event |
| 24 | `24_price_format` | Price format settings |
| 25 | `25_screenshot_enhanced` | Enhanced screenshot |
| 26 | `26_series_batch_update` | Series batch update |
| 27 | `27_reflex_chart` | Reflex integration |
| 28 | `28_cross_process_chart` | Cross-process Qt embedding |
| 29 | `29_grid_layout` | Grid layout system |
| 30 | `30_table_component` | Table component (watchlist/position management) |
| 31 | `31_chart_sync` | Chart synchronization (timeline + crosshair) |
| 32 | `32_html_tab_chart` | HtmlTabChart multi-strategy Tab switching |
| 33 | `33_reset_sub` | reset_sub subchart content reset |
| 34 | `34_candle_series` | CandleSeries independent K-line series |
| 35 | `35_line_markers` | Line / Histogram series markers |
| 36 | `36_histogram_colors` | Histogram arbitrary per-bar colors |
| 37 | `37_more_series_types` | AreaSeries / OHLCBarSeries / BaselineSeries |
| 38 | `38_drawing_multi_pane` | Cross-pane Drawing distribution |
| 39 | `39_legend_group` | Legend grouping: group toggle + individual switches |
| 40 | `40_toolbox_multi_pane` | ToolBox cross-pane drawing: 3 pane demo |

> **Total: 40 examples** (v3.0)


## Example Screenshots

> **Below are screenshot locations for all examples, replace images based on actual results**

### Example 1: Displaying CSV Data

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    df = pd.read_csv('ohlcv.csv')
    chart.set(df)
    chart.show(block=True)
```

![Displaying CSV Data](images/1_setting_data.png)

---

### Example 2: Real-time K-line Updates

```python
import pandas as pd
from time import sleep
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    df1 = pd.read_csv('ohlcv.csv')
    df2 = pd.read_csv('next_ohlcv.csv')
    chart.set(df1)
    chart.show()
    for _, bar in df2.iterrows():
        chart.update(bar)
        sleep(0.1)
```

![Real-time K-line Updates](images/2_live_data.gif)

---

### Example 3: Updating from Tick Data

```python
import pandas as pd
from time import sleep
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.set(pd.read_csv('ohlc.csv'))
    chart.show()
    for _, tick in pd.read_csv('ticks.csv').iterrows():
        chart.update_tick(tick)
        sleep(0.03)
```

![Tick Data Updates](images/3_tick_data.gif)

---

### Example 4: Line Indicator (SMA)

```python
import pandas as pd
from lightweight_charts import Chart

def calculate_sma(df, period=50):
    return pd.DataFrame({
        'time': df['date'],
        f'SMA {period}': df['close'].rolling(period).mean()
    }).dropna()

if __name__ == '__main__':
    chart = Chart()
    df = pd.read_csv('ohlcv.csv')
    chart.set(df)
    line = chart.create_line('SMA 50')
    line.set(calculate_sma(df, 50))
    chart.show(block=True)
```

![Line Indicator](images/4_line_indicators.png)

---

### Example 5: Style Customization

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    df = pd.read_csv('ohlcv.csv')
    chart.layout(background_color='#090008', text_color='#FFFFFF')
    chart.candle_style(up_color='#00ff55', down_color='#ed4807')
    chart.watermark('1D', color='rgba(180,180,240,0.7)')
    chart.set(df)
    chart.show(block=True)
```

![Style Customization](images/5_styling.png)

---

### Example 6: Callback Events

```python
import pandas as pd
from lightweight_charts import Chart

def on_search(chart, searched_string):
    new_data = get_bar_data(searched_string, chart.topbar['timeframe'].value)
    if not new_data.empty:
        chart.topbar['symbol'].set(searched_string)
        chart.set(new_data)

if __name__ == '__main__':
    chart = Chart(toolbox=True)
    chart.events.search += on_search
    chart.topbar.textbox('symbol', 'TSLA')
    chart.topbar.switcher('timeframe', ('1min', '5min', '30min'))
    chart.set(get_bar_data('TSLA', '5min'))
    chart.show(block=True)
```

![Callback Events](images/6_callbacks.gif)

---

### Example 7: Multi-Panel Charts

```python
import pandas as pd
from lightweight_charts import HTMLChart

def demo():
    chart = HTMLChart(
        width=1200, height=800,
        position=111,                   # Chart position (grid format)
        pane_index=0,                   # Panel index
        marker_auto_scale=True          # Whether markers auto-scale
    )
    df = pd.read_csv('ohlcv.csv')
    chart.set(df)
    line7 = chart.create_line('SMA 7', color='red')
    line7.set(df[['date', 'close']].rename(columns={'close': 'SMA 7'}))
    chart.show()

if __name__ == '__main__':
    demo()
```

![Multi-Panel Charts](images/7_multi_pane.png)

---

### Example 8: Volume + Open Interest

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart(toolbox=True)
    df = generate_data()  # Contains open_interest column
    chart.set(df)
    chart.show(block=True)
```

![Volume and Open Interest](images/8_volume_open_interest.png)

---

### Example 9: Multiple Chart Instances

```python
import asyncio
from threading import Thread
from lightweight_charts import Chart

def run_chart(chart):
    asyncio.run(chart.show_async())

if __name__ == '__main__':
    chart1 = Chart(title='AAPL')
    chart2 = Chart(title='TSLA')
    chart1.set(df1)
    chart2.set(df2)
    t1 = Thread(target=run_chart, args=(chart1,), daemon=True)
    t2 = Thread(target=run_chart, args=(chart2,), daemon=True)
    t1.start()
    t2.start()
```

![Multiple Chart Instances](images/9_multi_chart.png)

---

### Example 10: Persistent Legend

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    df = generate_data()
    chart.legend(visible=True, ohlc=True, persistent=True)
    chart.set(df)
    chart.show(block=True)
```

![Persistent Legend](images/10_persistent_legend.png)

---

### Example 11: Vertical Span Highlighting

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    df = pd.read_csv('ohlcv.csv')
    chart.set(df)
    chart.vertical_span(start_time='2024-01-05', end_time='2024-06-10', color='rgba(252,219,3,0.15)')
    chart.show(block=True)
```

![Vertical Span Highlighting](images/11_vertical_span.png)

---

### Example 12: Resource Audit

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart(toolbox=True)
    chart.set(df)
    # Create various resources...
    result = chart.audit(use_js=True)  # JS side state check
    print(result)
    chart.show(block=True)
```

![Resource Audit](images/12_audit.png)

---

### Example 13: Batch Update

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.set(initial_df)
    chart.show()
    # Batch update
    chart.update_bars(new_bars_df)
    chart.update_ticks(ticks_df)
```

![Batch Update](images/13_batch_update.png)

---

### Example 14: Time Period Locking

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.set(df_5min)
    chart.set_period(3600)  # Lock to 1 hour
    chart.set(df_30min)  # Important: need to call set() again after set_period() to take effect, still displayed at 1 hour
    chart.show(block=True)
```

![Time Period Locking](images/14_set_period.png)

---

### Example 15: PySide6 Integration

```python
import sys
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from lightweight_charts.widgets import QtChart

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.chart = QtChart()
        layout = QVBoxLayout()
        layout.addWidget(self.chart.get_webview())
        self.chart.set(df)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

![PySide6 Integration](images/15_pyside6_simple.png)

---

### Example 16: PySide6 Performance Test

```python
import sys
from PySide6.QtWidgets import QMainWindow
from lightweight_charts.widgets import QtChart

class SpeedRaceWindow(QMainWindow):
    def run_batch_race(self):
        start = time.perf_counter()
        self.chart.update_bars(new_bars)
        elapsed = time.perf_counter() - start
        print(f'update_bars: {elapsed:.4f}s')
```

![PySide6 Performance Test](images/16_pyside6_race.png)

---

### Example 18: Hovered Series on Top

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.chart_options(hovered_series_on_top=True)  # v5.2.0+
    chart.set(df)
    chart.show(block=True)
```

![Hovered Series on Top](images/18_hovered_series_on_top.png)

---

### Example 19: Timescale Options

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.time_scale(
        right_offset_pixels=50,
        enable_conflation=True,
        precompute_conflation_on_init=True
    )
    chart.set(large_df)
    chart.show(block=True)
```

![Timescale Options](images/19_timescale_options.png)

---

### Example 20: Tick Mark Density Control

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.price_scale(tick_mark_density=2.5)  # v5.2.0+
    chart.set(df)
    chart.show(block=True)
```

![Tick Mark Density Control](images/20_tick_mark_density.png)

---

### Example 21: Marker Auto-Scale

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart(marker_auto_scale=False)
    chart.set(df)
    chart.add_marker(time='2024-01-15', position='above', text='Event')
    chart.show(block=True)
```

![Marker Auto-Scale](images/21_marker_auto_scale.png)

---

### Example 22: Remove Data Points

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.set(df)
    chart.pop(50)  # Remove last 50 data points
    chart.show(block=True)
```

![Remove Data Points](images/22_pop.png)

---

### Example 23: Crosshair Move Event

```python
def on_crosshair_move(chart, payload):
    dt = pd.to_datetime(payload['time'], unit='s')
    print(f'{dt} | price = {payload.get("price")}')

if __name__ == '__main__':
    chart = Chart()
    chart.events.crosshair_move += on_crosshair_move
    chart.set(df)
    chart.show(block=True)
```

![Crosshair Move Event](images/23_crosshair_move.png)

---

### Example 24: Price Format Settings

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.set(df)
    chart.price_scale(price_format={'type': 'base', 'base': 100, 'precision': 2})
    chart.show(block=True)
```

![Price Format Settings](images/24_price_format.png)

---

### Example 25: Enhanced Screenshot

```python
from lightweight_charts import Chart
import time

if __name__ == '__main__':
    chart = Chart()
    chart.set(df)
    chart.watermark('Screenshot Demo')
    chart.show(block=False)
    time.sleep(2)
    img = chart.screenshot(add_top_layer=True, include_crosshair=True)
    with open('screenshot.png', 'wb') as f:
        f.write(img)
```

![Enhanced Screenshot](images/25_screenshot_enhanced.png)

---

### Example 26: Series Batch Update

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.set(df)
    line = chart.create_line('SMA 20')
    line.update_bars(sma_data)  # Batch update series
    chart.show(block=True)
```

![Series Batch Update](images/26_series_batch_update.png)

---

### Example 27: Reflex Integration

```python
import reflex as rx
from lightweight_charts import ReflexChart

chart = ReflexChart(width=1000, height=600, auto_flush=True)
chart.set(pd.read_csv('ohlcv.csv'))

class ChartState(rx.State):
    def tick(self):
        chart.update(_next_bar())
        return chart.flush()
```

![Reflex Integration](images/27_reflex_chart.png)

---

### Example 28: Cross-Process Qt Embedding

```python
from PySide6.QtWidgets import QMainWindow
from lightweight_charts import CrossProcessChart

class MainWindow(QMainWindow):
    def __init__(self):
        self.chart = CrossProcessChart(parent=self, width=800, height=500)
        self.chart.set(df)
```

![Cross-Process Qt Embedding](images/28_cross_process_chart.png)

---

### Example 29: Grid Layout

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart1 = Chart(position=221)  # 2 rows, 2 columns, position 1
    chart2 = chart1.create_subchart(position=222)
    chart3 = chart1.create_subchart(position=223)
    chart4 = chart1.create_subchart(position=224)
    chart1.set(df)
    chart1.show(block=True)
```

![Grid Layout](images/29_grid_layout.png)

---

### Example 30: Table Component

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart(width=1000, height=600)
    chart.set(df)
    
    # Create watchlist table
    watchlist = chart.create_table(
        width=0.22,
        height=0.4,
        headings=('Symbol', 'Price', 'Chg%', 'Volume'),
        widths=(0.35, 0.25, 0.2, 0.2),
        alignments=('left', 'right', 'right', 'right'),
        position=(0.02, 0.1),  # Use relative coordinates (x, y), range 0-1
        draggable=True,
        func=on_watchlist_click
    )
    
    # Add data
    watchlist.new_row('AAPL', '198.50', '+1.2%', '12.5M')
    watchlist.new_row('GOOGL', '141.80', '-0.8%', '8.2M')
    watchlist.new_row('MSFT', '420.30', '+2.1%', '15.8M')
    
    # Set styles
    watchlist.header(color='rgba(70, 130, 180, 0.8)', text_color='#FFFFFF')
    watchlist.rows[0].background_color('rgba(0, 255, 0, 0.1)')
    
    chart.show(block=True)
```

**Position Parameter Description:**

| Format | Example | Description |
|--------|---------|-------------|
| Tuple (x, y) | `(0.02, 0.1)` | Recommended: relative coordinates, range 0-1 |
| Tuple (x, y) | `(100, 50)` | Pixel coordinates, values >= 1 are treated as pixels |
| String (deprecated) | `'left'`, `'right'` | Not recommended, triggers DeprecationWarning, equivalent to `(0, 0)` |

![Table Component](images/30_table_component.png)

---

### Example 31: Chart Synchronization

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    # Create main chart - using 2x2 grid layout
    chart = Chart(width=1200, height=800, title='Chart Sync Demo', position=(2, 2, 1))
    
    # Create right subchart (fully synchronized timeline and crosshair)
    subchart_right = chart.create_subchart(
        position=(2, 2, 2),
        sync_id=chart.id,           # Sync to main chart
        sync_crosshairs_only=False  # Full synchronization
    )
    
    # Create bottom subchart (crosshair sync only)
    subchart_bottom = chart.create_subchart(
        position=223,            # Equivalent to (2, 2, 3)
        width=2.0,               # Span two columns
        sync_id=chart.id,
        sync_crosshairs_only=True  # Crosshair sync only
    )
    
    chart.set(df)
    subchart_right.set(df2)
    subchart_bottom.set(df3)
    chart.show(block=True)
```

**Sync Parameter Description:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `sync_id` | `bool` or `str` | `True` syncs to parent chart; string is the target chart's id |
| `sync_crosshairs_only` | `bool` | `True` syncs only crosshair, timeline remains independent |

![Chart Synchronization](images/31_chart_sync.png)

---

### Example 32: HtmlTabChart (Multi-Strategy Tab Switching)

```python
from lightweight_charts import HtmlTabChart

chart = HtmlTabChart(width=1200, height=800)

# Strategy 1: Moving Average Crossover
chart.set_name('MA Crossover')
chart.set(df1)
chart.set_trades(trades1)
chart.set_performance_metrics(perf1, 'MA Crossover')
chart.set_parameters_list(params1)
chart.new_window()  # Switch to next strategy

# Strategy 2: Bollinger Bands
chart.set_name('Bollinger Bands')
chart.set(df2)
chart.set_trades(trades2)
chart.set_performance_metrics(perf2, 'Bollinger Bands')
chart.set_parameters_list(params2)

chart.export('multi_charts.html')
```

**HtmlTabChart Features:**

| Feature | Description |
|---------|-------------|
| Multi-strategy switching | Switch between different strategies via sidebar |
| Technical indicators | Support SMA, Bollinger Bands, etc. |
| Trade markers | Open/Close position arrows |
| Trade details | Table showing trade records, double-click to jump |
| Performance metrics | Sharpe ratio, max drawdown, win rate, etc. |
| Strategy parameters | Display configuration for each strategy |
| Legend display | Show all indicator names in top-left corner |

> Adapted from [smalinin/bn_lightweight-charts-python](https://github.com/smalinin/bn_lightweight-charts-python)'s HtmlChart_BN

![HtmlTabChart](images/32_html_tab_chart.png)

---

### Example 33: reset_sub (Subchart Content Reset)

```python
from lightweight_charts import Chart

chart = Chart(width=1400, height=900, position=(2,2,1), toolbox=True)
sub_a = chart.create_subchart(position=(2,2,2), toolbox=True, sync_id=chart.id)
sub_b = chart.create_subchart(position=(2,2,3), sync_id=chart.id)
sub_c = chart.create_subchart(position=(2,2,4), toolbox=True)  # Independent

# Populate data
chart.set(bars_main); sub_a.set(bars_a); sub_b.set(bars_b); sub_c.set(bars_c)

# reset sub_b → clears all content, preserves layout
sub_b.reset_sub()

# Re-populate → subchart is reusable
sub_b.set(new_bars)

# reset main chart → other subcharts unaffected
chart.reset_sub()
chart.set(new_bars)
```

**reset_sub Scope:**

| Resource | Cleanup Method |
|----------|---------------|
| OHLCV data | `clear_data()` |
| Line/Histogram series | `Line.delete()` / `Histogram.delete()` |
| Price lines | `PriceLine.delete()` |
| Markers | `clear_markers()` |
| Drawings | `Drawing.delete()` |
| Tables | `Table.delete()` |
| ToolBox | DrawingTool events + ContextMenu + commandFunction + DOM |
| TopBar | Widget callbacks + DOM |
| Legend | crosshair subscription + DOM |
| Events | JSEmitter subscriptions |
| syncCharts | Bidirectional disassociation + rebuild |
| handlers | Salt-matched cleanup |

> After reset, subchart can be re-populated. Crosshair and timeline sync auto-recover.

![reset_sub](images/33_reset_sub.gif)

---

### Example 34: CandleSeries (Independent K-line Series)

```python
import pandas as pd
from lightweight_charts import Chart

# Main K-line
chart = Chart(width=1400, height=900)
chart.set(df_main)

# Reference K-line (independent pane)
ref = chart.create_candle_series(
    name='Reference',
    pane_index=1,
    up_color='rgba(0, 150, 255, 0.8)',
    down_color='rgba(255, 100, 0, 0.8)',
)
ref.set(df_reference)       # Initial data
ref.update_bar(new_bar)         # Update/append
ref.update_bars(df_more)   # Batch append
ref.add_marker(...)             # Add marker

chart.show(block=True)
```

**CandleSeries Features:**

| Feature | Description |
|---------|-------------|
| `create_candle_series()` | Create independent K-line (no volume/open interest) |
| `set(df)` | Set initial OHLC data |
| `update_bar(series)` | Update latest bar or append new bar |
| `update_bars(df)` | Batch update multiple bars |
| `add_marker(...)` | Add markers on independent K-line |
| `delete()` | Delete series and clean up JS object |
| `pane_index` | Control which pane to render in |

> Independent K-lines are useful for reference/comparison K-lines, supporting crosshair sync with the main K-line.

![CandleSeries](images/34_candle_series.png)

---

### Example 35: Line / Histogram Series Markers

```python
from lightweight_charts import Chart

chart = Chart(width=1200, height=700, title='Line Series Markers Demo')
chart.set(candle_df)

# Markers on Line series
line20 = chart.create_line('SMA20', color='#2196F3', width=2)
line20.set(sma20)
line20.add_marker(dates[25], 'below', 'circle', '#2196F3', 'SMA20 Cross')

# Markers on Histogram series
hist = chart.create_histogram('Volume', color='rgba(100,100,200,0.5)', pane_index=1)
hist.set(vol_df)
hist.add_marker(dates[5], 'below', 'circle', '#9C27B0', 'Vol Spike')

# Batch markers on Line
line20.add_markers([
    {'time': dates[35], 'position': 'below', 'shape': 'arrow_up', 'color': '#00BCD4', 'text': 'Batch 1'},
    {'time': dates[45], 'position': 'above', 'shape': 'arrow_down', 'color': '#00BCD4', 'text': 'Batch 2'},
])

chart.show(block=True)
```

**Supported Series for Markers:**

| Series | add_marker() | add_markers() |
|--------|----------|-----------|
| CandleSeries (main K-line) | ✅ | ✅ |
| LineSeries (line) | ✅ | ✅ |
| HistogramSeries (histogram) | ✅ | ✅ |

![Line Series Markers](images/35_line_markers.png)

---

### Example 36: Histogram Arbitrary Colors (per-bar coloring)

```python
from lightweight_charts import Chart

chart = Chart(width=1200, height=700, title='Histogram Custom Colors Demo')
chart.set(candle_df)

# DataFrame with color column — each bar gets its own color
delta_df = pd.DataFrame({
    'time': dates,
    'value': delta,          # positive = buyer dominant, negative = seller dominant
    'color': colors,         # one color per bar
})

hist = chart.create_histogram(
    name='Volume Delta',
    color='rgba(100,200,100,0.5)',
    pane_index=1,
)
# Note: chart.set() does NOT forward the color column — histogram must be set separately
hist.set(delta_df)

chart.show(block=True)
```

**Per-bar Coloring Key Points:**

| Point | Description |
|-------|-------------|
| `color` column | Include a `color` column in DataFrame for automatic per-bar coloring |
| `chart.set()` | Does NOT forward `color` column — histogram must call `set()` separately |
| Positive/Negative values | Supports bidirectional coloring (e.g., Volume Delta: buyer→warm, seller→cool) |

![Histogram Colors](images/36_histogram_colors.png)

---

### Example 37: New Series Types (Area / OHLC Bar / Baseline)

```python
from lightweight_charts import Chart

chart = Chart(width=1200, height=800, title='New Series Types Demo')
chart.set(df)

# 1. AreaSeries — line + gradient fill
area = chart.create_area_series(
    name='SMA 20 (Area)',
    color='#2196F3',
    top_color='rgba(33, 150, 243, 0.35)',
    bottom_color='rgba(33, 150, 243, 0.0)',
)
area.set(sma20_df)

# 2. OHLCBarSeries — OHLC horizontal bars
ohlc_bar = chart.create_ohlc_bar_series(
    name='OHLC Bar',
    up_color='#26A69A',
    down_color='#EF5350',
    pane_index=1,
)
ohlc_bar.set(df)

# 3. BaselineSeries — baseline with two-tone coloring
baseline = chart.create_baseline_series(
    name='RSI Deviation',
    baseline_value=0,
    topLineColor='#26A69A',
    bottomLineColor='#EF5350',
    pane_index=2,
)
baseline.set(rsi_df)

chart.show(block=True)
```

**New Series Types:**

| Type | Factory Method | Use Case |
|------|---------------|----------|
| AreaSeries | `create_area_series()` | Area chart: trend fill for MA, volatility, etc. |
| OHLCBarSeries | `create_ohlc_bar_series()` | OHLC bars: alternative K-line visualization |
| BaselineSeries | `create_baseline_series()` | Baseline: RSI deviation, P&L, zero-axis centered indicators |
| `legend=False` | All series support it | Hide auxiliary series (background bands, helper lines) from legend |

![New Series Types](images/37_more_series_types.png)

---

### Example 38: Cross-Pane Drawing

```python
from lightweight_charts import Chart

# 3-pane drawing demo
chart = Chart(width=1200, height=800, title='Drawing Series Multi-Pane', toolbox=True)
chart.legend(visible=True)
chart.set(df)

# Pane 0: K-line + horizontal line + trend line + Box
chart.horizontal_line(price=200, color='orange', width=2, text='Avg Price')
chart.trend_line(start_time, start_price, end_time, end_price, color='#1E80F0')
chart.box(start_time, start_price, end_time, end_price, color='#E91E63')

# Pane 1: histogram + ray + horizontal line
hist = chart.create_histogram('RSI Dev', pane_index=1)
chart.ray_line(start_time, value=50, color='gray', pane_index=1)
chart.horizontal_line(price=70, color='red', pane_index=1)

# Pane 2: line + vertical line
sma = chart.create_line('SMA 50', pane_index=2)
chart.vertical_line(time=key_time, color='#FF5722', pane_index=2)

chart.show(block=True)
```

![Cross-Pane Drawing](images/38_drawing_multi_pane.png)

---

### Example 39: Legend Grouping

```python
from lightweight_charts import Chart

chart = Chart()
chart.legend(visible=True, ohlc=True, percent=True, lines=True)
chart.set(df)

# group='MA': both MAs in the same legend row
sma20 = chart.create_line('SMA 20', color='yellow', width=1, group='MA')
ema50 = chart.create_line('EMA 50', color='cyan', width=1, group='MA')

# group='MOM': momentum indicators same row
roc = chart.create_line('ROC 10', color='red', width=1, group='MOM')
mom = chart.create_line('MOM 10', color='green', width=1, group='MOM')

# No group: independent row
rsi = chart.create_line('RSI 14', color='purple', pane_index=1)

chart.show(block=True)
```

**Legend Interaction:**
- ♦ **Group toggle**: one-click toggle all series in the group
- 👁 **Eye icon**: toggle individual series, group toggle updates automatically
- Cross-pane group names are supported

![Legend Grouping](images/39_legend_group.png)

---

### Example 40: ToolBox Cross-Pane Drawing

```python
from lightweight_charts import Chart
from lightweight_charts.toolbox import DrawingInfo

chart = Chart(width=1200, height=800, toolbox=True)
chart.set(df)

# 3 panes
sma = chart.create_line('SMA 7', color='red', pane_index=0)
hist = chart.create_histogram('Delta', color='#9B59B6', pane_index=1)
rsi = chart.create_line('RSI', color='#26A69A', pane_index=2)

# Register drawing change callback (auto-includes pane_index)
def on_drawings_change(drawings: list[DrawingInfo]):
    for d in drawings:
        print(f'pane={d.pane_index}  type={d.type}')

chart.toolbox.on_change += on_drawings_change
chart.show(block=True)
```

**Cross-Pane ToolBox:**
- ToolBox UI stays on Pane 0
- Click any pane to draw there
- Callbacks include `pane_index` automatically

![ToolBox Cross-Pane](images/40_toolbox_multi_pane.png)

---
