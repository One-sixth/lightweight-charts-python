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

## 🔧 v2.7.2 TS 编译警告消除（2026-06-21）

### 问题
v2.7.0 重构将 `Handler.series` 改为 `ISeriesApi | null`（惰性创建），导致 11 个 TS2345/TS2531 警告。使用处传入 `this.series` 但 TS 认为它可能是 `null`。

### 修复策略：Null Guard
所有使用 `series` 的地方添加 null guard（`if (!series) return/continue`），而非 `!` 非空断言。原因：series 确实可能是 null（构造函数初始化为 null），防御性编程更安全。

### 修改位置
| 文件 | 函数 | 改动 |
|------|------|------|
| handler.ts | `createToolBox()` | 顶部 `if (!this.series) return` |
| handler.ts | `syncChartsAll` ×2 | `srcSeries` / `target.series` null guard |
| handler.ts | `syncCharts` | `crosshairHandler` 顶部 guard；`getPoint` 签名 `series: ISeriesApi \| null` + 内部 guard |
| handler.ts | `_syncCharts` | `srcSeries` / `target.series` null guard |
| legend.ts | `legendHandler()` | 顶部 `if (!this.handler.series) return` |

### 教训
- `Handler.series` 初始化为 `null` 后，所有引用点都必须考虑 null 情况
- `continue` 只能用于循环内，回调函数中用 `return`

---

## 🏗️ v2.8.0 架构：统一输入 + set→update_bars 委托

### 类层次

```
Pane (util.py)
├── Window (abstract.py)           ← JS 桥接层
├── SeriesCommon (series.py)       ← 数据系列基类
│   ├── LineSeries                 ← 折线（继承全部 set/update_bars/update_ticks）
│   ├── HistogramSeries            ← 柱状图（同上，额外 _option_columns=['color']）
│   ├── AreaSeries                 ← 面积图（折线+渐变填充，继承全部 set/update_bars/update_ticks）
│   ├── BaselineSeries             ← 基准线（以基准值为界上下分色，继承全部 set/update_bars/update_ticks）
│   ├── VolumeSeries               ← 成交量（覆盖 _prepare_vol_df/update_bars/update_ticks）
│   ├── OpenInterestSeries         ← 持仓量（仅 __init__/_build/config，其余全部继承）
│   ├── CandleSeries               ← K 线（覆盖 set/update_bars/update_ticks，OHLC 聚合）
│   └── OHLCBarSeries              ← 美国线（继承 CandleSeries，覆盖 __init__/_build/bar_style）
└── AbstractChart (abstract.py)    ← 图表容器（组合模式）
    ├── self.candle: CandleSeries       ← 固定 ID: window.Chart_X_candle
    ├── self.volume: VolumeSeries       ← 固定 ID: window.Chart_X_volume（始终存在）
    └── self.oi: OpenInterestSeries     ← 固定 ID: window.Chart_X_oi（始终存在）
```

### 统一输入契约

所有系列的 `set()`/`update_bars()`/`update_ticks()` 统一接受 `time` + `value` 列。

AbstractChart 接口：
- `set(df)` / `update_bars(df)`：接受 `time, open, high, low, close, [volume], [open_interest]`
- `update_ticks(df)`：接受 `time, price, [volume], [open_interest]`
- 内部自动重命名：`price→value`、`volume→value`、`open_interest→value`

### set → update_bars 委托模式（v2.8.0）

SeriesCommon / VolumeSeries / OpenInterestSeries 统一使用：
1. `set()`：清空 JS/Python + `_last_bar=None` + 委托 `update_bars()` + markers
2. `update_bars()`：`_prepare_xxx()` 清洗+校验+选列 → 空数据用 `setData`（高效），有数据用 per-row `update`
3. `_prepare_xxx()`：各系列特有的清洗+校验+选列入口

### normal_df 精简（v2.8.0）

- 不再自动将列名转为小写
- 不再自动将 `date` 列重命名为 `time`
- 只做：无 time 列时用 index + 时间转秒级时间戳

### VolumeSeries 着色（v2.8.0）

- `_prepare_vol_df` 要求 `open`/`close` 列，缺失抛 `ValueError`
- `self.data` 维护 5 列：`time, value, open, close, color`
- tick 累积模式：保留已有 `open`，更新 `close`，重算 `color`
- AbstractChart 转发时自动带上 `open`/`close`（bar 路径）或 `price`（tick 路径）

### AbstractChart 不联动 _lines（v2.8.0）

`set()`/`update_bars()`/`update_ticks()` 不再自动转发数据给 Line/Histogram 系列。
Line/Histogram 需要各自调用 `line.set(df)` 独立设置，df 必须包含 `time` 和 `value` 列。

### data 属性（v2.8.0）

- `chart.data`：始终返回 7 列 `time, open, high, low, close, volume, open_interest`
- `chart.vol_data`：只返回 `time, value`（不暴露 open/close/color）
- `chart.oi_data`：返回 `time, value`

---

## 🆕 v2.8.1 新增 Series 类型（2026-06-27）

### 新增三个 Series

| Series | Python 类 | JS 创建方法 | 数据输入 | 说明 |
|--------|----------|-----------|---------|------|
| **面积图** | `AreaSeries` | `createAreaSeries` | time + value | 折线+渐变填充，支持 topColor/bottomColor |
| **美国线** | `OHLCBarSeries` | `createOHLCBarSeries` | time + O/H/L/C | 继承 CandleSeries，横向 OHLC 柱状图 |
| **基准线** | `BaselineSeries` | `createBaselineSeries` | time + value | 以基准值为界上下分色 |

### 继承设计决策

**AreaSeries / BaselineSeries → SeriesCommon**：
- 数据输入与 LineSeries 完全一致（time + value）
- 只需覆盖 `__init__`（调不同 JS 方法），其余全部继承
- AreaSeries 额外参数：topColor/bottomColor/relativeGradient/invertFilledArea
- BaselineSeries 额外参数：baseValue + 6 种颜色（top/bottom fill/line）

**OHLCBarSeries → CandleSeries**：
- 两者 95% 代码相同（OHLC 数据处理：set/update_bars/update_ticks/clear_data/delete）
- 覆盖 `__init__`：跳过 `CandleSeries.__init__`，直接调 `SeriesCommon.__init__` + `_build()`
- 覆盖 `_build()`：调 `createOHLCBarSeries` 替代 `createCandleSeries`
- 覆盖 `bar_style()`：美国线专属样式（upColor/downColor/openVisible/thinBars）
- 覆盖 `candle_style()`：抛出 `AttributeError` 提示使用 `bar_style()`

### OHLCBarSeries 覆盖 candle_style 的原因

```python
class OHLCBarSeries(CandleSeries):
    def __init__(self, ...):
        # 跳过 CandleSeries.__init__，避免创建 CandlestickSeries JS 对象
        SeriesCommon.__init__(self, chart, name, pane_index)
        self._build()  # 调自己的 _build

    def candle_style(self, *args, **kwargs):
        raise AttributeError("OHLCBarSeries 没有 candle_style，请使用 bar_style() 代替")
```

**为什么不能 `del self.candle_style`**：`candle_style` 是类方法（定义在 CandleSeries 上），不能通过 `del` 从实例上删除。正确做法是在子类中覆盖该方法。

### Legend OHLC 支持

**问题**：OHLCBarSeries 被加入 `_lines`，但 legend 的 lines 遍历只认 `value` 字段，OHLC 类型只有 `open/high/low/close`，导致 legend 显示为空。

**修复**：在 `legend.ts` 的 `legendHandler` 中，lines 遍历增加 `seriesType()` 检测：
```typescript
const seriesType = e.series.seriesType();
if (seriesType === 'Bar' || seriesType === 'Candlestick') {
    // 显示 O ... | H ... | L ... | C ...
} else if (seriesType === 'Histogram') {
    // shorthand 格式
} else {
    // 普通 value 格式
}
```

### JS 端新增要点

- **handler.ts import**：新增 `AreaSeries`、`BarSeries`、`BaselineSeries` 及 `AreaStyleOptions`、`BarStyleOptions`、`BaselineStyleOptions`
- **handler.ts SKIP_KEYS**：新增 `createAreaSeries`、`createOHLCBarSeries`、`createBaselineSeries`
- **handler.ts GLOBALS_RE**：新增 `AreaSeries_\d`、`OHLCBarSeries_\d`、`BaselineSeries_\d` 模式
- **createOHLCBarSeries**：与 createLineSeries/createHistogramSeries 完全对称的模式（name + options + paneIndex + dontAddList）

### lightweight-charts v5.2.0 完整 Series 清单

| Series 类型 | TS 导出 | Python 实现 | 状态 |
|-------------|---------|------------|------|
| CandlestickSeries | `CandlestickSeries` | `CandleSeries` | ✅ v2.7.0 |
| LineSeries | `LineSeries` | `LineSeries` | ✅ v2.7.0 |
| HistogramSeries | `HistogramSeries` | `HistogramSeries` | ✅ v2.7.0 |
| AreaSeries | `AreaSeries` | `AreaSeries` | ✅ v2.8.1 |
| BarSeries | `BarSeries` | `OHLCBarSeries` | ✅ v2.8.1 |
| BaselineSeries | `BaselineSeries` | `BaselineSeries` | ✅ v2.8.1 |
| CustomSeries | — | — | ❌ 暂不实现 |

---

## 📊 Handler 构造函数状态

```typescript
// handler.ts — 精简后的构造函数，7 个参数
constructor(
    chartId: string,
    innerWidth: number,
    innerHeight: number,
    nrows: number,
    ncols: number,
    index: number,
    autoSize: boolean
)

// 惰性创建，仅 series/volumeSeries/openInterestSeries
this.series = null;
this.volumeSeries = null;
this.openInterestSeries = null;

// Python 端 AbstractChart.__init__ 创建后设置引用
this.id.series = this.candle.id.series;
this.id.volumeSeries = this.volume.id.series;
this.id.openInterestSeries = this.oi.id.series;
// seriesMarkers 不再存在于 Handler 上，由 _update_markers() 按需在 series 级别创建
```

**已移除的参数**（v2.7.1 清理）：
- `paneIndex`：pane_index 在系列创建时（createLineSeries 等）传入，Handler 层面不需要
- `marker_auto_scale`：纯 Python 侧逻辑，`AbstractChart._marker_auto_scale` 存储，`_update_markers()` 直接读取

---

## 🔧 JS 端关键点

### seriesMarkers 按需创建（v2.7.1 清理后）
- **Handler 不再持有 `seriesMarkers`**：v2.7.0 中 Handler 级别的 `seriesMarkers` 从未被功能性使用，已移除
- **`_update_markers()` 按需在 series 级别创建**：首次调用时检查 `{self.id}.seriesMarkers` 是否存在，不存在则调用 `LightweightCharts.createSeriesMarkers()` 创建
- **清理随 series 删除自动完成**：`delete {series.id}` 删除 series 全局变量时，其 `seriesMarkers` 属性一并清除
- 所有 Series（Line/Histogram/VolumeSeries/OI Series）都支持标记

### GLOBALS_RE 正则
- 匹配 `Chart_\d` 前缀，覆盖 `Chart_1_candle`/`Chart_1_volume`/`Chart_1_oi`
- 新增 `VolumeSeries_\d` 和 `OpenInterestSeries_\d` 模式

### pane_index 参数
- `create_line`/`create_histogram` 等支持 `pane_index` 参数
- `pane_index=0`（默认）与主 K 线同 pane
- `pane_index=1` 独立 pane

---

## 📝 纯函数提取到 util.py

| 函数 | 说明 |
|------|------|
| `normal_df(df, exclude_lowercase)` | 标准化 DataFrame |
| `merge_value_by_time(df)` | 合并同时间戳 bar |
| `get_df_interval_offset(df)` | 获取时间间隔和偏移 |
| `time_to_bar_time(data, offset, interval)` | 时间对齐到 bar 边界 |

SeriesCommon 中保留薄委托（`self._chart._time_to_bar_time(data)` 等）。

---

## 📝 修改文件清单（v2.7.0 + v2.7.1 清理）

| 文件 | 修改内容 |
|------|---------|
| `lightweight_charts/abstract.py` | AbstractChart 组合重构、VolumeSeries、OpenInterestSeries、CandleSeries 增强、Candlestick 删除、固定 ID、reset/set 重建、**`_marker_auto_scale` 存储与 `_update_markers()` 使用**、**移除 Handler 级别 `seriesMarkers` 赋值**、**_df_cleaned 数据清洗优化**、**_lines 数据转发**、**VolumeSeries/OI 数据自维护**、**update_batch→update_bars 重命名**、**update=update_bar 类级别别名** |
| `lightweight_charts/util.py` | +4 个纯函数 |
| `lightweight_charts/drawings.py` | VerticalSpan 参数+时间+校验修复 |
| `lightweight_charts/__init__.py` | 导出 VolumeSeries、OpenInterestSeries |
| `src/general/handler.ts` | GLOBALS_RE、Handler 惰性创建、series 类型允许 null、**移除 `seriesMarkers` 属性/初始化/SKIP_KEYS/audit 读取**、**移除 `createSeriesMarkers` import 和调用**、**`createCandleSeries` 不再返回 seriesMarkers**、**audit `markersCount` 改为从 series 级别读取（后移除）**、**`_marker_auto_scale` 参数加 `_` 前缀** |
| `lightweight_charts/js/bundle.js` | 重新编译 |
| `test/test_candle_series.py` | 6 个测试用例 |
| `test/test_cleanup.py` | 泄漏检测适配、新增 test_reset_cleanup、WARN→FAIL、**handlers 检查区分 toolbox/non-toolbox** |
| `examples/35_line_markers/` | Line/Histogram 标记示例 |

---

## 🐛 Bug 修复记录

### clear_data() 漏清 volume/OI（2026-06-21 修复）
- **问题**：v2.7.0 重构后，`AbstractChart.clear_data()` 只委托给 `CandleSeries.clear_data()`，后者只清 K 线数据，**漏掉了 volume 和 OI 系列的数据**
- **影响**：`reset_sub()` 调用 `clear_data()` 后，成交量/持仓量柱状图仍然显示旧数据
- **根因**：旧版（继承模式）`clear_data()` 直接清除三个 JS series；新版（组合模式）拆分为独立类后，`CandleSeries.clear_data()` 只管自己
- **修复**：`AbstractChart.clear_data()` 补充清除 `self.volume` 和 `self.oi` 的数据
- **涉及文件**：`lightweight_charts/abstract.py` L1604-1610

### _seriesList 包含 volume/OI 导致审计计数错误（2026-06-21 修复）
- **问题**：v2.7.0 重构后，volume/OI 通过 `createHistogramSeries`/`createLineSeries` 创建，这两个方法无条件 `push` 到 `_seriesList`，导致 `extraSeriesCount` 始终 ≥2
- **影响**：`test_candle_series.py` 中 3 个测试 FAIL（期望 `extraSeriesCount==0` 但实际为 2）
- **根因**：旧版 handler.ts 有独立的 `createVolumeSeries`/`createOpenInterestSeries` 方法不加入 `_seriesList`；新版统一用 `createHistogramSeries`/`createLineSeries` 后丢失了这个区分
- **修复**：
  1. JS 端：`createLineSeries`/`createHistogramSeries` 新增 `noList` 参数，`true` 时跳过 `_seriesList.push`
  2. Python 端：`VolumeSeries.__init__` 和 `OpenInterestSeries.__init__` 创建时传 `true`
- **涉及文件**：`src/general/handler.ts` L679/697、`lightweight_charts/abstract.py` L839/L991

---

## 🔧 Legend reset_sub 后不恢复（2026-06-21 修复）

### 问题
`reset_sub()` 后再次 `set()` + `legend(visible=True)` + `create_line()`，legend 不显示。

### 根因
`legend.cleanup()` 中 `this.div.remove()` 将 DOM 元素从文档树移除，但：
- `legend(visible=True)` 只修改 detached div 的属性 → 无效
- `makeSeriesRow()` 向 detached 的 `seriesContainer` appendChild → 行不可见

### 修复
1. **legend.ts** 新增 `recreate()` 方法：重建 DOM 结构 + 重新订阅 crosshair
2. **abstract.py** `reset_sub()` 末尾（所有清理之后）调用 `legend.recreate()`
3. 顺序关键：`recreate()` 必须在 `cleanup()` + `_cleanup_events()` + `_unsync_all()` + `_remove_my_handlers()` **之后**执行，避免 crosshair 订阅被后续清理干扰

### 教训
- `div.remove()` 是破坏性操作，后续所有依赖该 DOM 的操作都会失败
- "清理→重建"模式中，重建必须放在**所有清理步骤之后**

---

## 🧪 test_cleanup.py handlers 检查失败（2026-06-21 修复）

### 问题
`test_resource_full_cleanup` 中两个 FAIL：
- `handlers_not_empty`：清理后 `len(chart.win.handlers) == 1`，期望 0
- `py_handlers`：Python 侧 final state 同样 FAIL

### 根因
`Chart(toolbox=True)` 初始化时，`ToolBox.__init__` 注册了 `save_drawings{chart.id}` handler：
```python
# toolbox.py:10
chart.win.handlers[f'save_drawings{self.id}'] = self._save_drawings
```
测试清理流程只移除了自己添加的 `test_handler`，未处理 ToolBox 的 handler。

### 修复
- 测试函数拆分为 `_impl(toolbox)` + 包装函数
- handlers 检查改为：toolbox=True 预期 1 个（save_drawings），toolbox=False 预期 0 个
- `test_resource_full_cleanup` 和 `test_multi_chart_cleanup` 均测试 toolbox=True 和 toolbox=False 两种场景

### 教训
- 组件（ToolBox、TopBar 等）初始化时注册的 handler 属于"基础设施"，不随用户资源清理而删除
- 测试清理检查需区分"用户 handler"和"组件 handler"，不能一刀切期望 0

---

## 🐛 update_bars/update_from_ticks 不转发 volume/OI（2026-06-21 修复）

### 问题
v2.7.0 组合架构重构后，`AbstractChart.update_bars(df)` 只委托给 `self.candle.update_bars(df)`，后者只处理 OHLC 列，volume/OI 数据被静默丢弃。`set()` 正确转发了 volume/OI，但 `update()`/`update_bars()`/`update_from_ticks()` 遗漏了。

### 影响
- `chart.update_bars(df)` — volume 不更新（用户在 examples/34_candle_series/3_batch_update.py 中发现）
- `chart.update_from_ticks(df)` — volume 不更新
- `chart.update_from_tick(series)` — volume 不更新

### 修复
1. **`update()`/`update_bars()`**：新增 volume/OI 转发给 `self.volume`/`self.oi`
2. **`update_from_ticks()`**：重写——先聚合 volume/OI 转发给独立 series，再剥离 volume/OI 列交给 CandleSeries 处理 OHLC（避免重复聚合）
3. **`update_from_tick()`**：委托给 `update_from_ticks()` 统一处理
4. **`update_bar`/`update_bars` 别名**：从 `property(lambda: self.candle.xxx)` 改为普通方法，委托给 `update()`/`update_bars()`

### 教训
- **property 别名陷阱**：`update_bars = property(lambda self: self.candle.update_bars)` 直接绑定 CandleSeries 方法，绕过了 AbstractChart 的转发逻辑。改为普通方法委托更安全
- **`update_from_ticks` 不可简单转发**：CandleSeries 内部已有 tick→bar 聚合逻辑（含 volume），直接转发会导致 volume 重复聚合。必须剥离 volume/OI 列后再交给 CandleSeries

---

## 📊 数据管线架构（v2.7.2+）

### _df_cleaned 清洗优化
- **问题**：AbstractChart.set() 转发数据给 candle/volume/OI/lines 时，每个 series 各自调 `normal_df + _time_to_bar_time + merge_value_by_time`，重复 N 次
- **方案**：`_clean_df(df, _df_cleaned=False)` 统一清洗入口，`_df_cleaned=True` 跳过全部三步
- **AbstractChart 独立版**：继承 Pane（非 SeriesCommon），需独立定义 `_clean_df`
- **_lines 名字保护**：`_line_names()` 返回所有 line 名字集合，传给 `normal_df(exclude_lowercase=...)` 防止被小写化

### update/update_bar 模式
```python
def update_bar(self, series):
    """更新最新一根 bar。"""
    self.update_bars(series.to_frame().T)
update = update_bar  # 类级别别名
```
所有 5 个类（SeriesCommon/VolumeSeries/OI/CandleSeries/AbstractChart）统一模式。

### 更新顺序
candle → volume → oi → _lines（每个 series 独立维护 `_last_bar`，顺序不影响正确性）

### VolumeSeries/OpenInterestSeries 数据自维护
- `set()` 维护 `self.data` + `self._last_bar`
- `update_bars()` 增量维护 `self.data` + `_last_bar` 过滤旧数据

---

## 🧪 数据聚合测试体系（2026-06-22 新增）

### 测试文件
`test/test_data_aggregation.py` — 13 个测试函数（7 旧 + 6 新），覆盖完整数据聚合管线。

### 新增测试模块

| 模块 | 内容 | 校验项数 |
|------|------|---------|
| `test_util_functions` | `get_df_interval_offset` / `normal_df` / `time_to_bar_time` / `merge_value_by_time` 纯函数单元测试 | 16 |
| `test_cross_level_aggregation` | 5s→1min, 1min→5min, 1h→daily, 1s→1min→5min→1h 多级链式聚合 | 15 |
| `test_chaos_random_mixed` | **100 步混沌测试**：随机 mix ticks+bars+不同时间级别，每步校验 | 100 步 |
| `test_chaos_multi_level_fusion` | 8 步操作序列：5min→1min→1h→ticks→15min→ticks→1min→1h | 8 步 |
| `test_chaos_last_bar_inheritance` | 连续 5 批 ticks 落在同一窗口，验证 open 不变/high 递增/low 递减 | 10 步 |
| `test_edge_cases` | 空 DataFrame、单行、乱序 tick、重复时间戳、set() 覆盖 | 14 |

### 关键设计决策

#### compute_expected 的 tick vs bar 清洗路径差异 ⭐
- **tick 路径**：只做 `normal_df + time_to_bar_time`（不做 `merge_value_by_time`！）
- **bar 路径**：做 `normal_df + time_to_bar_time + merge_value_by_time`
- **原因**：`AbstractChart.update_from_ticks` 只做 `normal_df + time_to_bar_time`，然后传给 `candle.update_from_ticks(_df_cleaned=True)` 跳过清洗
- **坑**：如果 tick 路径也做 `merge_value_by_time`，多条 tick 会被压缩为一条（只保留 last price），导致 OHLC 聚合的 max/min 全部丢失

#### 期望值计算的 replace-or-append 逻辑
- 复刻 `update_bars` 的边界替换：第一个新 bar 时间 == 最后一根旧 bar 时间 → 替换最后一根
- 其他情况：简单追加
- 不用 `drop_duplicates`（会导致旧数据中匹配的行被错误删除）

#### 真实 Chart 测试模式
- 所有测试使用真实 `Chart()` 实例（不调 `show()`，不启动 pywebview）
- 数据管理在 Python 端完成，JS 调用排队但不执行
- 访问路径：`chart.candle.data`（OHLC）、`chart.volume.data`（volume）、`chart.oi.data`（OI）

### 辅助函数

| 函数 | 用途 |
|------|------|
| `assert_close(actual, expected, label, errors)` | DataFrame 近似比较，返回 True/False |
| `compute_expected(expected, new_bars, chart, is_ticks, cumulative_volume, prev_last_bar)` | 模拟 chart 聚合管线计算期望值 |
| `verify_chaos(chart, expected, step, op_desc, errors)` | 混沌测试每步校验，失败时打印 worst index + 时间戳 |
| `make_random_ticks(n, start_ts, ...)` | 生成随机 tick 数据 |
| `make_random_bars(n, start_ts, interval_sec, ...)` | 生成随机 bar 数据（任意时间级别） |

---

## 🎨 Histogram 任意颜色支持（2026-06-23 新增）

### 设计
- `Histogram.__init__` 内置 `_option_columns=['color']`，无需外部传入
- `SeriesCommon._option_columns` 机制：set/update_bars 时自动检测并携带可选列到 JS 端
- 使用时只需在 DataFrame 中包含 `color` 列：`df = pd.DataFrame({'time': ..., 'value': ..., 'color': ['#f00', '#0f0']})`

### _check_value_name_conflict_and_rename 方法
- **职责**：统一处理 value 列和系列名的冲突检测与重命名（替代旧的 `if self.name:` 分支）
- **非 inplace rename**：返回新 df，不修改调用者的 df → 多个 line 共享同一个 df 时互不干扰
- **精确匹配**：`df.rename(columns={self.name: 'value'})`，要求列名与 `self.name` 完全一致
- **调用者必须接收返回值**：`df = self._check_value_name_conflict_and_rename(df)`
- **三种结果**：重命名成功 / 已有 value 列直接用 / 冲突报错

### 为什么必须非 inplace
- `AbstractChart.set()` 中所有 line 共享同一个 df
- 如果 inplace rename，第一个 line 把 `SMA_5→value` 后，第二个 line 看到 `value+RSI_14` → 冲突报错
- `update_bars` 路径不受影响（`_clean_update_bars` 通过 `normal_df` 创建了独立副本），但非 inplace 更安全一致

### 注意事项
- `chart.set()` 不会转发 color 列（只转发 OHLC+volume），histogram 需要**单独 `hist.set()`**
- `_option_columns` 的列名必须全小写（`normal_df` 会将所有列名小写化，大写列名无法匹配）

---

*最后更新：2026-06-27（v2.8.1 新增 AreaSeries/OHLCBarSeries/BaselineSeries + legend OHLC 支持）*
