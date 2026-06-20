# Changelog

所有重要的项目更改都将记录在此文件中。

---

## [v2.7.0] - 2026-06-21

### 核心架构变更

#### 固定 ID + 按需重建
- **主 series 使用固定 ID**：`window.Chart_1_candle` / `window.Chart_1_volume` / `window.Chart_1_oi`
  - ID 不由 IDGen 自动生成，但 audit 的 `GLOBALS_RE`（`Chart_\d` 前缀）能正确捕获
  - 删除后按同名重建，JS 全局变量名一致
- **Handler 构造函数惰性创建**：`this.series`/`this.volumeSeries`/`this.openInterestSeries`/`this.seriesMarkers` 全部设为 `null`
  - 由 Python 端 AbstractChart.__init__ 创建后通过 JS 脚本设置 Handler 引用
- **`reset()` 彻底清理**：删除 candle/volume/oi 的 JS 对象和 Python 状态，Handler 引用设为 null
- **`set()` 按需重建**：检测 `self.candle`/`self.volume`/`self.oi` 为 None 时按固定 ID 重建
- **`_wrap_handler` 删除**：不再需要，直接用 `_fixed_id` 参数创建

#### VolumeSeries / OpenInterestSeries 独立化
- **构造函数参数 `candle` → `chart`**：不再绑定 CandleSeries，只依赖 AbstractChart
- **`_wrap_existing` 参数删除**：不再区分"包装"和"独立"模式
- **`self._candle` 依赖移除**：`self._candle._normal_df()` → `self._normal_df()`（继承自 SeriesCommon）
- **OHLC 着色保留**：有 `open`/`close` 列时自动着色，否则用默认 `_down_color`
- **`price_scale_id` 参数暴露**：VolumeSeries/OI Series 的 `__init__` 支持自定义价格尺度 ID
- **AbstractChart 直接管理**：`self.volume`/`self.oi` 由 AbstractChart 创建和管理，不再通过 `candle.attach_volume()`

#### CandleSeries 清理附属逻辑
- **`_attached` 列表删除**：CandleSeries 不再管理附属 series
- **`attach_volume`/`attach_open_interest` 删除**：由 AbstractChart 直接管理
- **`delete()` 不再级联**：只删除自身，不删除 volume/oi
- **`clear_data()` 不再级联**：只清自身数据
- **`_toggle_data()` 不再遍历**：只控制自身显隐
- **`set()` 不再自动转发**：volume/oi 数据由 AbstractChart.set() 转发
- **`volume_config()`/`open_interest_config()` 委托**：改为委托到 `self._chart.volume`/`self._chart.oi`

#### SeriesCommon 纯函数提取
- `_normal_df` / `merge_value_by_time` / `get_df_interval_offset` / `time_to_bar_time` 提取到 `util.py`
- SeriesCommon 中保留薄委托

#### 时间级别迁移至 AbstractChart
- `_interval`/`offset`/`_period_locked` 从 SeriesCommon 迁移到 AbstractChart
- `_set_interval`/`_time_to_bar_time`/`_single_datetime_format`/`set_period` 只在 AbstractChart 定义
- SeriesCommon 中的 `_time_to_bar_time`/`_single_datetime_format` 委托到 `self._chart`
- `set()` 中 `_set_interval` 在 `normal_df` 之后调用
- SeriesCommon.set() 增加初始化检查

#### 其他改进
- **`_update_markers` 统一 try-catch**：SeriesCommon 中升级，CandleSeries 删除冗余覆盖
- **`VerticalSpan` 修复**：参数 `series` → `chart`，时间处理统一用 `_single_datetime_format`，新增参数校验
- **`_is_subchart` 属性**：`reset()`/`clear_handlers()` 限制仅主图可调用
- **`remove_subchart` 清理**：JS 端遍历 window 全局变量，删除引用子图表 series 的 VolumeSeries/OI
- **`@property` None 保护**：`candle_data`/`data`/`markers`/`_last_bar` 在 `self.candle` 为 None 时返回安全默认值
- **test_cleanup.py**：新增 `test_reset_cleanup()` 验证 reset 后 series 全部删除再重建；WARN 改为 FAIL

### 新增示例
- `examples/35_line_markers/` — Line 和 Histogram 上的标记演示

---

## [v2.6.1] - 2026-06-16

### Fixed

- **pywebview `evaluate_js` 无法序列化 lightweight-charts API 对象**: JS 函数返回包含 ISeriesApi/IChartApi 等对象的结构时，`evaluate_js` 永久卡死，导致 `run_script_and_get` 超时
  - 修复: Python 端 `run_script` 调用末尾加 `;0`，阻止返回值传播
  - 影响: `CandleSeries`、`Line`、`Histogram` 等所有通过 `run_script` 创建的 series
- **消息循环异常处理终止整个消息处理**: `chart.py` 消息循环中 `KeyError` 和 `Exception` 的 `return` 会终止消息循环，导致后续消息全部丢失
  - 修复: `KeyError` 和未知 `Exception` 改为 `break` + `put(None)` + 输出 `[FATAL]` 错误信息；`JavascriptException` 继续循环
- **CandleSeries 标记不显示**: `_update_markers()` 未添加 try/catch 保护，JS 错误中断 async IIFE 执行链
  - 修复: `CandleSeries._update_markers()` 添加 try/catch 防御

### Changed

- **示例 34**: 新增 `examples/34_candle_series/` — CandleSeries 独立K线系列演示（静态/实时/批量更新）
- **测试**: 新增 `test/test_candle_series.py` — 6 个测试用例覆盖创建/删除/update/markers/多pane/混合资源/审计验证

---

## [v2.6.0] - 2026-06-16

### Added

- **`CandleSeries` 独立K线系列**: 在任意 pane 上绘制独立 K 线（无 volume/open interest），适用于参考K线、对比K线等场景
  - `AbstractChart.create_candle_series()` 工厂方法，支持 name/pane_index/up_color/down_color/price_line/price_label 等参数
  - `CandleSeries.set()` 设置初始 OHLC 数据
  - `CandleSeries.update()` 更新最新一根 bar 或追加新 bar
  - `CandleSeries.update_batch()` 批量更新多根 bar
  - `CandleSeries.marker()` 在独立 K 线上打标记
  - `CandleSeries.delete()` 删除系列并清理 JS 对象
  - JS 端新增 `Handler.createCandleSeries()` 方法，调用 `chart.addSeries(CandlestickSeries, ...)`，注册到 `_seriesList` 和 `legend`
  - `_update_markers()` 添加 try/catch 防御，防止 JS 错误中断 async IIFE 执行链
- **`sync_id` 组同步 API**: 全新的基于组名的图表同步机制，替代旧的 `sync=chart.id` 配对同步
  - 所有 `AbstractChart` 子类（`Chart`、`HtmlTabChart`、`HTMLChart`、`StreamlitChart`、`JupyterChart`、`WxChart`、`QtChart`）统一支持 `sync_id` 和 `sync_crosshairs_only` 参数
  - `Chart.__init__` 新增 `sync_id` 参数，主图表可直接加入同步组
  - `join_sync_group()` 方法：任意图表可运行时动态加入同步组
  - `_normalize_sync_id()` 静态方法：统一校验 `sync_id` 输入（仅允许 `str`/`None`/`True`/`False`）
  - 同步组规则：同组所有图表互相同步十字光标；时间范围仅在 `sync_crosshairs_only=False` 的图表间同步
  - `reset_sub()` 后同步自动恢复（`_syncGroup` 属性保留组名）

### Breaking Changes

- **`sync` 参数重命名为 `sync_id`，语义从"链式传递 chart.id"改为"组名字符串"**:
  - **旧 API（v2.5.x 及更早）**: `create_subchart(sync=chart.id)` — 传入目标图表的 ID（如 `window.Chart_1`），建立 A↔B 两点之间的配对同步关系
  - **新 API（v2.6.0）**: `create_subchart(sync_id='main')` — 传入任意组名字符串，所有使用相同组名的图表自动互相同步，无需知道彼此的 ID
  - 主图表加入同步组: `Chart(sync_id='main')` 或 `chart.join_sync_group('main')`
  - `True` 会被转为字符串 `'True'` 作为组名，`False`/`None` 表示不同步
  - 传入非 `str`/`None`/`True`/`False` 类型会抛出 `TypeError`
  - **迁移示例**:
    ```python
    # 旧写法（v2.5.x）
    chart = Chart(...)
    sub = chart.create_subchart(sync=chart.id)  # 传入 chart.id

    # 新写法（v2.6.0）
    chart = Chart(..., sync_id='main')  # 主图表加入 'main' 组
    sub = chart.create_subchart(sync_id='main')  # 子图加入同一组
    ```
- **`syncChartsAll` 不再直接使用**: 内部同步重建改用 `syncGroup` 按 `_syncGroup` 分组重建

### Changed

- **JS 端 `joinSyncGroup` 简化**: 移除 `startsWith('window.')` 兼容处理和 `window[id]` fallback，直接通过 `Handler._all.find()` 匹配
- **`_unsync_all` 重写**: 从复杂的 4 步配对拆解简化为 2 步（清空所有回调 → 按 `_syncGroup` 分组重建）
- **QUICK_REFERENCE.md 更新**: 同步部分全面替换为新的 `sync_id` 组同步 API 文档

---

## [v2.5.3] - 2026-06-15

### Fixed

- **HtmlTabChart 多子图布局溢出修复**: 修复 `create_subchart()` 在 HtmlTabChart 中布局溢出的问题
  - `setupGridLayout`: 容器高度 `100vh` → `100%`，跟随父元素而非视口
  - `reSize()` grid 模式: 去掉 HtmlTabChart 特殊分支，统一用 `wrapper.getBoundingClientRect()` 获取实际尺寸
  - `_createChart()`: 初始高度减去 nav 栏高度，避免首次渲染溢出

- **操作柄双击重置修复**: 修复绝对定位模式下操作柄双击重置后图表尺寸异常的问题
  - 根因：拖拽操作柄写入 px 高度，双击时混合使用百分比恢复导致尺寸错乱
  - 修复：首次拖拽时备份 `wrapper.style.height` 原始值，双击时从备份恢复
  - 涉及 `handler.ts` 三处修改：新增 `_originalHeight` 属性、`mousedown` 时备份、`dblclick` 时恢复

### Changed

- **`HTMLChart.export(filename)`**: 重写 `export()` 方法，直接接受 `filename` 参数，不再需要调用内部 `_export()`
- **示例 32 全面重写**:
  - `html_chart_example.py`: 2 subcharts × 2 panes 布局（K线+Volume × 2）
  - `html_tab_chart_demo.py`: 3 个策略 tab（Subcharts T/B + Panes T/B + Absolute Position）
  - 演示 `create_subchart()` + `pane_index` + `set_position()` 三种布局方式

---

## [v2.5.2] - 2026-06-15

### Added

- **StaticLWC 及其子类新参数支持**: 为 `StaticLWC`、`StreamlitChart`、`JupyterChart`、`HTMLChart`、`HtmlTabChart` 添加 `AbstractChart` 的新参数支持
  - 新增参数: `position`（网格位置）、`pane_index`（面板索引）、`marker_auto_scale`（标记自动缩放）
  - 确保参数完整传递链: 子类 → `StaticLWC` → `AbstractChart`
  - 更新示例 `32_html_tab_chart` 展示新参数使用

### Changed

- **QUICK_REFERENCE.md 文档更新**: 更新 `HTMLChart` 和 `HtmlTabChart` 示例，展示新参数使用
- **示例代码更新**: `examples/32_html_tab_chart/html_tab_chart_demo.py` 添加新参数示例

---

## [v2.5.1] - 2026-06-10

### Added

- **HtmlTabChart iframe 嵌入示例**: 新增示例 `32_html_tab_chart` 中的 iframe 嵌入演示，展示如何将 HtmlTabChart 嵌入其他 HTML 页面
  - 采用双文件方案：外壳 HTML + 图表内容 HTML，通过 `<iframe src="...">` 引用
  - 记录了多种单文件方案（srcdoc/data:base64/blob/Shadow DOM/innerHTML）的失败原因
- **reset_sub()**: 新增子图内容重置功能，清除子图全部内容但保留布局，不影响其他子图，reset 后可重用
  - 清除范围：K线数据、折线/柱状图系列、价格线、标记、绘图、表格、ToolBox、TopBar、Legend、Events、sync、handlers
  - 新增示例 `33_reset_sub`，演示 4 子图网格 + 主图 reset + 独立子图 + 十字光标同步恢复
  - 新增测试 `test_reset_sub.py`，自动化验证 Python + JS 双端资源清理
- **Table div 归属修复**: Table 不再追加到全局容器，改为追加到所属图表的 div，修复多子图表格重叠问题
- **syncChartsAll 回调存储**: crosshair 和 range 回调现在被正确存储到 `_syncCallbacks` 中，支持后续清理和重建

### Changed

- **syncChartsAll 保护检查**: `target.legend?.div` 检查仅保护 `legendHandler` 调用，不再阻断 `setCrosshairPosition`
- **DrawingTool/ContextMenu 访问权限**: `_chart`、`_clickHandler`、`_moveHandler`、`_onRightClick`、`div` 改为 public，支持 ToolBox 清理
- **ToolBox 构造函数**: 存储 `_contextMenu` 和 `_undoHandler` 引用，支持精确清理

### Fixed

- **syncChartsAll 回调未存储**: 匿名回调改为命名变量并存储到 `_syncCallbacks['__crosshairAll']`/`['__rangeAll']`，支持 unsubscribe
- **_unsync_all 只处理部分回调**: 改为遍历所有 `_syncCallbacks` 条目统一清理，兼容 `syncCharts` 和 `syncChartsAll` 两种模式
- **_rebuildSync 排除 reset 子图**: reset_sub 后改为调用 `syncChartsAll` 全量重建，不排除任何子图
- **setCrosshairPosition 异常中断**: 用 try-catch 包裹，空数据图表异常不影响其他图表的十字光标同步
- **Table div 追加到全局容器**: 移除 Table JS 构造函数中的 `window.containerDiv.appendChild`，由 Python 端控制追加位置

---

## [v2.4.2] - 2026-06-07

### Added

- **HtmlTabChart**: 新增多策略 Tab 切换图表，支持多策略切换、交易明细、绩效指标展示
  - 改自 [smalinin/bn_lightweight-charts-python](https://github.com/smalinin/bn_lightweight-charts-python) 的 HtmlChart_BN
  - 新增示例 `32_html_tab_chart`
  - 支持技术指标（SMA、布林带）、买卖标记、图例显示
  - 使用专用标记 `html-tab-chart-marker` 实现自适应高度计算

### Changed

- **API 重命名**: `StaticLWC.load()` → `export()`，`_load()` → `_export()`
- **HTMLChart**: 移除 `filename` 构造参数，改为 `export(filename)` 方法
- **HtmlTabChart**: 移除 `filename` 构造参数，改为 `export(filename)` 方法
- **ReflexChart**: `load()` → `export()`，`_load()` → `_export()`

### Fixed

- **HtmlTabChart 多策略代码丢失**: 修复 `_prepare_html()` 只遍历历史策略，遗漏当前策略的问题
- **HtmlTabChart UTF-8 编码**: 修复 HTML 文件写入时的 `UnicodeEncodeError`
- **marker API 参数格式**: 修复 `position` 和 `shape` 参数使用错误格式导致标记不显示的问题
- **HtmlTabChart X 轴刻度被裁剪**: 修复图表高度计算错误导致 X 轴刻度不可见的问题
- **HtmlTabChart 滚动条**: 修复页面出现滚动条的问题，改用 flexbox 布局

---

## [v2.4.1] - 2026-05-28

### Added

- **图表同步功能**: `create_subchart()` 新增 `sync` 参数，支持多图表同步时间轴和十字光标
- **图表同步示例**: 新增示例 `31_chart_sync`，演示 `sync` 和 `sync_crosshairs_only` 参数的使用
- **表格组件改进**: `create_table()` 支持 `height=None` 和 `width=None` 实现自动适应内容大小
- **网格布局系统**: `position` 参数支持三种格式：整数（如 `111`）、元组（如 `(2,2,1)`）、字符串（已弃用）
- **运行时位置控制**: 新增 `get_position()` 和 `set_position()` 方法，支持动态调整图表位置
- **相对大小控制**: `width`/`height` 参数相对于网格单元，支持内缩（<1.0）和侵占（>1.0）
- **网格冲突检测**: 自动检测同一窗口中图表网格规格冲突，防止布局混乱，抛出清晰的 `ValueError` 异常
- **测试整合**: 将根目录测试文件整合到 `tests/` 文件夹，统一管理测试用例
- **文档完善**: 添加详细的网格布局与冲突处理说明到 API 参考文档

### Changed

- **表格 position 参数变更**: `create_table()` 的 `position` 参数字符串输入已废弃，输入任何字符串等效于输入 `(0, 0)`，会发出 `DeprecationWarning`
- **表格位置处理逻辑**: 统一 position 参数处理，移除重复的类型检查
- **Table 类默认位置**: 默认值从 `'left'` 改为 `(0, 0)`
- **position 参数弃用警告**: `parse_position()` 对字符串输入发出 `DeprecationWarning`，推荐使用数字格式
- **代码优化**: 重构 `parse_position()` 和 `_convert_string_to_grid()` 函数，使用字典映射替代 if-elif 链，提高代码可维护性
- **参数重命名**: `sync_id` 重命名为 `sync`，更符合 Python 命名规范

### Fixed

- **表格布局问题**: 修复了表格内容不显示、表头与表内容重叠的问题
- **表格拖动区域问题**: 修复了表格可拖动区域过大超出表格大小的问题
- **回调 KeyError**: 修复了表格点击时 `KeyError: 'null'` 的问题
- **表格样式修复**: 添加 `overflowWrapper.style.flex = '1'` 和 `overflowWrapper.style.minHeight = '0'`
- **代码质量**: 清理了多处 TODO 注释，添加了详细说明和类型定义
- **Rollup 编译警告**: 修复了 TypeScript 类型错误，解决 `example.ts` 和 `toolbox.ts` 的编译警告

### Deprecated

- **表格 position 字符串**: `create_table()` 的 `position` 参数不再支持字符串（`'left'`, `'right'`, `'top'`, `'bottom'`），建议使用相对坐标元组格式 `position=(x, y)`
- **字符串 position 格式**: `parse_position()` 对字符串输入发出弃用警告，推荐使用数字格式（如 `121`）或元组格式（如 `(1, 2, 1)`）

---

## [v2.3.3] - 2026-05-25

### Added

- **实时数据流式更新**: 支持直接从 tick 数据更新 K 线
- **多面板图表**: 使用 `create_subchart()` 创建子图
- **工具箱**: 在图表上直接绘制趋势线、矩形、射线、水平线
- **事件系统**: 时间周期选择器、搜索、快捷键等
- **表格组件**: 用于自选股、下单、持仓管理
- **Polygon.io 集成**: 直接获取市场数据
- **成交量 + 持仓量叠加**: 独立 Y 轴缩放
- **多 Chart 实例**: 完全独立的图表对象
- **常驻图例**: 鼠标移出图表时 OHLC 仍可见
- **垂直区间高亮**: 半透明填充标记日期范围
- **资源清理 API**: `reset()`、`clear_handlers()`、`audit()`、`delete()`
- **PriceLine 对象**: `create_price_line().delete()`
- **Table.delete()**: 销毁表格并清理 JS 状态
- **人类可读的 ID**: `window.Chart_1`、`window.Line_3` 等
- **资源审计**: `chart.audit(use_js=True)` 返回完整 TOML 格式的 JS 变量状态
- **全面的清理测试**: test_cleanup.py 验证所有资源类型的 Python + JS 无泄漏
- **序列批量更新 API**: `Line/Histogram.update_batch()` 高性能批量更新
- **K 线批量更新**: `chart.update_bars()/update_from_ticks()`
- **跨进程嵌入 Qt**: `CrossProcessChart` 通过原生窗口句柄将 pywebview 窗口嵌入 QWidget

### Supported Environments

- PySide6
- PyQt6
- wxPython
- asyncio
- Reflex

---

## 约定

- `Added`: 新增功能
- `Changed`: 现有功能的变更
- `Deprecated`: 即将移除的功能
- `Removed`: 已移除的功能
- `Fixed`: 修复的 bug
- `Security`: 安全相关的修复
