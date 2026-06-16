# 📊lightweight-charts-python

# [MIT License](LICENSE)

![cover1](images/29_grid_layout.png)
![cover2](images/12_audit.png)

**lightweight-charts-python** is dedicated to providing a simple, Pythonic way to access TradingView's Lightweight Charts.

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


## 📓 Updates and Enhancements

Below is the consolidated and optimized Markdown version, retaining all information with ordered lists and emojis for a clear, readable structure:

1. ✅ **Series Batch Update API** — `Line.update_batch()` / `Histogram.update_batch()` updates multiple data points at once, significantly improving performance
2. 🚀 **K-line Batch Update** — `chart.update_bars()` / `chart.update_from_ticks()` batch data processing acceleration up to 10x
3. 📊 **Open Interest Visualization** — Independent Y-axis scaling for Open Interest, overlaid with volume display
4. 🔄 **Reflex Integration** — `ReflexChart(StaticLWC)` embeds K-line charts in [Reflex](https://reflex.dev) applications; incremental real-time updates via postMessage bridge; JS→Python callback bridge auto-forwards events like crosshair_move to State
5. 🧩 **Initialization Idempotency** — Resolves duplicate chart creation caused by module double-import during Reflex compile/runtime
6. 📚 **Example 26** — Performance comparison demo for Line and Histogram batch updates
7. 📚 **Example 27** — Complete Reflex example (SMA indicator + bar push + crosshair callback), with `clean.ps1` / `run.ps1` scripts
8. 🖥️ **Cross-Process Qt Embedding** — `CrossProcessChart` embeds pywebview chart window into PySide6/PyQt6 QWidget via native handle, supporting borderless mode and window size synchronization, similar to Chrome's multi-process architecture (Windows + Linux/X11)
9. 📚 **Example 28** — CrossProcessChart cross-process embedding into PySide6 QWidget complete demo
10. 🎛️ **Grid Layout System** — `position` parameter supports three formats: integer (e.g., `111`), tuple (e.g., `(2,2,1)`), string (deprecated), similar to matplotlib's subplot
11. 🔧 **Runtime Position Control** — New `get_position()` and `set_position()` methods for dynamic chart position adjustment
12. 📏 **Relative Size Control** — `width`/`height` parameters relative to grid cells, supporting shrink (<1.0) and expansion (>1.0)
13. 📚 **Example 29** — Grid layout complete demo
14. 🔗 **Chart Synchronization** — `create_subchart()` supports multi-chart synchronized timelines and crosshairs
15. 📚 **Example 31** — Chart synchronization complete demo
16. ⚠️ **Grid Conflict Detection** — Automatically detects grid specification conflicts within the same window to prevent layout confusion
17. 🧹 **Code Optimization** — Refactored `parse_position()` and `_convert_string_to_grid()` functions for improved code maintainability
18. 🌊 **Real-time Streaming Updates** — Supports direct K-line updates from tick data
19. 📈 **Multi-Panel Charts** — Create subcharts using `create_subchart()` (works in conjunction with chart synchronization)
20. ✏️ **Toolbox** — Draw trendlines, rectangles, rays, and horizontal lines directly on charts
21. 🎯 **Event System** — Timeframe selector, search, keyboard shortcuts, etc.
22. 📋 **Table Component** — For watchlists, order management, and position management
23. 🔌 **Polygon.io Integration** — Direct market data fetching
24. 🏷️ **Persistent Legend** — OHLC remains visible when mouse moves off the chart
25. 🎨 **Vertical Span Highlighting** — Semi-transparent fill marking date ranges
26. 🧹 **Resource Cleanup API** — `reset()`, `clear_handlers()`, `audit()`, `delete()`
27. 📐 **_PriceLine_ Object** — `create_price_line().delete()`
28. 🗑️ **Table.delete()** — Destroys table and cleans up JS state
29. 🔤 **Human-Readable IDs** — `window.Chart_1`, `window.Line_3`, etc.
30. 📊 **Resource Audit** — `chart.audit(use_js=True)` returns complete TOML format JS variable state
31. ✅ **Comprehensive Cleanup Tests** — `test_cleanup.py` verifies Python + JS leak-free for all resource types
32. 🗂️ **Multiple Chart Instances** — Fully independent chart objects
33. 📑 **HtmlTabChart** — Multi-strategy Tab switching chart, supports strategy switching, trade details, performance metrics (adapted from [smalinin/bn_lightweight-charts-python](https://github.com/smalinin/bn_lightweight-charts-python)'s HtmlChart_BN)
34. 📚 **Example 32** — HtmlTabChart multi-strategy Tab switching complete demo
35. 🔄 **Subchart Content Reset** — `reset_sub()` clears all subchart content (data/lines/markers/drawings/tables/ToolBox/TopBar/Legend/Events/sync/handlers), preserves layout, does not affect other subcharts, reusable after reset
36. 📚 **Example 33** — reset_sub subchart content reset complete demo (4-subchart grid + main chart reset + independent subchart + crosshair sync recovery)
37. 🔗 **`sync_id` Group Sync API (v2.6.0)** — New group-name-based chart synchronization. All `AbstractChart` subclasses uniformly support `sync_id` and `sync_crosshairs_only` parameters

    🧰 **Primary Supported Environments** — PySide6, PyQt6, wxPython

---

## ⚠️ v2.6.0 Breaking Change: Chart Sync API Rewrite

**Old API (v2.5.x and earlier)**: `create_subchart(sync=chart.id)` — Pass the target chart's ID (e.g. `window.Chart_1`) to establish **pair sync** between A↔B. The main chart could not participate in sync (no `sync_id` parameter).

**New API (v2.6.0)**: `create_subchart(sync_id='main')` — Pass any **group name string**. All charts using the same group name automatically sync with each other, no need to know each other's IDs. The main chart joins via `Chart(sync_id='main')`.

```python
# ❌ Old way (v2.5.x) — chain pass chart.id, pair sync
chart = Chart(...)
sub = chart.create_subchart(sync=chart.id)      # pass chart.id
sub2 = chart.create_subchart(sync=chart.id)     # every subchart needs it

# ✅ New way (v2.6.0) — group sync, main chart participates
chart = Chart(..., sync_id='main')              # main chart joins 'main' group
sub = chart.create_subchart(sync_id='main')     # subchart joins same group
sub2 = chart.create_subchart(sync_id='main')    # auto mutual sync
```

**`sync_id` parameter rules**:
| Input | Result |
|-------|--------|
| `'main'` (string) | Join sync group named `'main'` |
| `True` | Converted to string `'True'` as group name |
| `False` / `None` | No sync |
| `123` / `[...]` etc. | Raises `TypeError` |


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
| `chart.update(series)` | Update the last K-line |
| `chart.update_from_tick(tick)` | Update K-line from tick data |
| `chart.marker(text, ...)` | Add price marker |
| `chart.marker_auto_scale(enable)` | Control whether markers participate in price axis scaling |
| `chart.pop(count)` | Remove N data points from the end |
| `chart.create_line(name, ...)` | Create line indicator |
| `chart.create_histogram(name, ...)` | Create histogram indicator |
| `chart.create_subchart(...)` | Create sub-panel |
| `chart.create_price_line(price, ...)` | Create price line |
| `chart.horizontal_line(price, ...)` | Create horizontal line |
| `chart.vertical_span(start, end, ...)` | Create vertical highlight span |
| `chart.get_position()` | Get chart render position (x, y, width, height) in percentages (before or after show) |
| `chart.set_position(x, y, width, height)` | Dynamically set chart render position (before or after show, pass None to reset) |
| `chart.audit(use_js=False)` | Resource audit (Python side) |
| `chart.audit(use_js=True)` | Resource audit (JS side, TOML format) |
| `chart.reset()` | Reset chart to initial state |
| `chart.screenshot(...)` | Screenshot (v5.2.0+ enhancement: supports add_top_layer and include_crosshair) |
| `chart.clear_handlers()` | Clear all event handlers |
| `chart.set_price_format(type, base, precision)` | Set price axis format to avoid floating point precision issues (v5.2.0+) |


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

---


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
        chart.update_from_tick(tick)
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
    chart.update_from_ticks(ticks_df)
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
    chart.marker(time='2024-01-15', position='above', text='Event')
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
    chart.set_price_format(type='base', base=100, precision=2)  # v5.2.0+
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
    line.update_batch(sma_data)  # Batch update series
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
