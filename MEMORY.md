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

## 🏗️ v2.7.0 架构：组合模式 + 固定 ID

### 类层次

```
Pane (util.py)
├── Window (abstract.py)           ← JS 桥接层
├── SeriesCommon (abstract.py)     ← 数据系列基类
│   ├── CandleSeries               ← K 线（OHLC + volume/OI + tick 聚合）
│   ├── Line                       ← 折线
│   ├── Histogram                  ← 柱状图
│   ├── VolumeSeries               ← 成交量（独立系列）
│   └── OpenInterestSeries         ← 持仓量（独立系列）
└── AbstractChart (abstract.py)    ← 图表容器（组合模式）
    ├── self.candle: CandleSeries       ← 固定 ID: window.Chart_1_candle
    ├── self.volume: VolumeSeries | None ← 固定 ID: window.Chart_1_volume
    └── self.oi: OpenInterestSeries | None ← 固定 ID: window.Chart_1_oi
```

### AbstractChart 组合模式

```python
class AbstractChart(Pane):  # 不再继承 Candlestick
    # __init__ 中：
    base = self.id.replace('window.', '')
    self.candle = CandleSeries(self, _fixed_id=f'window.{base}_candle')
    self.volume = VolumeSeries(self, _fixed_id=f'window.{base}_volume')
    self.oi = OpenInterestSeries(self, _fixed_id=f'window.{base}_oi')
```

- **固定 ID**：主 series 使用 `Chart_1_candle`/`volume`/`oi`，不被 IDGen 生成，但 audit 能捕获
- **惰性创建**：Handler 构造函数 `this.series`/`volumeSeries`/`openInterestSeries` 全部 null
- **按需重建**：`reset()` 删光 JS 对象，`set()` 检测 None 后按固定 ID 重建
- **属性代理**：`candle_data`/`data`/`markers`/`_last_bar` 用 `@property`（None 保护）
- **时间级别**：`_interval`/`offset`/`_period_locked` 在 AbstractChart 上，所有 series 共享

### 职责划分

| 类 | 职责 |
|---|------|
| **SeriesCommon** | 数据工具（`_normal_df` 等）、标记（`marker` 等）、精度、显隐 |
| **CandleSeries** | K 线数据（OHLC）、样式配置（`candle_style`）、tick 聚合 |
| **VolumeSeries** | 成交量数据、OHLC 着色、独立配置/删除 |
| **OpenInterestSeries** | 持仓量数据、独立配置/删除 |
| **AbstractChart** | 图表容器、绘图（`horizontal_line` 等）、子图管理、同步、数据转发 |

### 关键设计决策

1. **固定 ID + 按需重建**：reset 后彻底干净，set 时按固定 ID 重建
2. **绘图方法在 AbstractChart 上**：`horizontal_line`/`trend_line`/`box` 等只在 AbstractChart 定义
3. **`candle_style`/`volume_config`/`open_interest_config` 在 CandleSeries 上**
4. **`update_from_ticks` 双层设计**：SeriesCommon 通用版（取 last）+ CandleSeries 覆盖版（OHLC 聚合）
5. **`_is_subchart` 属性**：`reset()`/`clear_handlers()` 限制仅主图可调用
6. **`remove_subchart` 清理**：JS 端遍历 window 全局变量，删除引用子图表 series
7. **`_fixed_id` 参数**：所有 Series 支持，跳过 IDGen 自动生成

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
| `lightweight_charts/abstract.py` | AbstractChart 组合重构、VolumeSeries、OpenInterestSeries、CandleSeries 增强、Candlestick 删除、固定 ID、reset/set 重建、**`_marker_auto_scale` 存储与 `_update_markers()` 使用**、**移除 Handler 级别 `seriesMarkers` 赋值** |
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

## 🐛 update_batch/update_from_ticks 不转发 volume/OI（2026-06-21 修复）

### 问题
v2.7.0 组合架构重构后，`AbstractChart.update_batch(df)` 只委托给 `self.candle.update_batch(df)`，后者只处理 OHLC 列，volume/OI 数据被静默丢弃。`set()` 正确转发了 volume/OI，但 `update()`/`update_batch()`/`update_from_ticks()` 遗漏了。

### 影响
- `chart.update_bars(df)` — volume 不更新（用户在 examples/34_candle_series/3_batch_update.py 中发现）
- `chart.update_from_ticks(df)` — volume 不更新
- `chart.update_from_tick(series)` — volume 不更新

### 修复
1. **`update()`/`update_batch()`**：新增 volume/OI 转发给 `self.volume`/`self.oi`
2. **`update_from_ticks()`**：重写——先聚合 volume/OI 转发给独立 series，再剥离 volume/OI 列交给 CandleSeries 处理 OHLC（避免重复聚合）
3. **`update_from_tick()`**：委托给 `update_from_ticks()` 统一处理
4. **`update_bar`/`update_bars` 别名**：从 `property(lambda: self.candle.xxx)` 改为普通方法，委托给 `update()`/`update_batch()`

### 教训
- **property 别名陷阱**：`update_bars = property(lambda self: self.candle.update_batch)` 直接绑定 CandleSeries 方法，绕过了 AbstractChart 的转发逻辑。改为普通方法委托更安全
- **`update_from_ticks` 不可简单转发**：CandleSeries 内部已有 tick→bar 聚合逻辑（含 volume），直接转发会导致 volume 重复聚合。必须剥离 volume/OI 列后再交给 CandleSeries

---

*最后更新：2026-06-21 晚间（v2.7.2 volume 转发修复）*
