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

### CandleSeries.update_bars 边界替换 OHLC 合并（2026-07-01 修复）⭐
- **问题**：`CandleSeries.update_bars` 在边界替换时（新数据第一根 bar 时间 == 已有最后一根 bar 时间），用 `pd.concat([self.data.iloc[:-1], ohlc])` 直接替换整行。旧 bar 的 open/high/low 被新 bar 覆盖
- **影响**：tick 聚合场景下，同一时间窗口内多批 tick 的 OHLC 信息丢失（open 应保留旧值，high/low 应取极值）
- **修复**：
  ```python
  # 旧：直接替换
  self.data = pd.concat([self.data.iloc[:-1], ohlc], ignore_index=True)
  # 新：OHLC 合并（仅 df.iloc[0] 参与合并，剩余 bar 直接追加）
  df.iat[0, col_open_idx] = self.data.iat[-1, col_open_idx]  # 保留旧 open
  df.iat[0, col_high_idx] = max(self.data.iat[-1, col_high_idx], df.iat[0, col_high_idx])
  df.iat[0, col_low_idx] = min(self.data.iat[-1, col_low_idx], df.iat[0, col_low_idx])
  self.data = pd.concat([self.data.iloc[:-1], df], ignore_index=True)
  ```
- **关键细节**：OHLC 合并**只作用于 `df.iloc[0]`**（第一个新 bar），`df.iloc[1:]` 直接追加。这是因为 `update_bars` 先做 `merge_value_by_time`（合并同时间戳），然后才做边界替换
- **测试同步**：`compute_expected` 必须精确模拟此行为，不能简化

### time_to_bar_time Series 返回类型（2026-07-01 修复）
- **问题**：`time_to_bar_time` 对 Series 输入返回 `np.int64(r)`，结果是 ndarray 而非 Series，导致下游 `.nunique()` 等 Series 方法报 `AttributeError`
- **修复**：`np.int64(r)` → `r.astype(np.int64)`，保持 Series 类型
- **涉及文件**：`lightweight_charts/util.py` L521

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

## 📚 Examples 兼容性维护

### API 破坏性变更后必须检查 examples（2026-06-27 经验）

**问题**：v2.8.0 将 `_check_value_name_conflict_and_rename()` 替换为 `_check_has_value_column()`，所有 LineSeries/HistogramSeries 的 `.set()` 必须传入 `'value'` 列。但 9 个 example 仍然用系列名当 DataFrame 列名，导致 `ValueError`。

**教训**：
- API 破坏性变更后，必须全面扫描所有 examples 的兼容性
- 常见模式：`calculate_sma()` 等辅助函数返回 `{'time': ..., 'SMA 20': ...}` 而非 `{'time': ..., 'value': ...}`
- 修复方案统一：将 DataFrame 列名改为 `'value'`，系列名通过 `create_line(name=...)` 单独指定

**检查清单**（API 破坏性变更后）：
1. 全局搜索 `.set(` — 检查入参 DataFrame 列名
2. 全局搜索 `.rename(columns=` — 检查重命名目标
3. 全局搜索 `DataFrame({` + 系列名/指标名 — 检查所有辅助函数
4. 运行所有 example 测试（至少 import 级别）

**已修复的文件**（9 个）：4_line_indicators、7_multi_pane、12_audit、13_batch_update、18_hovered_series_on_top、26_series_batch_update、32_html_tab_chart (2个)、35_line_markers

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

## 🎨 DrawingSeries 绘图管理架构（v2.8.1）

### 核心设计
```
AbstractChart
├── _drawing_series = {0: DrawingSeries(pane=0), 1: DrawingSeries(pane=1), ...}
│   └── DrawingSeries(Pane) → 惰性创建不可见 JS LineSeries
│       └── _drawings: [HorizontalLine, TrendLine, Box, ...]
├── toolbox._drawing_series = DrawingSeries(pane=0)  ← 独立隔离
└── drawings property → 遍历所有 pane 的 _drawings（兼容旧 API）
```

### 关键点
- 每个 pane 拥有独立的 DrawingSeries，drawing 通过 `attachPrimitive` 挂在各自的不可见 JS LineSeries 上
- ToolBox 持有完全独立的 DrawingSeries，与 chart 的互不干扰
- Drawing 基类持有 `self.drawing_series`（不再直接持有 chart），通过 `chart` property 兼容旧代码
- 工厂方法新增 `pane_index` 参数：`chart.horizontal_line(price, pane_index=1)`
- 旧的 `chart._drawings` 列表已移除，用 `chart.drawings` 属性（property）兼容

### show(wait=) 功能
- `chart.show(wait=5)`：显示窗口后等待 5 秒自动关闭，适用于截图/演示
- 内部用 `self.wv.wv_process.join(timeout=wait)` 替代 `time.sleep`，窗口被用户关闭时进程提前结束 → `join` 立即返回 → `exit()`
- PyWV 事件循环在 `queue.get` 超时后增加 `is_alive` 二次检查，避免窗口关闭后最多等 4 秒才退出（现在最多 2 秒）

---

## 🔍 Pane Primitives vs Series Primitives 深度调研（2026-06-28）

### 背景：DrawingSeries 空 series 不渲染 primitive

v2.8.1 的 DrawingSeries 设计：每个 pane 创建一个不可见的 JS LineSeries，drawing 通过 `attachPrimitive` 挂在上面。

**测试结果**：
| Pane | 系列内容 | DrawingSeries 有数据？ | Primitive 可见？ |
|------|---------|---------------------|-----------------|
| Pane 0 | candle + volume + SMA7 + SMA14 | ❌ 空 | ❌ 不可见 |
| Pane 1 | histogram + RSI line | ❌ 空 | ❌ 不可见 |
| Pane 2 | SMA50 line | ❌ 空 | ✅ 可见！ |

**结论**：`attachPrimitive` 本身不需要数据，但 **pane 的渲染循环对无数据 series 的处理不一致**。无数据 series 的 paneViews() 可能不被调用，导致 primitive 不渲染。Pane 2 能渲染可能是因为它是较轻量的 pane（只有 1-2 个 series）。

### 已验证的修复方案：附着到有数据的 series

将 `attachPrimitive` 从空 LineSeries 改为附着到 pane 上已有的数据 series（pane 0 用 candle，其他 pane 用第一条线）。测试确认：
- ✅ Pane 0 的所有 drawing（水平线、趋势线、框、垂直线）全部可见
- ✅ ToolBox 恢复正常，能在 Pane 0 绘制 drawing
- ❌ Pane 1/2 的 drawing 不可见（因为 `_attach_target` 始终返回 candle series，附着到了错误的 pane）

### 发现的新 API：Pane Primitives

参考文件：`C:\Users\TWD\Downloads\temp2\` 下的 `pane-primitives.md`、`ipane-api.ts`、`ipane-primitive-api.ts`

**Pane Primitives** 是 lightweight-charts v4 新增的 primitive 类型，**直接附着到 pane 而非 series**：

```javascript
// 旧方式（Series Primitive）—— 需要一个 series
const series = chart.addSeries(LineSeries, {...});
series.attachPrimitive(myDrawing);

// 新方式（Pane Primitive）—— 直接附着到 pane
const pane = chart.panes()[0];
pane.attachPrimitive(myDrawing);
```

#### IPaneApi 接口关键方法
- `pane.attachPrimitive(primitive: IPanePrimitive)` — 附着 pane primitive
- `pane.detachPrimitive(primitive: IPanePrimitive)` — 移除 pane primitive
- `pane.getSeries(): ISeriesApi[]` — 获取 pane 上所有 series
- `pane.paneIndex(): number` — 获取 pane 索引
- `pane.priceScale(priceScaleId: string): IPriceScaleApi` — 获取价格轴（可用于坐标转换！）
- `chart.panes(): IPaneApi[]` — 获取所有 pane

#### IPanePrimitive 接口
```typescript
interface PaneAttachedParameter<HorzScaleItem = Time> {
    chart: IChartApiBase<HorzScaleItem>;  // 图表实例
    requestUpdate: () => void;            // 请求重绘
}

type IPanePrimitive<HorzScaleItem = Time> = IPanePrimitiveBase<PaneAttachedParameter<HorzScaleItem>>;
```

#### IPanePrimitive vs ISeriesPrimitive 对比

| 特性 | ISeriesPrimitive | IPanePrimitive |
|------|-----------------|----------------|
| 附着方式 | `series.attachPrimitive(drawing)` | `pane.attachPrimitive(drawing)` |
| attached 参数 | `{chart, series, requestUpdate}` | `{chart, requestUpdate}` |
| paneViews() | ✅ 支持 | ✅ 支持 |
| priceAxisViews() | ✅ 支持（右侧价格标签） | ❌ 不支持 |
| timeAxisViews() | ✅ 支持（底部时间标签） | ❌ 不支持 |
| priceAxisPaneViews() | ✅ 支持（价格轴区域绘制） | ❌ 不支持 |
| timeAxisPaneViews() | ✅ 支持（时间轴区域绘制） | ❌ 不支持 |
| 依赖 series | ✅ 必须附着到 series | ❌ 直接附着到 pane |
| 坐标转换 | `series.coordinateToPrice()` | `pane.priceScale('right').coordinateToPrice()` |
| 空 series 兼容 | ⚠️ 无数据 series 可能不触发渲染 | ✅ 不依赖 series 数据 |

#### Pane Primitives 对 Drawing 的影响

当前 Drawing 类（HorizontalLine、TrendLine、Box 等）继承 `PluginBase`（实现 `ISeriesPrimitive`）。如果改为 `IPanePrimitive`：

1. **坐标转换**：`series.coordinateToPrice(y)` → `pane.priceScale('right').coordinateToPrice(y)` ✅ 可行
2. **时间转换**：`chart.timeScale()` 不变 ✅
3. **priceAxisViews() 丢失**：HorizontalLine 右侧的价格标签（显示数字）无法显示 ⚠️ 需要用 Canvas 自绘替代
4. **autoscaleInfo() 丢失**：drawing 的价格范围不会影响自动缩放 ⚠️ 可能需要手动处理

#### 两种实现路径

**路径 A：宿主 series 方案（快速修复）**
- 每个 pane 跟踪第一个创建的数据 series 作为"宿主"
- drawing 附着到宿主 series（有数据，一定参与渲染循环）
- 优点：改动小（主要在 Python 端），保留 priceAxisViews
- 缺点：依赖 pane 上有数据 series，reset 后需要重新绑定

**路径 B：Pane Primitives 方案（彻底重构）**
- Drawing 基类从 `PluginBase`（ISeriesPrimitive）改为实现 `IPanePrimitive`
- 使用 `pane.attachPrimitive` 直接附着到 pane
- 坐标转换用 `pane.priceScale('right').coordinateToPrice()`
- 优点：不依赖任何 series，架构更干净
- 缺点：丢失 priceAxisViews（右侧价格标签），需要 Canvas 自绘替代；JS+Python 两端改动大

#### 额外发现：chart.panes() API

`chart.panes()` 返回 `IPaneApi[]`，可以通过索引获取任意 pane 的引用。这比 `chart.addSeries(..., paneIndex)` 更灵活：
- 可以检查 pane 是否存在
- 可以获取 pane 上所有 series
- 可以直接在 pane 上 attach/detach primitive

#### 重要发现：IPriceScaleApi 无坐标转换方法

`IPriceScaleApi` 在 v5.2.0 中**没有** `coordinateToPrice`/`priceToCoordinate` 方法。
坐标转换需要通过 `pane.getSeries()[0]` 获取 pane 上有数据的 series，再用 `ISeriesApi.coordinateToPrice()`。

---

## ✅ Pane Primitive 改造完成（2026-06-28）

### 改造结果

DrawingSeries 从 ISeriesPrimitive 完全改造为 IPanePrimitive，**所有 pane 的 drawing 都可见，ToolBox 正常工作**。

### 核心架构变更

```
旧架构：
Drawing → PluginBase(ISeriesPrimitive) → series.attachPrimitive(drawing)

新架构：
Drawing → PanePluginBase(IPanePrimitive) → pane.attachPrimitive(drawing)
```

### 修改文件清单

| 文件 | 改动 |
|------|------|
| `src/pane-plugin-base.ts` | **新增**，实现 IPanePrimitive 接口 |
| `src/drawing/drawing.ts` | PluginBase → PanePluginBase，_eventToPoint 用 pane.getSeries()[0].coordinateToPrice()，detach 用 pane.detachPrimitive() |
| `src/drawing/pane-view.ts` | series.priceToCoordinate → pane.getSeries()[0].priceToCoordinate |
| `src/drawing/two-point-drawing.ts` | 构造函数新增 pane 第一参数 |
| `src/horizontal-line/horizontal-line.ts` | 构造函数新增 pane，mouseIsOverDrawing 用 pane.getSeries() |
| `src/horizontal-line/pane-view.ts` | series 引用改为 pane.getSeries() |
| `src/horizontal-line/axis-view.ts` | series 引用改为 pane.getSeries() |
| `src/horizontal-line/ray-line.ts` | 构造函数新增 pane，mouseIsOverDrawing 用 pane.getSeries() |
| `src/trend-line/trend-line.ts` | 构造函数新增 pane |
| `src/box/box.ts` | 构造函数新增 pane |
| `src/vertical-line/vertical-line.ts` | 构造函数新增 pane，updatePoints 用 chart.timeScale() |
| `src/vertical-line/pane-view.ts` | series 引用改为 pane.getSeries() |
| `src/drawing/drawing-tool.ts` | this._series → this._pane，attachPrimitive 用 pane |
| `src/general/toolbox.ts` | 构造函数 series → pane，loadDrawings 传 pane |
| `src/general/handler.ts` | createToolBox() 用 chart.panes()[0]，无参数 |
| `lightweight_charts/drawings.py` | JS 构造函数传 pane 引用，attachPrimitive/detachPrimitive 用 pane |
| `lightweight_charts/drawing_series.py` | 移除 _ensure_js_series 和 dummy 数据，仅作 per-pane 管理器 |
| `lightweight_charts/toolbox.py` | createToolBox() 无参数 |

### 已知代价

- HorizontalLine 右侧价格标签（priceAxisViews）暂时丢失（Pane Primitive 不支持）
- 后续可用 Canvas 自绘替代

### 坐标转换方案

由于 `IPriceScaleApi` 无 coordinateToPrice/priceToCoordinate，改用 `pane.getSeries()[0]` 获取 pane 上第一个有数据的 series 做坐标转换。

---

## 🔧 show(wait=N) 回调根因修复（2026-06-28）

### 问题

`show(wait=N)` 模式下 JS 回调永远到不了 Python handler。

### 根因

`show(wait=N)` 只做了 `wv_process.join(timeout=wait)`，**没有运行 `show_async()` 消息循环**，`emit_queue` 永远不被消费。

### 修复

`show(wait=N)` 改为：启动后台超时线程 + 主线程运行 `asyncio.run(show_async())`。

```python
if wait is not None:
    import threading
    def _auto_exit():
        self.wv.wv_process.join(timeout=wait)
        if self.is_alive:
            self.is_alive = False
            self.wv.emit_queue.put('exit')
    threading.Thread(target=_auto_exit, daemon=True).start()
    asyncio.run(self.show_async())
```

---

## 🖱️ 跨 pane 拖拽修复（2026-06-28）

### 问题

鼠标在 Pane 1 时能拖动 Pane 0 的 drawing。

### 根因

`_handleHoverInteraction` 没有检查鼠标是否在当前 drawing 所属的 pane 上。

### 修复方案演进

1. **DOM 方案**（失败）：`pane.getHTMLElement().getBoundingClientRect()` 与 `chart.chartElement()` 比较 → `param.point.y` 是 pane 相对坐标，不是图表绝对坐标
2. **paneIndex + getHeight 累加**（失败）：同上，坐标系不对
3. **MouseEventParams.paneIndex**（成功 ✅）：`param.paneIndex === this.pane.paneIndex()` 直接比较

### 关键发现

`MouseEventParams` 有 `paneIndex` 属性（"The index of the Pane"），**这是判断鼠标在哪个 pane 上的正确方式**。

### 实现

```typescript
protected _isMouseInMyPane(param: MouseEventParams): boolean {
    if (param.paneIndex === undefined) return true;
    return param.paneIndex === this.pane.paneIndex();
}
```

拖拽中不检查边界（让拖拽自由完成），未拖拽时检查边界（防止跨 pane 交互）。

---

## 📏 RayLine 数据范围外拖拽修复（2026-06-28）

### 问题

RayLine 创建在数据范围外或拖动到数据范围外后，再也无法拖动。

### 根因

`_mouseIsOverDrawing` 中 `priceToCoordinate` / `timeToCoordinate` 在数据范围外返回 null，`if (!y || !x) return false` 直接拒绝。

### 修复

坐标转换失败时跳过该坐标的检查，而不是直接返回 false：

```typescript
const yOk = y !== null ? Math.abs(y - param.point.y) < tolerance : true;
const xOk = x !== null ? param.point.x > x - tolerance : true;
return yOk && xOk;
```

---

## 🧰 ToolBox 生命周期与回调系统（2026-06-28）

### ToolBox 生命周期

```
ToolBox.__init__  → _build()    ← 初始创建
reset()           → _delete()   ← 开头销毁一切
                → _build()    ← 结尾重建
reset_sub()       → _delete()   ← 开头销毁一切
                → _build()    ← 结尾重建
```

- `_delete()`：移除 handler + 销毁 JS toolBox + 清空 drawings/drawing_list/on_change
- `_build()`：注册 handler + 创建 JS toolBox

### 回调系统（`+=` / `-=`）

```python
chart.toolbox.on_change += my_func   # 注册
chart.toolbox.on_change -= my_func   # 卸载
```

回调签名：`func(drawings: list[DrawingInfo])`

### DrawingInfo 追踪

ToolBox 内部维护 `_drawing_list: list[DrawingInfo]`，每次 JS `saveDrawings` 触发时自动同步。可通过 `chart.toolbox.drawings_list` 访问。

---

## 🎛️ TopBar 生命周期（2026-07-01）

### TopBar 生命周期

```
TopBar.__init__()  → _created=False, _widgets={}
  ↓ 第一次 widget 调用触发
_create()          → _created=True, JS createTopBar() → handler._topBar + DOM 挂载
  ↓
clear()            → handlers 清理 + _widgets 清空 + JS 重建空容器（_created 不变）
  ↓
_create()          → 无需调用（_created 仍为 True），直接添加新 widget
  ↓
delete()           → 调 clear() + _created=False + JS _div.remove() + _topBar=undefined
  ↓
_create()          → _created=False guard 通过，JS createTopBar() 重建
```

### clear() vs delete()

| 方法 | Python handlers | _widgets | _created | JS DOM | JS _topBar |
|------|----------------|----------|----------|--------|------------|
| `clear()` | ✅ 移除 | ✅ 清空 | ❌ 不变(True) | 🔄 重建空容器 | ❌ 不变 |
| `delete()` | ✅ 移除 | ✅ 清空 | → False | ❌ 移除 | → undefined |

- **clear()**：保留顶栏容器，清空内容。适合"换一批控件"场景
- **delete()**：完全拆除。适合 `reset_sub()` 等需要彻底清理的场景

### clear() 的 JS 实现

```js
// 重建空 left/right 容器，一次性清掉所有 widget 子元素和分隔符
var _l = {id}._div.querySelector('.topbar-container');
var _r = {id}._div.querySelectorAll('.topbar-container')[1];
_l.innerHTML = '';
_r.innerHTML = '';
```

**为什么用 innerHTML='' 而非逐个 remove**：分隔符（`makeSeparator`）创建后未被追踪，无法逐个删除。重建空容器是最干净的方式。

### 回调清理链

```
Widget.__init__(func) → wrapper 闭包捕获 func + topbar
                     → self.win.handlers[self.id] = wrapper

clear()/delete() → self.win.handlers.pop(widget.id)  ← 断开 Python→JS 调用链
                → self._widgets.clear()               ← widget 可 GC → 闭包 GC → func 释放
                → JS innerHTML=''                      ← DOM 销毁 → JS 事件监听器随元素 GC
```

### reset_sub() 中的调用

```python
# 旧：12 行内联清理
# 新：1 行
self.topbar.delete()
```

`delete()` 后 `self.topbar` 对象仍存在（Python 引用未断），用户通过 `widget 方法 → _create()` 复用同一实例重建。

---

## 🔍 Audit 补充（2026-06-28）

### Python 端新增

- `chart` 字段：`interval`、`offset`、`period_locked`
- `volume_oi` 字段：volume/oi 数据状态和数据量
- `toolbox` 字段：`on_change` 回调数、`tracked_drawings` 数、`saved_tags`
- `drawing_series` 字段：每个 pane 的 DrawingSeries 管理器和 drawings 数量

### JS 端新增

- `toolboxDrawings`：ToolBox DrawingTool 中的 drawing 数量
- `toolboxHasOnChanged`：ToolBox onChanged 回调是否已设置
- `paneCount`：图表 pane 数量
- `pane.N.seriesCount`：每个 pane 上的 series 数量
- `pane.N.height`：每个 pane 的高度

---

## ⚠️ __init__ 中引用未创建属性的陷阱（2026-06-28）

### 问题

`abstract.py` 的 `__init__` 中有 `if self.toolbox is not None: self.toolbox._build()` 在 `self.toolbox` 赋值之前，导致 `AttributeError`。

### 教训

**`__init__` 中的重建逻辑必须在属性赋值之后**。reset() 的 `_build()` 逻辑不应复制到 `__init__` 中——`ToolBox.__init__` 已经调用了 `_build()`。

---

## 🧵 show() 消息循环重构（2026-06-28）

### 旧架构

```
show(wait=N) → threading.Thread(_auto_exit) + asyncio.run(show_async())
show(block)  → asyncio.run(show_async())
show_async() → while True: emit_queue.get() + parse_event_message + func()
```

### 新架构

```
Chart.__init__ 末端 → threading.Thread(_message_loop, daemon=True)  ← 守护线程常驻
show(wait=N)        → wv_process.join(timeout=N) + self.exit()      ← 超简单
show(block)         → wv_process.join() + self.exit()
_message_loop()     → while is_alive: emit_queue.get() + parse + func()
```

### 优势

- `show()` 不再依赖 `asyncio.run()`，Jupyter/嵌套调用都能用
- 消息循环守护线程在 init 时启动，一直运行直到 `is_alive = False`
- `show()` 只管 wait/block，逻辑极简
- 异步回调在守护线程中用 `asyncio.run()`（独立线程无 event loop 冲突）

---

## 🐛 Histogram Legend 精度遗漏（2026-06-28 修复）

**Bug**：HistogramSeries 的 legend 值不受 `precision` 约束，显示 `120.1111111111111` 而非 `120.11`

**根因**：`legend.ts` 中 Histogram 走了 `shorthandFormat`（设计给 Volume/OI 用，小数字直接 `toString()` 不做精度截断），而非其他 Series 用的 `legendItemFormat(data.value, format.precision)`

**修复**：删掉 Histogram 的 if 分支，所有 value 类型 series 统一用 `legendItemFormat(data.value, format.precision)`

**教训**：Legend 中添加新的 series 类型支持时，必须检查数值格式化路径是否使用了正确的精度控制函数。

---

## 🧹 v2.8.3 SeriesCommon 代码清理（2026-06-30）

### price_scale 重写
- **改前**：16 个参数的 f-string 拼接 JS，可读性极差
- **改后**：dict 构建 + `js_json()` 序列化，所有参数默认 `None`（不传则用 JS 官方默认值）
- **删死参数**：`perm_width` — 官方 API 无此字段
- **新增参数**：`ensure_edge_tick_marks_visible`
- **互锁参数**：`scale_margin_top` / `scale_margin_bottom` 必须同时指定或同时省略，否则 ValueError
- **CandleSeries.price_scale() 删除**：与 SeriesCommon 完全相同，改为继承

### 废弃别名清理
- **移除** `Line` / `Histogram` 别名 → 用 `LineSeries` / `HistogramSeries`
- **移除** `update_from_tick` / `update_from_ticks` / `update` 别名 → 用 `update_tick` / `update_ticks` / `update_bar`
- **涉及文件**：series.py、abstract.py、__init__.py

### _apply_options 通用方法
- **新增** `SeriesCommon._apply_options(options)` — 统一 `{self.id}.series.applyOptions()` 入口
- 5 处调用收敛到 1 个方法

### 删除冗余子类 delete() override
- 7 个子类（LineSeries/HistogramSeries/VolumeSeries/OpenInterestSeries/CandleSeries/AreaSeries/OHLCBarSeries/BaselineSeries）的 `delete()` 全是 `super().delete()` 纯透传
- 全部删除，直接继承 SeriesCommon.delete()，减少 32 行

---

## 🔧 Toolbox _delete() 顺序陷阱（2026-06-30 修复）

### 问题
`toolbox._delete()` 先移除 Python handler，再调 JS `_cleanup()`。JS 清理过程中触发 `onChanged → saveDrawings → callbackFunction`，消息发到 Python 时 handler 已不存在 → `[Warning] Event handler not found`。

### 修复
**反转顺序**：先 JS 清理（handler 仍在，回调能正常处理），再移除 Python handler。

```python
# 改前（错误顺序）
self._chart.win.handlers.pop(...)   # 1. handler 没了
self.run_script(f'..._cleanup()')   # 2. JS 触发回调 → 找不到 handler

# 改后（正确顺序）
self.run_script(f'..._cleanup()')   # 1. JS 清理，handler 仍在
self._chart.win.handlers.pop(...)   # 2. 安全移除
```

### 关键发现：_clear_handlers() vs _remove_my_handlers()
- **`_clear_handlers()`**：清掉 Window 上**所有图表**的全部 handler，只应由 `reset()` 调用
- **`_remove_my_handlers()`**：用 salt 匹配只移除当前图表的 handler，不影响其他图表
- **教训**：多图表共享 Window 时，绝不能用 `_clear_handlers()`，否则会误杀其他图表的 handler

---

## 📝 series.py price_scale 参数设计模式

### "None = 不覆盖 JS 默认值" 模式
所有参数默认 `None`，不传则 JS 端使用官方默认值。避免 Python 端硬编码与官方不一致的默认值。

### 互锁参数校验
```python
if (scale_margin_top is None) != (scale_margin_bottom is None):
    raise ValueError('scale_margin_top 和 scale_margin_bottom 必须同时指定')
```

### _apply_price_scale_options 已废弃
曾经创建了 `_apply_price_scale_options` helper，后发现可以直接调用 `self.price_scale()` 复用，不需要额外抽象。

---

---

## 📊 VolumeSeries 数据管线重构（2026-06-30）

### 新增纯函数工具（util.py）

| 函数 | 职责 | 参数 |
|------|------|------|
| `merge_volume_by_time(df, is_tick)` | volume 专用合并 | bar 模式：value→last, open→first, close→last；tick 模式：value→sum, open/close→from price |
| `filter_old_bars(df, last_bar_time)` | 单调检查 + 丢弃旧数据 | 纯函数，无状态 |

### merge_volume_by_time 设计

- **bar 模式** (`is_tick=False`)：输入 time/value/open/close，value 取 last（去重，非 sum）
- **tick 模式** (`is_tick=True`)：输入 time/value/price，value 取 sum，open/close 从 price 生成
- 两种模式输出统一：time/value/open/close
- 所有输入列必须存在，缺失抛 ValueError

### normal_df 增强

新增 `required_cols` 参数：选列 + 校验一步到位。注意传入 tuple 时需 `list()` 转换，否则 pandas 会解释为多级列索引。

### VolumeSeries.update_bars 流程

```
输入 df (time/value/open/close)
  │
  ├─ _df_cleaned=False → normal_df + merge_volume_by_time(bar模式)
  └─ _df_cleaned=True  → 跳过
  │
  └─ filter_old_bars → 丢弃 time < _last_bar.time 的行
  │
  ├─ 首批数据 → setData 批量写入
  └─ 后续数据 →
      ├─ 新数据第一行时间 == self.data 最后一行时间 →
      │   ├─ _cumulative_volume=True → volume 累加（旧值+新值），open 保留旧值
      │   └─ _cumulative_volume=False → 直接覆盖
      │   └─ 替换最后一行
      └─ 时间不同 → 追加到末尾
```

### VolumeSeries.update_ticks 流程

```
输入 tick (time/value/price)
  │
  ├─ normal_df(tick_required_cols)
  └─ merge_volume_by_time(is_tick=True) → 聚合同时间戳 tick
  │
  └─ update_bars(_cumulative_volume=True)
      └─ tick 落在最后一条 bar → volume 累加
      └─ tick 落在新时间 → 追加
      └─ tick 落在非最后 bar → filter_old_bars 丢弃
```

### 关键设计决策

- `filter_old_bars` 始终执行（即使 `_cumulative_volume=True`）
- `_cumulative_volume` **只在最后一条 bar 时间匹配时生效**
- bar 模式 value 用 `last` 而非 `sum`（去重，非累加）
- `_prepare_vol_df` 已删除，职责由 `normal_df(required_cols)` + `merge_volume_by_time` 替代

###踩坑记录

- **pandas tuple 选列**：`df[('a','b')]` 被解释为多级列索引，需 `df[list(cols)]`
- **assert Index == list**：返回 boolean array 无法评估，需 `assert list(idx) == list(lst)`
- **tick 路径不需要 time_to_bar_time**：tick 数据已对齐，只有 bar 路径需要

---

## 📐 数据管线统一（2026-06-30）

### 目标
将 VolumeSeries 成熟的数据管线模式（纯函数链 + filter_old_bars）移植到 CandleSeries 和 SeriesCommon，实现三种 series 的管线结构对称。

### 新增纯函数

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `merge_candle_by_time(df, is_tick)` | bar: `time,O,H,L,C` / tick: `time,value` | `time,O,H,L,C` | OHLC 聚合（high=max, low=min） |
| `merge_volume_by_time(df, is_tick)` | bar: `time,value,O,C` / tick: `time,value,price` | `time,value,O,C` | volume 聚合（value=sum） |
| `merge_value_by_time(df)` | `time,[O,H,L,C,vol,OI,...]` | 保持原列结构 | 通用聚合（vol=sum, OI=last） |

### CandleSeries 改造

| 方法 | Before | After |
|------|--------|-------|
| `set()` | 内联全部逻辑 | `clear_data()` + `update_bars()` + markers |
| `update_bars()` | `_clean_df` + 内联 mask | `normal_df` + `merge_candle_by_time` + `filter_old_bars` + 选列 |
| `update_ticks()` | 内联 groupby + 手写 OHLC | `merge_candle_by_time(is_tick=True)` + `update_bars(_df_cleaned=True)` |

### SeriesCommon 改造

| 方法 | Before | After |
|------|--------|-------|
| `set()` | 内联 setData + 清空 | `clear_data()` + `update_bars()` |
| `update_bars()` | 3 层嵌套调用 | 一气呵成（清洗→校验→更新） |
| `update_ticks()` | 内联 groupby(last) + 手写校验 | `merge_value_by_time()` + `tick_required_cols` 校验 |

### 删除的函数
- `_check_has_value_column` → 内联到 `update_bars`
- `_prepare_line_data` → 内联到 `update_bars`
- `_clean_update_bars` → 内联到 `update_bars`
- `_clean_df` → 死代码，由用户删除

### AbstractChart 简化
- `set()` / `update_bars()` 中 vol_cols 构建：循环+条件 → 直接列表 `['time','volume','open','close']`
- `set()` 委托 `update_bars()`，不再重复列选择逻辑
- `set()` 中 `toolbox.clear_drawings()` 加 `is not None` guard

### 关键设计决策

#### `_time_to_bar_time` 只在 SeriesCommon 保留
- **SeriesCommon**（Line/Histogram）：独立使用时需要时间对齐 → 保留
- **CandleSeries** / **VolumeSeries**：独立使用时不需要时间对齐，由 AbstractChart 统一负责 → 不加
- **原则**：原始有的保留，新加的不加，guard 全删

#### `update = update_bar` 别名已废弃
- 旧代码有 `update = update_bar` 类级别别名
- 现已删除，测试代码统一改为 `update_bar()`

#### CandleSeries.update_bars 选列时机
- AbstractChart 传入的 df 包含 volume/OI 等额外列
- 选列 `df[bar_required_cols]` 必须在 assert 之前，否则 `list(df.columns) != bar_required_cols` 会误报

### 兼容性破坏
| 变更 | 影响 | 迁移 |
|------|------|------|
| `update()` 别名删除 | 调用 `series.update(bar)` 报 AttributeError | 改为 `series.update_bar(bar)` |
| `marker()` → `add_marker()` | 调用 `chart.marker(...)` 报 AttributeError | 改为 `chart.add_marker(...)` |
| `marker_list()` → `add_markers()` | 调用 `chart.marker_list([...])` 报 AttributeError | 改为 `chart.add_markers([...])` |
| `_check_has_value_column` 删除 | 无外部调用者 | 无需迁移 |
| `_prepare_line_data` 删除 | 无外部调用者 | 无需迁移 |
| `_clean_update_bars` 删除 | 无外部调用者 | 无需迁移 |
| `_clean_df` 删除 | 无外部调用者 | 无需迁移 |
| `set(keep_drawings=True)` 参数删除 | `AbstractChart.set()` 不再接受 | 始终清空 drawings |

---

*最后更新：2026-07-01（CandleSeries OHLC 合并修复）*

---

## 🏷️ Legend 分组功能（2026-07-01）

### 需求
同组的 series 在 legend 中显示在同一行，行前有 ♦ 组开关可一键控制组内所有指标显示/隐藏。组内顺序用创建顺序，显示组名。

### Python API
```python
# group 参数贯穿所有 create_* 方法
sma20 = chart.create_line('SMA 20', color='yellow', group='MA')
ema50 = chart.create_line('EMA 50', color='cyan', group='MA')
rsi   = chart.create_line('RSI', color='purple')  # 无组，独立行
```

### Legend 渲染结构
```
OHLC + Volume + %                        ← candle legend
♦ MA    ■ SMA 20 : 190  👁    ■ EMA 50 : 181  👁    ← 组行（group='MA'）
♦ MOM   ■ ROC 10 : 1.8  👁    ■ MOM 10 : 3.2  👁    ← 组行（group='MOM'）
■ BB Mid 20 : 186  👁                                    ← 独立行（无 group）
■ ATR 14 : 10  👁                                        ← 独立行（无 group）
♦ OSC   ■ RSI 14 : 44  👁    ■ %K 14 : 48  👁          ← 组行（pane 1）
■ Williams %R : -51  👁                                  ← 独立行（pane 1）
■ CCI 20 : -7  👁                                        ← 独立行（pane 1）
```

### 交互行为
- **♦ 组开关 click**：一键切换组内所有 series 的 `visible`，同步更新组名图标（♦→♢）和所有个人眼睛图标
- **个人眼睛 click**：切换单个 series 可见性，同步更新组开关状态（全关则组开关关）
- **跨 pane 分组**：允许同名 group 跨 pane，组开关控制所有同名 series

### 核心架构
```
LineElement { group: string | null, individualOn: boolean, row: HTMLDivElement | null }
GroupElement { row, groupToggle, groupNameSpan, elements[], on, individualOnList[] }

makeSeriesRow(name, series, paneIndex, group=null):
  ├─ group == null → 独立行（原行为）
  └─ group != null → _groups[group] 存在则追加，不存在则 _renderGroupRow 创建组行
```

### 删除时的组内清理（JS 端）
删除组内 series 时：从 `_groups[group].elements` 移除 → 从组行移除 DOM → 组空则删组行 + 清理 `_groups[groupName]`

### 修改文件
| 文件 | 改动 |
|------|------|
| `src/general/legend.ts` | LineElement +group/individualOn、GroupElement 接口、_groups 字典、makeSeriesRow 分组渲染、_renderGroupRow、_updateToggleIcon、_rerenderContainer、delete 组内清理 |
| `src/general/handler.ts` | 6 个 create*Series 加 group 参数 |
| `src/general/styles.css` | `.legend-group-row` / `.legend-group-toggle` 样式 |
| `lightweight_charts/series.py` | SeriesCommon.__init__ +group、所有子类透传、delete() JS 组内清理 |
| `lightweight_charts/abstract.py` | 7 个 create_* 加 group 参数 + 透传 |
| `examples/39_legend_group/` | 分组功能完整演示 |

### 教训
- `takeScreenshot()` 只截 canvas，不含 legend DOM 覆盖层
- legend 是 DOM 元素（绝对定位在 handler.div 上），需要桌面截图才能看到

---

## 🖱️ ToolBox 跨 Pane 绘图（2026-07-01）

### 需求
ToolBox UI 固定在 Pane 0，但绘图可落在任意 pane 上。用户点击哪个 pane，drawing 就创建在那个 pane 上。

### 实现方案：MouseEventParams.paneIndex

利用 lightweight-charts 的 `MouseEventParams.paneIndex`（点击事件自带），在 `DrawingTool._onClick` 中解析目标 pane。

### 修改文件

| 文件 | 改动 |
|------|------|
| `src/drawing/drawing-tool.ts` | 新增 `_resolvePane(param)` 方法，从 `param.paneIndex` 解析目标 pane；`_onClick` 在创建 drawing 前更新 `this._pane` 到目标 pane |
| `src/general/toolbox.ts` | `saveDrawings` 序列化附加 `paneIndex: d.pane.paneIndex()` |
| `lightweight_charts/toolbox.py` | `DrawingInfo` 新增 `pane_index`/`start_time`/`start_price`/`end_time`/`end_price` 字段；`_on_callback` 解析 `paneIndex` |
| `lightweight_charts/series.py` | `CandleSeries.__init__` 补上缺失的 `group` 参数（顺带修复已有 bug） |
| `test/run_tests.py` | 补上漏掉的 `test_volume_series.py` |
| `examples/40_toolbox_multi_pane/` | 3 pane 示例（K线 + Histogram + RSI），ToolBox 跨 pane 绘图 |

### DrawingInfo 完整字段

```python
DrawingInfo:
    id           # 唯一标识
    type         # 绘图类型（HorizontalLine, TrendLine, Box, ...）
    pane_index   # 所在 pane 索引
    start_time   # 起点时间（秒级时间戳，可能为 None）
    start_price  # 起点价格（可能为 None）
    end_time     # 终点时间（可能为 None）
    end_price    # 终点价格（可能为 None）
    points       # 原始点列表（dict，含 time/logical/price）
    options      # 绘图选项（颜色、线宽等）
```

### 关键设计
- **UI 路径**：`DrawingTool._onClick` 读取 `param.paneIndex` → `chart.panes()[paneIndex]` → 在该 pane 上创建 drawing
- **编程路径**：DrawingSeries 工厂方法不变（仍用 `pane_index` 参数）
- **序列化**：JS `saveDrawings` 每个 drawing 附加 `paneIndex` → Python `_on_callback` 解析

### Bug 修复：CandleSeries 缺失 group 参数
- **根因**：`create_candle_series(group=...)` 传 `group` 给 `CandleSeries.__init__`，但 `__init__` 不接受此参数
- **修复**：`CandleSeries.__init__` 加上 `group: str = None`，透传给 `SeriesCommon.__init__`
- **教训**：新增参数时，调用链上每个环节都要检查

---

## 🔧 v2.8.5 HtmlTabChart 多 tab legend/candle 修复（2026-07-01）

### 问题
HtmlTabChart 切换 tab 后，第一个 tab 的 legend/candle 正常，第二个及后续 tab 出现：
1. candle 不可见
2. legend 完全静态（数字不跳动，但眼睛图标能正常显隐 series）
3. line series 可见（因为每个 tab 独立创建）
4. legend 只显示眼睛图标，没有 series 名字

### 根因（三层）
1. **JS 全局变量残留**：`updateChart(id)` 清空容器（DOM 销毁），但 `window.{prefix}_candle` 等全局变量仍指向旧的已销毁 series 对象
2. **series 不重建**：`_build()` 只在 `__init__` 中调用一次，后续 tab 的 `set()` 操作不存在的 JS 对象
3. **handler 引用过期**：`handler.series` 指向旧 series → `legendHandler` return → legend 静态

### 修复（三文件配合）
| 文件 | 改动 |
|------|------|
| `widgets.py` `get_html()` | 切换 tab 前 `delete window.{prefix}_candle/volume/oi` 清理旧全局变量 |
| `series.py` × 3 `_build()` | `if (!{self.id})` 防重复创建 |
| `abstract.py` `set()` | 开头调 `_build()` + handler 引用赋值，确保每个 tab 都重建 series |
| `legend.ts` `makeSeriesRow()` | div 初始内容 `■ 系列名`（解决只有眼睛图标的问题） |

### 教训
- **HtmlTabChart 多 tab**：所有 tab 共享同一 Python 对象，`__init__` JS 只在第一个 tab
- **JS 全局变量生命周期**：清空 DOM ≠ 清理 JS 全局变量，需显式 `delete`
- **`_build()` 必须可重入**：多 tab 场景需 JS 端条件判断防重复
- **`set()` 要自包含**：不能假设 series 已存在，每次 `set()` 都要确保就绪

---

## 🆕 HtmlTabChart new_window 命令重放重构（2026-07-01）

### 问题
`new_window()` 手动调 `candle._build()`、`volume._build()`、`oi._build()`、`toolbox._build()`，每次新增组件都需同步更新。

### 方案：init 快照 + 重放
- `__init__` 末尾保存 `self._init_html = self._html`（init 阶段全量 JS 快照）
- `new_window()` 直接 `self._html = self._init_html` 重放完整 init 命令

### 效果
| 方面 | 改前 | 改后 |
|------|------|------|
| 覆盖范围 | candle + vol + oi + toolbox | ✅ **全部 init 组件自动覆盖** |
| 新增组件支持 | ❌ 需手动 _build | ✅ 自动覆盖 |
| 介入复杂逻辑 | 6 行手动 _build | 0 行，零介入 |
| 代码量 | 11 行 | 5 行 |

---

## 🐛 HtmlTabChart + ToolBox 图表全背景色修复（2026-07-01）

### 根因
`window.callbackFunction` 在静态 HTML 中**未定义**。`DrawingTool` 初始化时订阅 chart 事件，执行过程中调用了 `callbackFunction`，抛出 `TypeError: window.callbackFunction is not a function`，导致：
- `async function updateChart()` 的 Promise 被 reject
- `setData([])` + `update()` 等数据加载代码**未执行**
- 图表创建成功但数据为 0 → 显示为全背景色

### 修复（升级到基类）
`widgets.py` 中两处配合修复：
1. **基类** `StaticLWC.__init__`：`self.run_script('window.callbackFunction = function(){};')` — 所有静态图表自动生效
2. **安全网** `HtmlTabChart.get_html()` 保留相同代码，双重保险

**为什么升级到基类**：检查发现，`HTMLChart`、`JupyterChart`、`StreamlitChart` 等所有继承 `StaticLWC` 的静态图表，只要启用 `toolbox=True` 都会触发相同错误。基类修复一劳永逸。

### 验证
- ✅ `HtmlTabChart` + toolbox: data=50, tb=true
- ✅ 多 tab (new_window) + toolbox: 两 tab 各 50 数据、toolbox 正常
- ✅ 切换 tab 完美恢复
- ✅ `HTMLChart` + toolbox: 同样正常

### ReflexChart 特殊处理
`ReflexChart` 也继承 `StaticLWC`，但它是**动态图表**（通过 iframe + postMessage 与 Reflex 应用通讯）。

**关键区别**：`ReflexChart._build_html()` 主动设置了 `callbackFunction` 为真正的 postMessage 桥接函数。但 `StaticLWC.__init__` 的 `function(){}` 在 IIFE 内部执行，会覆盖这个真正的函数。

**修复**：将 `messaging` 代码块移到 IIFE 之后执行，确保 `function(){}` 只在初始化期间生效，之后由真正的通讯函数接管。

**执行顺序**：
```
IIFE 执行 → callbackFunction = function(){}（安全初始化）
         → 图表代码执行（createToolBox 等）
IIFE 完成
messaging 执行 → callbackFunction = postMessage 桥 ✅（接管通讯）
```

### ReflexChart _html 内存泄漏修复
**问题**：`ReflexChart.run_script` 调用 `super().run_script()`（即 `StaticLWC.run_script`），每次动态更新都追加到 `self._html`，**永不清理**。

**影响**：1 次/秒更新 → 8.5 MB/天增长。长期运行（特别是高频 Tick 数据）会撑爆内存。

**修复**：引入 `_html_frozen` 标志：
- `__init__` 中设为 `False`
- `to_reflex()` 生成 iframe 后设为 `True`
- `run_script` 中检查：已冻结则跳过 `super().run_script()`，只追加到 `_pending`

**数据流**：
```
初始化阶段:  run_script → _html ✅ + _pending ✅
to_reflex(): 生成 iframe → _html_frozen = True
动态更新:     run_script → _html ❌(已冻结) + _pending ✅
flush():                  _pending → postMessage → 清空
```

**效果**：`_html` 恒定在 ~28 KB，`_pending` 每次 `flush()` 后清空，内存零增长。

---

## 🎯 v2.8.6 API 补全（2026-07-01）

### 新增功能

#### 1. AbstractChart._apply_options(options)
- **用途**：通用图表选项设置入口
- **位置**：`abstract.py`
- **调用方式**：`chart._apply_options({'layout': {'background': {'color': '#000'}}})`
- **说明**：内部方法，与 Series 级别的 `_apply_options()` 对称

#### 2. TimeScaleApi 时间轴 API
- **用途**：封装 `chart.timeScale()` 的完整 API
- **位置**：`util.py`
- **调用方式**：`chart.time_scale_api()` 返回 `TimeScaleApi` 实例
- **主要方法**（14个）：
  - 滚动控制：`scroll_position()`, `scroll_to_position()`, `scroll_to_real_time()`
  - 范围管理：`get_visible_range()`, `set_visible_range()`, `get_visible_logical_range()`, `set_visible_logical_range()`
  - 视图控制：`fit_content()`, `width()`
  - 事件订阅：`subscribe_visible_logical_range_change()`, `subscribe_visible_time_range_change()`, `subscribe_size_change()`
- **复用**：`AbstractChart.fit()` 和 `set_visible_range()` 内部调用此 API

#### 3. build_price_scale_options() 纯函数
- **用途**：将 Python snake_case 参数转换为 JS 驼峰格式的选项字典
- **位置**：`util.py`
- **调用方式**：`build_price_scale_options(auto_scale=True, mode='normal')`
- **说明**：供 `SeriesCommon.price_scale()` 和 `PriceScaleApi.apply_options()` 复用

#### 4. PriceScaleApi 价格轴 API
- **用途**：封装 `chart.priceScale()` 的完整 API
- **位置**：`util.py`
- **调用方式**：`chart.price_scale_api(scale_id)` 返回 `PriceScaleApi` 实例
- **主要方法**（6个）：
  - 选项管理：`apply_options(**kwargs)`, `options()`
  - 范围控制：`get_visible_range()`, `set_visible_range()`, `set_auto_scale()`
  - 尺寸获取：`width()`
- **复用**：`AbstractChart.price_scale(scale_id, **kwargs)` 内部调用此 API

### 设计决策

1. **单例模式 vs 方法调用**：选择方法调用（每次返回新实例），更简洁，无需缓存
2. **API 命名**：`time_scale_api()` 和 `price_scale_api(scale_id)`，与官方库命名风格一致
3. **位置**：API 类放在 `util.py`，避免 `abstract.py` 过于臃肿
4. **向后兼容**：新增功能，不影响现有代码
5. **纯函数复用**：`build_price_scale_options()` 供 Series 和 Chart 两级 API 共用，避免代码重复
6. **方法复用**：`AbstractChart.fit()` 和 `set_visible_range()` 内部调用 `TimeScaleApi`，减少重复代码
7. **price_scale 重构**：`AbstractChart.price_scale()` 从委托到 `candle.price_scale()` 改为使用 `PriceScaleApi`，支持指定价格轴 ID

---

*最后更新：2026-07-01（TimeScaleApi & PriceScaleApi 实现）*
