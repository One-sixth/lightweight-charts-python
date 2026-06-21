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

## 🏗️ 架构概览（v2.7.0）

### 类层次

```
Pane (util.py)
├── Window (abstract.py)           ← JS 桥接层
├── SeriesCommon (abstract.py)     ← 数据系列基类（数据工具、标记、精度、显隐）
│   ├── CandleSeries               ← K 线（OHLC + 样式 + tick 聚合）
│   ├── Line                       ← 折线
│   ├── Histogram                  ← 柱状图
│   ├── VolumeSeries               ← 成交量（独立系列，OHLC 着色）
│   └── OpenInterestSeries         ← 持仓量（独立系列）
└── AbstractChart (abstract.py)    ← 图表容器（组合模式）
    ├── self.candle: CandleSeries       ← 固定 ID: window.Chart_X_candle
    ├── self.volume: VolumeSeries | None ← 固定 ID: window.Chart_X_volume
    ├── self.oi: OpenInterestSeries | None ← 固定 ID: window.Chart_X_oi
    ├── self._lines / _drawings / _tables
    └── 28+ 委托方法
```

### 关键设计

1. **固定 ID**：主 series 使用 `Chart_X_candle`/`volume`/`oi`，不被 IDGen 生成，audit 能捕获
2. **惰性创建**：Handler 构造函数 `this.series`/`volumeSeries`/`openInterestSeries` 全部 null
3. **按需重建**：`reset()` 删光 JS 对象，`set()` 检测 None 后按固定 ID 重建
4. **`@property` 代理**：`candle_data`/`data`/`markers`/`_last_bar` 有 None 保护
5. **时间级别**：`_interval`/`offset`/`_period_locked` 在 AbstractChart 上
6. **绘图方法只在 AbstractChart**：不在 SeriesCommon
7. **`update_from_ticks` 双层设计**：SeriesCommon 通用版 + CandleSeries 覆盖版
8. **`_is_subchart` 标识**：`reset()`/`_clear_handlers()` 限制仅主图可调用

---

## 🛠️ 开发流程

### 新增 JS 功能
1. 在 `src/general/handler.ts` 中添加方法
2. 更新 `GLOBALS_RE`（audit 正则）和 `SKIP_KEYS`（audit 跳过列表）
3. 注意：`createLineSeries`/`createHistogramSeries` 的 `dontAddList` 参数 — volume/OI 创建时传 `true` 跳过 `_seriesList`，避免审计计数污染
4. 执行 `npx rollup -c rollup.config.js` 编译
5. 复制 `dist/bundle.js` → `lightweight_charts/js/bundle.js`

### 新增 Python 功能
1. 在 `lightweight_charts/abstract.py` 中添加类/方法
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
python test/test_candle_series.py    # CandleSeries 6 个测试
python test/run_tests.py             # 完整测试套件（test_cleanup + test_features + test_util）
```

---

## 📁 项目结构

```
lightweight-charts-onesixth/
├── lightweight_charts/         ← Python 后端
│   ├── abstract.py             # 核心类: Window, SeriesCommon, AbstractChart, CandleSeries, Line, Histogram, VolumeSeries, OpenInterestSeries, PriceLine
│   ├── util.py                 # 工具: Pane, IDGen, Events, 纯函数, 类型别名
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
│   ├── test_candle_series.py   # CandleSeries 6 个测试
│   ├── test_cleanup.py         # 资源清理 + 多图表 + reset 测试
│   ├── test_features.py        # 功能测试
│   └── test_util.py            # 工具函数测试
├── examples/                   ← 示例 (35 个)
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
2. 检查 `seriesMarkers` 是否已创建（`_update_markers` 会动态创建）
3. 所有 Series 都支持标记

### reset 后 set 失败
1. 检查 `self.candle` 是否为 None（reset 后应为 None）
2. `set()` 会自动检测并按固定 ID 重建 candle/volume/oi
3. `@property` 有 None 保护，直接访问 `chart.candle_data` 安全

### 绘图/控件回调失效
1. 检查是否误调了 `_clear_handlers()`（见上方"禁止手动调用"规则）
2. 检查 handler 是否被 `_remove_my_handlers()` 误删
3. 用 `print(chart.win.handlers)` 查看当前注册的 handler 列表

---

## 📋 测试覆盖

| 测试 | 覆盖内容 |
|------|---------|
| `test_basic_create_delete` | 创建/设置数据/标记/删除/Python 状态清理 + JS audit |
| `test_update_operations` | update 单 bar/update 已有 bar/update_batch 批量/set 重置 |
| `test_markers` | marker 显式时间/marker 默认时间/marker_list 批量/remove/clear + JS 验证 |
| `test_multi_pane` | 多 pane 独立 K 线/各自数据和标记/独立更新/独立删除 |
| `test_candle_with_main` | 主 K 线 + CandleSeries + Line + Histogram 混合资源清理 |
| `test_options` | 自定义颜色/边框/影线/价格线参数 + JS 验证 |
| `test_cleanup.py` | 资源全链路创建/删除 + JS TOML 审计 + 多图表清理 + reset + **handlers 检查区分 toolbox/non-toolbox** |
| `test_features.py` | 数据列重命名/line 追踪/截图/topbar 事件 |
| `test_util.py` | 工具函数测试（13 个） |
