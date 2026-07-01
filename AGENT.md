# AGENT.md - Agent 操作指南

本文件指导 AI Agent 如何在 lightweight-charts-onesixth 项目中安全高效地工作。

---

## 🔴 最高优先级规则

### ⚠️ run_script 必须加 `;0`
所有通过 `run_script` 执行的 JS 代码，如果返回值可能包含 lightweight-charts API 对象（ISeriesApi/IChartApi 等），**必须在末尾加 `;0`**。否则 pywebview 的 `evaluate_js` 会永久卡死。

### ⚠️ 消息循环不能终止
修改 `chart.py` 消息循环时，异常处理中**绝对不能有 `return`**。只能跳过当前消息，让循环继续。

### ⚠️ return_queue 值必须是简单类型
`evaluate_js` 返回值必须 `str()` 转换后再 `put` 到 `return_queue`。

### ⚠️ 禁止手动调用 _clear_handlers()
`_clear_handlers()` 是**内部方法**，仅供 `reset()` 调用，不应手动调用！

原因：
- 它会清空 **整个 Window** 上所有图表的**全部** handler — ToolBox 的 `save_drawings`、TopBar 控件回调、JSEmitter 事件回调、hotkey 回调等全部丢失
- `reset()` 调用后会立即恢复主图的 ToolBox handler，但其他 handler 不会恢复
- 多子图场景中，所有子图的 handler 也会被一并清掉

**如果确实需要清理特定图表的 handler**，使用 `_remove_my_handlers()` 精确清除，不要用 `_clear_handlers()` 全量清空。

---

## 🏗️ 架构概览（v3.0）

### 类层次

```
Pane (util.py)
├── Window (abstract.py)           ← JS 桥接层
├── SeriesCommon (series.py)       ← 数据系列基类（数据工具、标记、精度、显隐）
│   ├── LineSeries                 ← 折线（继承全部 set/update_bars/update_ticks）
│   ├── HistogramSeries            ← 柱状图（同上，额外支持 _option_columns=['color']）
│   ├── VolumeSeries               ← 成交量（覆盖 _prepare_vol_df/update_bars/update_ticks，OHLC 着色）
│   ├── OpenInterestSeries         ← 持仓量（仅 __init__/_build/config，其余全部继承 SeriesCommon）
│   └── CandleSeries               ← K 线（覆盖 set/update_bars/update_ticks，OHLC 聚合）
└── AbstractChart (abstract.py)    ← 图表容器（组合模式）
    ├── self.candle: CandleSeries       ← 固定 ID: window.Chart_X_candle
    ├── self.volume: VolumeSeries       ← 固定 ID: window.Chart_X_volume（始终存在）
    ├── self.oi: OpenInterestSeries     ← 固定 ID: window.Chart_X_oi（始终存在）
    ├── self._lines / _drawings / _tables
    └── 委托方法
```

### 统一的系列输入契约

所有系列的 `set()` / `update_bars()` / `update_ticks()` 统一接受 `time` + `value` 列：

| 方法 | 输入列 | 说明 |
|------|--------|------|
| `series.set(df)` | `time, value` | 统一格式 |
| `series.update_bars(df)` | `time, value` | 统一格式 |
| `series.update_ticks(df)` | `time, value` | 统一格式 |

特殊要求：
- **VolumeSeries**：`_prepare_vol_df` 要求 `open`/`close` 列用于涨跌着色，缺失时抛 `ValueError`
- **VolumeSeries `self.data`**：维护 `time, value, open, close, color` 五列
- **CandleSeries**：`set`/`update_bars` 要求 `open, high, low, close` 列

### AbstractChart 接口

| 方法 | 输入列 | 说明 |
|------|--------|------|
| `chart.set(df)` | `time, open, high, low, close, [volume], [open_interest]` | bar 数据 |
| `chart.update_bars(df)` | 同上 | bar 数据 |
| `chart.update_ticks(df)` | `time, price, [volume], [open_interest]` | tick 数据 |
| `chart.data` | 返回 `time, open, high, low, close, volume, open_interest` | 始终 7 列 |
| `chart.candle_data` | 返回 `time, open, high, low, close` | candle 原始数据 |
| `chart.vol_data` | 返回 `time, value` | volume 原始数据（仅两列） |
| `chart.oi_data` | 返回 `time, value` | OI 原始数据 |

AbstractChart 内部自动做列重命名：`price→value`、`volume→value`、`open_interest→value` 后转发给各系列。

### set → update_bars 委托模式

SeriesCommon / VolumeSeries / OpenInterestSeries 统一使用此模式：

```python
def set(self, df, _df_cleaned=False):
    self.run_script(f"{self.id}.series.setData([])")
    self.data = pd.DataFrame()
    self._last_bar = None
    if df is None or df.empty:
        return
    self.update_bars(df, _df_cleaned)
    if self.markers:
        self._update_markers()

def update_bars(self, df, _df_cleaned=False):
    df = self._prepare_xxx(df, _df_cleaned)  # 清洗 + 校验 + 选列
    if df is None or df.empty:
        return
    if self.data is None or self.data.empty:
        # 首批 → setData 批量写入（高效）
        self.data = df.copy()
        self.run_script(f'{self.id}.series.setData({js_data(df)})')
    else:
        # 后续 → per-row update
        js_commands = [...]
        self.data = pd.concat([self.data.iloc[:-1], df], ...)
        self._last_bar = df.iloc[-1]
```

### 关键设计

1. **固定 ID**：主 series 使用 `Chart_X_candle`/`volume`/`oi`，不被 IDGen 生成，audit 能捕获
2. **常驻系列**：candle/volume/oi 始终存在，reset 后自动重建
3. **`@property` 代理**：`candle_data`/`vol_data`/`oi_data`/`data`/`markers`
4. **`normal_df` 精简**：不再自动转小写，不再自动 `date→time`，只做时间转换
5. **绘图方法只在 AbstractChart**：不在 SeriesCommon
6. **`_is_subchart` 标识**：`reset()`/`_clear_handlers()` 限制仅主图可调用
7. **seriesMarkers 按需创建**：由 `_update_markers()` 在 series 级别按需创建
8. **不联动 _lines**：AbstractChart 的 set/update_bars/update_ticks 不自动转发数据给 Line/Histogram

---

## 🛠️ 开发流程

### 新增 JS 功能
1. 在 `src/general/handler.ts` 中添加方法
2. 更新 `GLOBALS_RE`（audit 正则）和 `SKIP_KEYS`（audit 跳过列表）
3. 注意：`createLineSeries`/`createHistogramSeries` 的 `dontAddList` 参数 — volume/OI 创建时传 `true` 跳过 `_seriesList`，避免审计计数污染
4. 执行 `npx rollup -c rollup.config.js` 编译
5. 复制 `dist/bundle.js` → `lightweight_charts/js/bundle.js`

### 新增 Python 功能
1. 在 `lightweight_charts/series.py` 或 `abstract.py` 中添加类/方法
2. 如果涉及 `run_script` 调用，检查返回值是否包含 API 对象
3. 更新 `lightweight_charts/__init__.py` 导出
4. 创建示例 `examples/XX_name/`
5. 创建测试 `test/test_name.py`

### 编译命令
```bash
cd D:\Data\github_repo\lightweight-charts-onesixth
npx rollup -c rollup.config.js
copy dist\bundle.js lightweight_charts\js\bundle.js
```

### 测试命令
```bash
cd D:\Data\github_repo\lightweight-charts-onesixth
python test/run_tests.py             # 完整测试套件（7 个测试文件）
```

---

## 📁 项目结构

```
lightweight-charts-onesixth/
├── lightweight_charts/         ← Python 后端
│   ├── abstract.py             # 核心类: Window, AbstractChart
│   ├── series.py               # 系列类: SeriesCommon, LineSeries, HistogramSeries, VolumeSeries, OpenInterestSeries, CandleSeries
│   ├── util.py                 # 工具: Pane, IDGen, Events, normal_df, 纯函数
│   ├── chart.py                # Chart (pywebview) + CrossProcessChart
│   ├── widgets.py              # JupyterChart, HTMLChart, HtmlTabChart, QtChart
│   ├── drawings.py             # Drawing 基类 + HorizontalLine, TrendLine, Box, VerticalLine, RayLine, VerticalSpan
│   ├── js/bundle.js            # 编译后前端
│   └── __init__.py             # 导出
├── src/                        ← TypeScript 前端
│   ├── general/handler.ts      # Handler 类 (核心)
│   ├── general/legend.ts       # 图例
│   └── general/toolbox.ts      # 绘图工具箱
├── test/                       ← 测试
│   ├── test_cleanup.py         # 资源清理 + 多图表 + reset 测试
│   ├── test_features.py        # 功能测试
│   ├── test_util.py            # 工具函数测试
│   ├── test_candle_series.py   # CandleSeries 测试
│   ├── test_data_aggregation.py # 数据聚合测试（含混沌测试）
│   ├── test_reset_sub.py       # 子图重置测试
│   ├── test_position.py        # 布局位置测试
│   └── run_tests.py            # 测试运行器
├── examples/                   ← 示例 (36 个)
├── MEMORY.md                   # 项目长期记忆
└── AGENT.md                    # 本文件
```

---

## 🔍 调试技巧

### run_script_and_get 超时
1. 先检查是否加了 `;0`（最常见原因）
2. 检查 JS 函数是否抛异常（查看消息循环日志）
3. 检查 `_return_q` 是否初始化

### audit 不返回
1. 检查 `chart.py` 消息循环是否有 `return` 终止了循环
2. 检查 `evaluate_js` 返回值类型
3. 用 `run_script_and_get('Lib.Handler.audit()')` 单独测试

### 标记不显示
1. 检查 `_update_markers` 是否有 try/catch 保护
2. `seriesMarkers` 由 `_update_markers()` 按需创建（首次调用时自动创建）
3. 检查 `_marker_auto_scale` 是否正确传递
4. 所有 Series 都支持标记

### reset 后 set 失败
1. 检查 `self.candle` 是否为 None（reset 后应为 None）
2. `set()` 会自动检测并按固定 ID 重建 candle/volume/oi
3. `@property` 有 None 保护，直接访问 `chart.candle_data` 安全

### 绘图/控件回调失效
1. 检查是否误调了 `_clear_handlers()`（见上方"禁止手动调用"规则）
2. 检查 handler 是否被 `_remove_my_handlers()` 误删
3. 用 `print(chart.win.handlers)` 查看当前注册的 handler 列表

### VolumeSeries 着色异常
1. 检查输入是否包含 `open`/`close` 列（必需）
2. AbstractChart 自动转发时会带上 `open`/`close`
3. 独立创建 VolumeSeries 时，`set(df)` 的 df 必须包含 `time, value, open, close`

---

## ⚠️ 已废弃的旧名称（保留兼容）

| 旧名称 | 新名称 | 说明 |
|--------|--------|------|
| `Line` | `LineSeries` | 类重命名 |
| `Histogram` | `HistogramSeries` | 类重命名 |
| `update_from_tick()` | `update_tick()` | 方法重命名 |
| `update_from_ticks()` | `update_ticks()` | 方法重命名 |

旧名称保留为别名/转发包装器，但已标记废弃，将在未来版本移除。

---

## 📋 测试覆盖

| 测试 | 覆盖内容 |
|------|---------|
| `test_cleanup.py` | 资源全链路创建/删除 + JS TOML 审计 + 多图表清理 + reset + handlers 检查 |
| `test_features.py` | 数据列处理 + Line 创建和追踪 + 截图 + topbar 事件 |
| `test_util.py` | 工具函数测试（13 个） |
| `test_candle_series.py` | CandleSeries 创建/更新/标记/多 pane/混合系列/样式 |
| `test_data_aggregation.py` | 多频率 set/update_bar/update_bars/update_ticks/重复时间戳合并/纯函数/跨级别聚合/混沌测试/边界情况 |
| `test_reset_sub.py` | 子图内容重置 + 数据隔离 + 重置后重用 |
| `test_position.py` | 网格布局位置解析 + 经典模式 |
