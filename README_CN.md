# lightweight-charts-python

[![PyPi Release](https://img.shields.io/pypi/v/lightweight-charts?color=32a852&label=PyPi)](https://pypi.org/project/lightweight-charts/)
[![Made with Python](https://img.shields.io/badge/Python-3.8+-c7a002?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/github/license/louisnw01/lightweight-charts-python?color=9c2400)](https://github.com/louisnw01/lightweight-charts-python/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/documentation-006ee3)](https://lightweight-charts-python.readthedocs.io/en/latest/index.html)

![cover](https://raw.githubusercontent.com/louisnw01/lightweight-charts-python/main/cover.png)

**lightweight-charts-python** 致力于提供简单、Pythonic 的方式接入 TradingView 的 Lightweight Charts。

---

## 安装

```bash
pip install lightweight-charts
```

---

## 特性

1. **实时数据流式更新** — 支持直接从 tick 数据更新 K线。
2. **多面板图表** — 使用 `create_subchart()` 创建子图。
3. **工具箱** — 在图表上直接绘制趋势线、矩形、射线、水平线。
4. **事件系统** — 时间周期选择器、搜索、快捷键等。
5. **表格组件** — 用于自选股、下单、持仓管理。
6. **Polygon.io 集成** — 直接获取市场数据。
7. **成交量 + 持仓量叠加** — 独立 Y 轴缩放。
8. **多 Chart 实例** — 完全独立的图表对象。
9. **常驻图例** — 鼠标移出图表时 OHLC 仍可见。
10. **垂直区间高亮** — 半透明填充标记日期范围。
11. **资源清理 API** — `reset()`、`clear_handlers()`、`audit()`、`delete()`。
12. **PriceLine 对象** — `create_price_line().delete()`。
13. **Table.delete()** — 销毁表格并清理 JS 状态。
14. **人类可读的 ID** — `window.Chart_1`、`window.Line_3` 等。
15. **资源审计** — `chart.audit(use_js=True)` 返回完整 TOML 格式的 JS 变量状态。
16. **全面的清理测试** — test_cleanup.py 验证所有资源类型的 Python + JS 无泄漏。

**支持环境：** Jupyter Notebook、PyQt6、PyQt5、PySide6、wxPython、Streamlit、asyncio。

---

## 示例

### 0. 多面板支持

```python
import pandas as pd
import webbrowser
from bn_lightweight_charts import HTMLChart

def demo():
    chart = HTMLChart(width=1200, height=800, inner_height=-500, filename='charts.html')
    df = pd.read_csv('./PDATA/4ohlcv.csv')
    chart.set(df)

    # 面板 0 — SMA7
    line7 = chart.create_line('SMA 7', color='red')
    sma7_data = df.set_index('date')['close'].rolling(7).mean().reset_index()
    sma7_data.columns = ['time', 'SMA 7']
    line7.set(sma7_data)

    # 面板 1 — 柱状图
    sma20_data = df[['date', 'close']].copy()
    sma20_data['close'] = sma20_data['close'].rolling(20).mean()
    line20 = chart.create_histogram('SMA 20', pane_index=1)
    line20.set(sma20_data.rename(columns={'date': 'time', 'close': 'SMA 20'}))

    chart.load()
    webbrowser.open(chart.filename)

if __name__ == '__main__':
    demo()
```

### 1. 显示 CSV 数据

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()
    df = pd.read_csv('ohlcv.csv')
    chart.set(df)
    chart.show(block=True)
```

### 2. 实时更新 K线

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
            chart.marker(text='价格突破 $20！')
        last_close = bar['close']
        sleep(0.1)
```

### 3. 从 Tick 数据实时更新

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

### 4. 折线指标（SMA）

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

### 5. 样式定制

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

### 6. 回调事件

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

### 21. marker_auto_scale — 标记是否参与价格轴自动缩放 (v5.2.0)

```python
from lightweight_charts import Chart
import pandas as pd
import numpy as np

# 生成示例数据
def generate_bars(num=200):
    np.random.seed(42)
    times = pd.date_range('2020-01-01', periods=num, freq='1h')
    prices = 100 + np.cumsum(np.random.randn(num) * 0.2)
    data = []
    for i, t in enumerate(times):
        base = prices[i]
        data.append({
            'time': t,
            'open': base + np.random.randn() * 0.1,
            'high': base + abs(np.random.randn()) * 0.3,
            'low': base - abs(np.random.randn()) * 0.3,
            'close': base + np.random.randn() * 0.1,
        })
    return pd.DataFrame(data)

if __name__ == '__main__':
    df = generate_bars(200)

    # 左侧窗口：标记不参与缩放（可能看不到标记）
    chart1 = Chart(title='marker_auto_scale=False', marker_auto_scale=False)
    chart1.set(df)
    chart1.marker(time=df['time'].iloc[30], position='above', shape='arrow_up',
                  color='#ffaa00', text='这里有个标记')

    # 右侧窗口：标记参与缩放（始终可见）
    chart2 = Chart(title='marker_auto_scale=True', marker_auto_scale=True)
    chart2.set(df)
    chart2.marker(time=df['time'].iloc[30], position='above', shape='arrow_up',
                  color='#ffaa00', text='这里有个标记')

    chart1.show(block=False)
    chart2.show(block=True)
```

---

## 核心 API 速查

| 方法 | 说明 |
|------|------|
| `chart.set(df)` | 设置 K线数据 |
| `chart.update(series)` | 更新最后一根 K线 |
| `chart.update_from_tick(tick)` | 从逐笔成交更新 K线 |
| `chart.marker(text, ...)` | 添加价格标记 |
| `chart.marker_auto_scale(enable)` | 控制标记是否参与价格轴缩放 |
| `chart.pop(count)` | 从末尾移除 N 个数据点 |
| `chart.create_line(name, ...)` | 创建折线指标 |
| `chart.create_histogram(name, ...)` | 创建柱状图指标 |
| `chart.create_subchart(...)` | 创建子面板 |
| `chart.create_price_line(price, ...)` | 创建价格线 |
| `chart.horizontal_line(price, ...)` | 创建水平线 |
| `chart.vertical_span(start, end, ...)` | 创建垂直高亮区间 |
| `chart.audit(use_js=False)` | 资源审计（Python 侧） |
| `chart.audit(use_js=True)` | 资源审计（JS 侧，TOML 格式） |
| `chart.reset()` | 重置图表到初始状态 |
| `chart.screenshot(...)` | 截图（v5.2.0+ 增强：支持 add_top_layer 和 include_crosshair） |
| `chart.set_price_format(type, base, precision)` | 设置价格轴格式，避免浮点精度问题（v5.2.0+） |
| `chart.clear_handlers()` | 清空所有事件处理器 |
| `chart.set_price_format(type, base, precision)` | 设置价格轴格式，避免浮点精度问题（v5.2.0+） |
| `chart.screenshot(add_top_layer, include_crosshair)` | 增强截图，可包含水印和十字光标（v5.2.0+） |

### 示例 24 和 25（v5.2.0+ 低优先级功能）

#### set_price_format — 基础价格格式

```python
chart.set_price_format(type='base', base=100, precision=2)
# 以 base 为基准值，所有价格显示为 (实际值 / base)
```

#### screenshot — 增强截图

```python
img = chart.screenshot(add_top_layer=True, include_crosshair=True)
# add_top_layer: 包含水印等顶层元素
# include_crosshair: 包含十字光标
```

---

## 文档与支持

- [完整文档](https://lightweight-charts-python.readthedocs.io/en/latest/index.html)
- 咨询邮箱: `shaders_worker_0e@icloud.com`

---

**免责声明：** 本包为独立开发，未经 TradingView 背书、赞助或批准。作者与 TradingView 无任何官方关系，本包不代表 TradingView 的观点或立场。
