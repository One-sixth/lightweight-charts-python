# MEMORY.md - 项目长期记忆

本文件记录 lightweight-charts-onesixth 项目的核心经验、决策和教训。

---

## ⚠️ pywebview 关键陷阱（最高优先级）

### evaluate_js 无法序列化 lightweight-charts API 对象
- **问题**: JS 函数返回包含 ISeriesApi/IChartApi 等对象的结构时，pywebview 的 `evaluate_js` 无法序列化，导致**整个消息链路永久卡死**
- **修复**: Python 端 `run_script` 调用末尾加 `;0`，阻止返回值传播
- **影响范围**: `createCandleSeries`、`createLineSeries`、`createHistogramSeries` 等所有返回 `{name, series}` 结构的 JS 函数

### 消息循环异常处理不能终止循环
- **问题**: `chart.py` 消息循环中 `KeyError` 和 `Exception` 的 `return` 会**终止整个消息处理**
- **修复**: 移除 `return`，只 `put(None)` 到 return_queue，让循环继续
- **教训**: ⚠️ 消息循环中的异常处理**绝对不能终止循环**

---

## 🏗️ v2.7.0 架构：组合模式

### 类层次

```
Pane (util.py)
├── Window (abstract.py)           ← JS 桥接层
├── SeriesCommon (abstract.py)     ← 数据系列基类
│   ├── CandleSeries               ← K 线（OHLC + volume/OI + tick 聚合）
│   ├── Line                       ← 折线
│   ├── Histogram                  ← 柱状图
│   ├── VolumeSeries               ← 成交量（绑定到 CandleSeries）
│   └── OpenInterestSeries         ← 持仓量（绑定到 CandleSeries）
└── AbstractChart (abstract.py)    ← 图表容器（组合模式，不继承任何 Series）
```

### AbstractChart 组合模式

```python
class AbstractChart(Pane):  # 不再继承 Candlestick
    self.candle = CandleSeries._wrap_handler(self)  # 主 K 线
    self.volume = self.candle.attach_volume()        # 成交量（默认创建）
    self.oi = self.candle.attach_open_interest()     # 持仓量（默认创建）
```

- **`_wrap_handler`**：包装 Handler 已有的 JS series，不创建新 JS 对象
- **`_wrap_existing`**：VolumeSeries/OI Series 标记，`clear_data()` 时只清数据不删除
- **属性代理**：`candle_data`/`data`/`markers`/`_last_bar`/`_interval`/`offset` 用 `@property`
- **内部方法代理**：`_single_datetime_format`/`_normal_df`/`_time_to_bar_time`/`_set_interval` 用显式方法
- **不再使用 `__getattr__`**

### 职责划分

| 类 | 职责 |
|---|------|
| **SeriesCommon** | 数据工具（`_normal_df` 等）、标记（`marker` 等）、精度、显隐 |
| **CandleSeries** | K 线数据（OHLC）、volume/OI 管理、tick 聚合、样式配置 |
| **VolumeSeries** | 成交量数据、OHLC 着色、独立配置/删除 |
| **OpenInterestSeries** | 持仓量数据、独立配置/删除 |
| **AbstractChart** | 图表容器、绘图（`horizontal_line` 等）、子图管理、同步 |

### 关键设计决策

1. **绘图方法在 AbstractChart 上**：`horizontal_line`/`trend_line`/`box` 等只在 AbstractChart 定义，不在 SeriesCommon
2. **`candle_style`/`volume_config`/`open_interest_config` 在 CandleSeries 上**：不在 SeriesCommon
3. **`update_from_ticks` 双层设计**：
   - SeriesCommon 通用版：按 time 分组取 last，无 `cumulative_volume`
   - CandleSeries 覆盖版：OHLC 聚合 + volume/OI
4. **`_is_subchart` 属性**：`create_subchart()` 设为 True，`reset()`/`clear_handlers()` 限制仅主图可调用
5. **`remove_subchart` 清理**：JS 端遍历 window 全局变量，删除引用子图表 series 的 VolumeSeries/OI

---

## 📊 Chart 创建时的 series 状态

| 组件 | JS 端 | Python 端 |
|------|:---:|:---:|
| candle (K 线) | ✅ Handler 构造函数创建 | ✅ `_wrap_handler` 包装 |
| volume (成交量) | ✅ Handler 构造函数创建 | ✅ `attach_volume(_wrap_existing=True)` |
| open_interest (持仓量) | ✅ Handler 构造函数创建 | ✅ `attach_open_interest(_wrap_existing=True)` |

---

## 🔧 JS 端关键点

### async IIFE 脚本链
- `on_js_load()` 将所有排队脚本拼接成一个 async IIFE 执行
- 链中任何脚本报错会中断整个 async 函数
- 关键操作（如 `setMarkers`）必须用 try/catch 保护

### seriesMarkers 动态创建
- `_update_markers()` 中动态检查 `{self.id}.seriesMarkers` 是否存在
- 如果不存在，调用 `LightweightCharts.createSeriesMarkers(series, [], {autoScale: true})` 创建
- 这样所有 Series（Line/Histogram/VolumeSeries/OI Series）都支持标记
- Handler 构造函数中仍为 `this.series` 预创建 seriesMarkers（主 K 线）

### Handler 构造函数
- 永远创建 3 个 series：`this.series`（K 线）、`this.volumeSeries`（成交量）、`this.openInterestSeries`（持仓量）
- Python 端通过 `_wrap_existing` 模式复用，不重复创建

### pane_index 参数
- `create_line`/`create_histogram` 等支持 `pane_index` 参数
- `pane_index=0`（默认）与主 K 线同 pane
- `pane_index=1` 独立 pane（如 Volume 柱状图不挤压 K 线）

---

## 📝 修改文件清单（v2.7.0）

| 文件 | 修改内容 |
|------|---------|
| `lightweight_charts/abstract.py` | AbstractChart 组合重构、VolumeSeries、OpenInterestSeries、CandleSeries 增强、Candlestick 删除 |
| `lightweight_charts/drawings.py` | VerticalSpan 参数 `series`→`chart`、时间处理统一、参数校验 |
| `lightweight_charts/__init__.py` | 导出 VolumeSeries、OpenInterestSeries |
| `src/general/handler.ts` | GLOBALS_RE 新增 VolumeSeries/OI 匹配 |
| `lightweight_charts/js/bundle.js` | 重新编译 |
| `test/test_candle_series.py` | 6 个测试用例 |
| `test/test_cleanup.py` | 泄漏检测适配 |

---

*最后更新：2026-06-20*
