# lightweight-charts-python

[MIT License](LICENSE)

![cover](cover.png)

**lightweight-charts-python** aims to provide a simple and Pythonic way to access and implement TradingView's Lightweight Charts.

Chinese Version ReadMe: [README.md](README.md)

---

### Trying to Continue Maintenance

I have limited knowledge of TypeScript and primarily rely on DeepSeek AI for assistance with maintenance.

Most bugs have been resolved, and all examples have been tested successfully on Windows.
The main Lightweight Charts library has been updated to v5.2.0, with some new v5 features added.

---

### Recent Updates (v2.3 → v2.3.3)

**New or Updated Features:**
1. ✅ **Sequence Batch Update API** — `Line.update_batch()` / `Histogram.update_batch()` update multiple data points at once for dramatically improved performance
2. ✅ **Candlestick Batch Update** — `chart.update_bars()` / `chart.update_from_ticks()` batch data processing with 10x speedup
3. ✅ **Open Interest Visualization** — Independent Y-axis scaling, overlay with volume
4. ✅ **Reflex Integration** — `ReflexChart(StaticLWC)` for embedding charts in [Reflex](https://reflex.dev) web apps; incremental live updates via postMessage bridge; JS→Python callback bridge forwarding crosshair_move etc. to State
5. ✅ **Init Idempotency** — Fixes duplicate chart creation caused by Reflex compile/runtime module double-import
6. ✅ **Example 26** — Batch update performance comparison demo for Line and Histogram
7. ✅ **Example 27** — Complete Reflex demo (SMA + bar push + crosshair callback), with `clean.ps1` / `run.ps1` scripts
8. ✅ **Cross-Process Qt Embedding** — `CrossProcessChart` embeds pywebview chart window into PySide6/PyQt6 QWidget via HWND, with frameless mode and resize sync (Windows only)
9. ✅ **Example 28** — CrossProcessChart cross-process embedding demo

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
19. **Cross-Process Qt Embedding** — `CrossProcessChart` embeds pywebview window into QWidget via HWND (Windows only).

**Primary supported environments:** PySide6, PyQt6, wxPython, asyncio, Reflex.

---

# Recommendation

It is recommended that AI coding assistants read the **QUICK_REFERENCE.md** file first for a quick overview of the entire project.

---

# Installation

```bash
pip install ?
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

## More Examples
See the [examples](examples/README.md) directory for more sample code.

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
| `chart.audit(use_js=False)` | Resource audit (Python side) |
| `chart.audit(use_js=True)` | Resource audit (JS side, TOML format) |
| `chart.reset()` | Reset the chart to its initial state |
| `chart.screenshot(...)` | Screenshot (v5.2.0+ enhanced: supports add_top_layer and include_crosshair) |
| `chart.set_price_format(type, base, precision)` | Set price axis format to avoid floating-point precision issues (v5.2.0+) |
| `chart.clear_handlers()` | Clear all event handlers |
| `chart.set_price_format(type, base, precision)` | Set price axis format to avoid floating-point precision issues (v5.2.0+) |

---

## Documentation & Support

---

**Disclaimer:** This package is an independent creation and has not been endorsed, sponsored, or approved by TradingView. The author has no official relationship with TradingView, and this package does not represent the views or opinions of TradingView.
