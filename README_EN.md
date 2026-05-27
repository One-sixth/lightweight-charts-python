# lightweight-charts-python

[MIT License](LICENSE)

![cover1](images/29_grid_layout.png)
![cover2](images/12_audit.png)

**lightweight-charts-python** aims to provide a simple and Pythonic way to access and implement TradingView's Lightweight Charts.

Chinese Version ReadMe: [README.md](README.md)

---

### Trying to Continue Maintenance

I have limited knowledge of TypeScript and primarily rely on DeepSeek AI for assistance with maintenance.
After comparing numerous candlestick charting libraries, I found that lightweight-charts-python is the only library with sufficient functionality, strong performance, and easy Qt UI embedding. Due to essential requirements, I am attempting to continue maintaining this project.

Most bugs have been resolved, and all examples have been tested successfully on Windows.
The main Lightweight Charts library has been updated to v5.2.0, with some new v5 features added.

---

### Recent Updates

**New or Updated Features:**
1. ✅ **Sequence Batch Update API** — `Line.update_batch()` / `Histogram.update_batch()` update multiple data points at once for dramatically improved performance
2. ✅ **Candlestick Batch Update** — `chart.update_bars()` / `chart.update_from_ticks()` batch data processing with 10x speedup
3. ✅ **Open Interest Visualization** — Independent Y-axis scaling, overlay with volume
4. ✅ **Reflex Integration** — `ReflexChart(StaticLWC)` for embedding charts in [Reflex](https://reflex.dev) web apps; incremental live updates via postMessage bridge; JS→Python callback bridge forwarding crosshair_move etc. to State
5. ✅ **Init Idempotency** — Fixes duplicate chart creation caused by Reflex compile/runtime module double-import
6. ✅ **Example 26** — Batch update performance comparison demo for Line and Histogram
7. ✅ **Example 27** — Complete Reflex demo (SMA + bar push + crosshair callback), with `clean.ps1` / `run.ps1` scripts
8. ✅ **Cross-Process Qt Embedding** — `CrossProcessChart` embeds pywebview chart window into PySide6/PyQt6 QWidget via native window handle, with frameless mode and resize sync (Windows + Linux/X11)
9. ✅ **Example 28** — CrossProcessChart cross-process embedding demo
10. ✅ **Grid Layout System** — `position` parameter supports three formats: integer (e.g., `111`), tuple (e.g., `(2,2,1)`), string (deprecated), similar to matplotlib's subplot
11. ✅ **Runtime Position Control** — New `get_position()` and `set_position()` methods for dynamically adjusting chart position
12. ✅ **Relative Size Control** — `width`/`height` parameters relative to grid cell, supporting shrink (<1.0) and expand (>1.0)
13. ✅ **Example 29** — Complete grid layout demo
14. ✅ **Chart Sync** — `create_subchart()` new `sync` parameter (formerly `sync_id`), supports timeline and crosshair synchronization across multiple charts
15. ✅ **Example 31** — Complete chart sync demo
16. ✅ **Grid Conflict Detection** — Auto-detect grid specification conflicts in the same window to prevent layout chaos
17. ✅ **Code Optimization** — Refactored `parse_position()` and `_convert_string_to_grid()` functions for improved maintainability

**Usage:**
```bash
pip install lightweight-charts-python
cd examples/27_reflex_chart
.\run.ps1          # auto-clean cache + start Reflex
# or manually:
reflex run
```

`ReflexChart` three modes:
- **Static HTML** (no reflex) — `chart.get_html()`
- **Static Reflex embed** — `chart.to_reflex()` returns `rx.Component`
- **Dynamic Reflex embed** — `auto_flush=True` + `chart.flush()` → incremental updates; `on_load` installs callback bridge → receives JS events

---

Added and Enhanced Features

1. **Real-time streaming updates** — Supports updating candlesticks directly from tick data.
2. **Multi-pane charts** — Create sub-charts using `create_subchart()`.
3. **Toolbox** — Draw trendlines, rectangles, rays, and horizontal lines directly on charts.
4. **Event system** — Timeframe selectors, search, hotkeys, and more.
5. **Table component** — Useful for watchlists, order entry, and position management.
6. **Polygon.io integration** — Direct access to market data.
7. **Volume + Open Interest overlay** — Independent Y-axis scaling.
8. **Multi-Chart instances** — Completely independent chart objects.
9. **Persistent legend** — OHLC remains visible even when the mouse leaves the chart.
10. **Vertical span highlighting** — Highlight date ranges with semi-transparent fills.
11. **Resource cleanup API** — `reset()`, `clear_handlers()`, `audit()`, `delete()`.
12. **PriceLine object** — `create_price_line().delete()`.
13. **Table.delete()** — Destroy tables and clean up JS state.
14. **Human-readable IDs** — `window.Chart_1`, `window.Line_3`, etc.
15. **Resource audit** — `chart.audit(use_js=True)` returns full TOML-formatted JS variable state.
16. **Comprehensive cleanup tests** — test_cleanup.py verifies no leaks in Python + JS for all resource types.
17. **Sequence Batch Update API** — `Line/Histogram.update_batch()` high-performance batch updates.
18. **Candlestick Batch Update** — `chart.update_bars()/update_from_ticks()`.
19. **Cross-Process Qt Embedding** — `CrossProcessChart` embeds pywebview window into QWidget via native window handle (Windows + Linux/X11).
20. **Grid Layout System** — `position` parameter supports integer, tuple formats; dynamic position control via `get_position()`/`set_position()`.
21. **Chart Sync** — Synchronize timeline and crosshair across multiple charts with `sync` parameter.

**Primary supported environments:** PySide6, PyQt6, wxPython, asyncio, Reflex.

---

# Recommendation

It is recommended that AI coding assistants read the **QUICK_REFERENCE.md** file first for a quick overview of the entire project.

---

# Installation

```bash
pip install https://github.com/One-sixth/lightweight-charts-python
```

# Build

Building this package requires a Node.js environment, as `npm` commands are needed.

First, build the JS bundle library.

### Install Node.js dependencies
```
npm install @rollup/plugin-typescript --save-dev
npm audit fix --force
```

### Build and copy the output to the Python source directory
```
npx rollup -c rollup.config.js
cp dist/bundle.js lightweight_charts/js/bundle.js
```

### Build the wheel package
```
python -m build
```

The built `.whl` file will be in the `dist` directory.

---

## Core API Quick Reference

| Method | Description |
|------|------|
| `chart.set(df)` | Set candlestick data |
| `chart.update(series)` | Update the last candlestick |
| `chart.update_from_tick(tick)` | Update candlesticks from individual trades |
| `chart.marker(text, ...)` | Add a price marker |
| `chart.marker_auto_scale(enable)` | Control whether markers participate in price axis auto-scaling |
| `chart.pop(count)` | Remove N data points from the end |
| `chart.create_line(name, ...)` | Create a line indicator |
| `chart.create_histogram(name, ...)` | Create a histogram indicator |
| `chart.create_subchart(...)` | Create a sub-pane |
| `chart.create_price_line(price, ...)` | Create a price line |
| `chart.horizontal_line(price, ...)` | Create a horizontal line |
| `chart.vertical_span(start, end, ...)` | Create a vertical highlight span |
| `chart.get_position()` | Get chart rendering position (x, y, width, height) as percentages (available before/after show) |
| `chart.set_position(x, y, width, height)` | Dynamically set chart rendering position (available before/after show, pass None to restore default) |
| `chart.audit(use_js=False)` | Resource audit (Python side) |
| `chart.audit(use_js=True)` | Resource audit (JS side, TOML format) |
| `chart.reset()` | Reset the chart to its initial state |
| `chart.screenshot(...)` | Screenshot (v5.2.0+ enhanced: supports add_top_layer and include_crosshair) |
| `chart.clear_handlers()` | Clear all event handlers |
| `chart.set_price_format(type, base, precision)` | Set price axis format to avoid floating-point precision issues (v5.2.0+) |


---

## Documentation & Support

---

**Disclaimer:** This package is an independent creation and has not been endorsed, sponsored, or approved by TradingView. The author has no official relationship with TradingView, and this package does not represent the views or opinions of TradingView.

---

## Examples

### 0. Multi-pane Support

```python
import pandas as pd
import webbrowser
from lightweight_charts import HTMLChart

def demo():
    chart = HTMLChart(width=1200, height=800, inner_height=-500, filename='charts.html')
    df = pd.read_csv('./PDATA/4ohlcv.csv')
    chart.set(df)

    # Pane 0 — SMA7
    line7 = chart.create_line('SMA 7', color='red')
    sma7_data = df.set_index('date')['close'].rolling(7).mean().reset_index()
    sma7_data.columns = ['time', 'SMA 7']
    line7.set(sma7_data)

    # Pane 1 — Histogram
    sma20_data = df[['date', 'close']].copy()
    sma20_data['close'] = sma20_data['close'].rolling(20).mean()
    line20 = chart.create_histogram('SMA 20', pane_index=1)
    line20.set(sma20_data.rename(columns={'date': 'time', 'close': 'SMA 20'}))

    chart.load()
    webbrowser.open(chart.filename)

if __name__ == '__main__':
    demo()
```

### 1. Display CSV Data

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    df = pd.read_csv('ohlcv.csv')
    chart.set(df)
    chart.show(block=True)
```

### 2. Real-time Candlestick Updates

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

    last_close = df1.iloc[-1]['close']
    for _, bar in df2.iterrows():
        chart.update(bar)
        if bar['close'] > 20 and last_close < 20:
            chart.marker(text='Price crossed $20!')
        last_close = bar['close']
        sleep(0.1)
```

### 3. Real-time Updates from Tick Data

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

### 4. Line Indicators (SMA)

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
    chart.legend(visible=True)

    df = pd.read_csv('ohlcv.csv')
    chart.set(df)

    line = chart.create_line('SMA 50')
    line.set(calculate_sma(df, 50))

    chart.show(block=True)
```

### 5. Styling

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    df = pd.read_csv('ohlcv.csv')

    chart.layout(background_color='#090008', text_color='#FFFFFF', font_size=16)
    chart.candle_style(up_color='#00ff55', down_color='#ed4807')
    chart.volume_config(up_color='#00ff55', down_color='ed4807')
    chart.watermark('1D', color='rgba(180,180,240,0.7)')
    chart.crosshair(mode='normal', vert_color='#FFFFFF', horz_color='#FFFFFF')
    chart.legend(visible=True, font_size=14)

    chart.set(df)
    chart.show(block=True)
```

### 6. Callback Events

```python
import pandas as pd
from lightweight_charts import Chart

def on_search(chart, searched_string):
    new_data = get_bar_data(searched_string, chart.topbar['timeframe'].value)
    if not new_data.empty:
        chart.topbar['symbol'].set(searched_string)
        chart.set(new_data)

def on_timeframe_selection(chart):
    new_data = get_bar_data(chart.topbar['symbol'].value, chart.topbar['timeframe'].value)
    if not new_data.empty:
        chart.set(new_data, keep_drawings=True)

if __name__ == '__main__':
    chart = Chart(toolbox=True)
    chart.events.search += on_search
    chart.topbar.textbox('symbol', 'TSLA')
    chart.topbar.switcher('timeframe', ('1min', '5min', '30min'), default='5min',
                          func=on_timeframe_selection)
    chart.set(get_bar_data('TSLA', '5min'))
    chart.show(block=True)
```

### 7. Reflex Embedding (with Live Updates + Callbacks)

```python
import reflex as rx
import pandas as pd
from lightweight_charts import ReflexChart

chart = ReflexChart(width=1000, height=600, auto_flush=True)
chart.set(pd.read_csv('ohlcv.csv'))
chart.layout(background_color='#0c0d0f', text_color='#d8d9db')

class ChartState(rx.State):
    def tick(self):
        chart.update(_next_bar())
        return chart.flush()  # postMessage incremental update, no duplicate init

    def mount(self):
        # Install JS→Python callback bridge
        return rx.call_script("""
if (!window.__LWC_BRIDGE) {
    window.__LWC_BRIDGE = true;
    window.addEventListener('message', function(e) {
        if (e.data?.type === 'lwc-callback') {
            var el = document.getElementById('cb-buffer');
            if (el) {
                var setter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                setter.call(el, e.data.payload);
                el.dispatchEvent(new Event('input', {bubbles: true}));
            }
        }
    });
}""")

def index() -> rx.Component:
    return rx.vstack(
        rx.button('+1 Bar', on_click=ChartState.tick),
        chart.to_reflex(id='lwc-frame', width='100%'),
        rx.input(id='cb-buffer', on_change=ChartState.on_crosshair,
                 style={'opacity':0,'position':'absolute','width':0,'height':0}),
        width='100%', height='100vh', align='stretch',
    )

app = rx.App()
app.add_page(index, on_load=ChartState.mount, title='Reflex + Lightweight Charts')
```

---

## Full Examples Directory

| Number | Example Name | Description |
|------|----------|----------|
| 1 | `1_setting_data` | Basic data setup |
| 2 | `2_live_data` | Real-time candlestick updates |
| 3 | `3_tick_data` | Tick data updates |
| 4 | `4_line_indicators` | Line indicator SMA |
| 5 | `5_styling` | Styling customization |
| 6 | `6_callbacks` | Callback events |
| 7 | `7_multi_pane` | Multi-pane charts |
| 8 | `8_volume_open_interest` | Volume + Open Interest |
| 9 | `9_multi_chart` | Multi-Chart instances |
| 10 | `10_persistent_legend` | Persistent legend |
| 11 | `11_vertical_span` | Vertical span highlighting |
| 12 | `12_audit` | Resource audit |
| 13 | `13_batch_update` | Batch update API |
| 14 | `14_set_period` | Time period lock |
| 15 | `15_pyside6_simple` | PySide6 integration |
| 16 | `16_pyside6_race` | PySide6 performance test |
| 18 | `18_hovered_series_on_top` | Hovered series on top |
| 19 | `19_timescale_options` | Time scale options |
| 20 | `20_tick_mark_density` | Tick mark density control |
| 21 | `21_marker_auto_scale` | Marker auto scale |
| 22 | `22_pop` | Remove data points |
| 23 | `23_crosshair_move` | Crosshair move event |
| 24 | `24_price_format` | Price format settings |
| 25 | `25_screenshot_enhanced` | Enhanced screenshot |
| 26 | `26_series_batch_update` | Series batch update |
| 27 | `27_reflex_chart` | Reflex integration |
| 28 | `28_cross_process_chart` | Cross-process Qt embedding |
| 29 | `29_grid_layout` | Grid layout system |
| 30 | `30_table_component` | Table component (watchlist/position management) |
| 31 | `31_chart_sync` | Chart sync (timeline + crosshair) |


---

## Example Screenshots

> **Below are the screenshot placeholders for all examples; images can be replaced based on actual results**

### Example 1: Display CSV Data

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    df = pd.read_csv('ohlcv.csv')
    chart.set(df)
    chart.show(block=True)
```

![Display CSV Data](images/1_setting_data.png)

---

### Example 2: Real-time Candlestick Updates

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

![Real-time Updates](images/2_live_data.gif)

---

### Example 3: Updates from Tick Data

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

### Example 4: Line Indicators (SMA)

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

![Line Indicators](images/4_line_indicators.png)

---

### Example 5: Styling

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

![Styling](images/5_styling.png)

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

### Example 7: Multi-pane Charts

```python
import pandas as pd
from lightweight_charts import HTMLChart

def demo():
    chart = HTMLChart(width=1200, height=800)
    df = pd.read_csv('ohlcv.csv')
    chart.set(df)
    line7 = chart.create_line('SMA 7', color='red')
    line7.set(df[['date', 'close']].rename(columns={'close': 'SMA 7'}))
    chart.show()

if __name__ == '__main__':
    demo()
```

![Multi-pane Charts](images/7_multi_pane.png)

---

### Example 8: Volume + Open Interest

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart(toolbox=True)
    df = generate_data()  # includes open_interest column
    chart.set(df)
    chart.show(block=True)
```

![Volume Open Interest](images/8_volume_open_interest.png)

---

### Example 9: Multi-Chart Instances

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

![Multi-Chart Instances](images/9_multi_chart.png)

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

![Vertical Span](images/11_vertical_span.png)

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

### Example 13: Batch Updates

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.set(initial_df)
    chart.show()
    # Batch updates
    chart.update_bars(new_bars_df)
    chart.update_from_ticks(ticks_df)
```

![Batch Updates](images/13_batch_update.png)

---

### Example 14: Time Period Lock

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.set(df_5min)
    chart.set_period(3600)  # Lock to 1 hour
    chart.set(df_30min)  # Important: set() again after set_period for it to take effect
    chart.show(block=True)
```

![Set Period](images/14_set_period.png)

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

![PySide6 Race](images/16_pyside6_race.png)

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

![Hovered Series](images/18_hovered_series_on_top.png)

---

### Example 19: Time Scale Options

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

![Time Scale Options](images/19_timescale_options.png)

---

### Example 20: Tick Mark Density

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.price_scale(tick_mark_density=2.5)  # v5.2.0+
    chart.set(df)
    chart.show(block=True)
```

![Tick Mark Density](images/20_tick_mark_density.png)

---

### Example 21: Marker Auto Scale

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart(marker_auto_scale=False)
    chart.set(df)
    chart.marker(time='2024-01-15', position='above', text='Event')
    chart.show(block=True)
```

![Marker Auto Scale](images/21_marker_auto_scale.png)

---

### Example 22: Pop Data Points

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.set(df)
    chart.pop(50)  # Remove last 50 data points
    chart.show(block=True)
```

![Pop](images/22_pop.png)

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

![Crosshair Move](images/23_crosshair_move.png)

---

### Example 24: Price Format

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    chart.set(df)
    chart.set_price_format(type='base', base=100, precision=2)  # v5.2.0+
    chart.show(block=True)
```

![Price Format](images/24_price_format.png)

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

![Reflex Chart](images/27_reflex_chart.png)

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

![Cross Process Chart](images/28_cross_process_chart.png)

---

### Example 29: Grid Layout

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    chart1 = Chart(position=221)  # 2 rows, 2 cols, position 1
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

**position parameter explanation:**

| Format | Example | Description |
|------|------|------|
| Tuple (x, y) | `(0.02, 0.1)` | Recommended: relative coordinates, range 0-1 |
| Tuple (x, y) | `(100, 50)` | Pixel coordinates, values >= 1 are treated as pixels |
| String (deprecated) | `'left'`, `'right'` | Not recommended, triggers DeprecationWarning, equivalent to `(0, 0)` |

![Table Component](images/30_table_component.png)

---

### Example 31: Chart Sync

```python
from lightweight_charts import Chart

if __name__ == '__main__':
    # Create main chart - using 2x2 grid layout
    chart = Chart(width=1200, height=800, title='Chart Sync Demo', position=(2, 2, 1))
    
    # Create right sub-chart (fully synchronized timeline and crosshair)
    subchart_right = chart.create_subchart(
        position=(2, 2, 2),
        sync=chart.id,           # Sync to main chart
        sync_crosshairs_only=False  # Full sync
    )
    
    # Create bottom sub-chart (crosshair sync only)
    subchart_bottom = chart.create_subchart(
        position=223,            # Equivalent to (2, 2, 3)
        width=2.0,               # Span two columns
        sync=chart.id,
        sync_crosshairs_only=True  # Crosshair sync only
    )
    
    chart.set(df)
    subchart_right.set(df2)
    subchart_bottom.set(df3)
    chart.show(block=True)
```

**sync parameter explanation:**

| Parameter | Type | Description |
|------|------|------|
| `sync` | `bool` or `str` | `True` syncs to parent chart; string is target chart id |
| `sync_crosshairs_only` | `bool` | `True` syncs only crosshair, timeline independent |

![Chart Sync](images/31_chart_sync.png)
