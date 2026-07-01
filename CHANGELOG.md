# Changelog

所有重要的项目更改都将记录在此文件中。

---

## [v2.8.6] - 2026-07-01

### Changed

- **HtmlTabChart `new_window()` 重构为 init 快照重放**：
  - `__init__` 末尾保存 `self._init_html = self._html`（init 阶段全量 JS 命令快照）
  - `new_window()` 直接 `self._html = self._init_html` 重放完整 init 命令
  - 删除 6 行手动 `_build()`/`run_script`/`toolbox._build()` 代码
  - 自动覆盖所有 init 组件（candle/volume/oi/toolbox + 未来新增）

### Fixed

- **HtmlTabChart + ToolBox 图表全背景色**：
  - **根因**：`window.callbackFunction` 在静态 HTML 中未定义。`DrawingTool` 初始化时触发回调调用，抛出 `TypeError`，导致 `setData`/`update` 等数据加载代码未执行，图表数据为 0。
  - **修复**：`get_html()` 开头加 `window.callbackFunction = function(){};`，静态 HTML 无需与 Python 通信。

### Modified Files

| 文件 | 改动 |
|------|------|
| `lightweight_charts/widgets.py` | `__init__` 加快照 + `new_window()` 重放 + `get_html()` 加 `callbackFunction` 空函数 |

---

### Fixed

- **HtmlTabChart 多 tab legend/candle 修复**：切换 tab 后第二个及后续 tab 的 candle 不可见、legend 静态不更新。
  - **根因**：`updateChart(id)` 清空容器但不清除 JS 全局变量（`window.{prefix}_candle/volume/oi`），新 Handler 创建新 chart 后 series 全局变量仍指向旧的已销毁对象。`_build()` 只在 `__init__` 中调用一次，后续 tab 的 `set()` 无法重建 series。
  - **修复**：`get_html()` 切换 tab 前先 `delete` 旧全局变量；`_build()` 加 `if (!{id})` 防重复；`set()` 开头调 `_build()` + handler 引用赋值。
- **HtmlTabChart legend 只显示眼睛图标**：`makeSeriesRow` 创建的 div 为空，只在 `legendHandler`（crosshair 移动）中才填充。后续 tab 切换后 crosshair 未触发，div 一直空着。修复：创建 div 后立即设置初始内容 `■ 系列名`。

### Modified Files

| 文件 | 改动 |
|------|------|
| `lightweight_charts/widgets.py` | `get_html()` 新增切换 tab 前清理旧全局变量 |
| `lightweight_charts/series.py` | CandleSeries/VolumeSeries/OpenInterestSeries `_build()` 加 `if (!{self.id})` |
| `lightweight_charts/abstract.py` | `set()` 开头调 `_build()` + handler 引用赋值 |
| `src/general/legend.ts` | `makeSeriesRow()` 设置 div 初始内容 |

---

## [v2.8.4] - 2026-07-01

### Added

- **ToolBox 跨 Pane 绘图**：ToolBox UI 固定在 Pane 0，但鼠标点击哪个 pane 就在哪个 pane 上创建 drawing。利用 `MouseEventParams.paneIndex` 自动识别点击目标 pane。
- **`DrawingInfo` 增强**：新增 `pane_index`、`start_time`、`start_price`、`end_time`、`end_price` 字段，回调信息更完整。

### Fixed

- **`CandleSeries` 缺失 `group` 参数**：`create_candle_series(group=...)` 传 group 但 `CandleSeries.__init__` 不接受，导致 `TypeError`。已补上并透传给 `SeriesCommon.__init__`。

### Changed

- **`test/run_tests.py`**：补上遗漏的 `test_volume_series.py`（8/8 test suites）。

### Modified Files

| 文件 | 改动 |
|------|------|
| `src/drawing/drawing-tool.ts` | 新增 `_resolvePane(param)`；`_onClick` 解析目标 pane |
| `src/general/toolbox.ts` | `saveDrawings` 附加 `paneIndex` |
| `lightweight_charts/toolbox.py` | `DrawingInfo` 增加 pane_index + time/price 字段 |
| `lightweight_charts/series.py` | `CandleSeries.__init__` 补 `group` 参数 |
| `test/run_tests.py` | 加入 `test_volume_series.py` |
| `examples/40_toolbox_multi_pane/` | 3 pane ToolBox 示例 |

---

## [v2.8.3] - 2026-06-30

### Breaking Changes

- **`Line` / `Histogram` 别名已移除**：使用 `LineSeries` / `HistogramSeries` 代替。
- **`update_from_tick()` / `update_from_ticks()` 已移除**：使用 `update_tick()` / `update_ticks()` 代替。
- **`update = update_bar` 别名已移除**：使用 `update_bar()` 或 `update_bars()` 代替。
- **`price_scale()` 参数 `perm_width` 已移除**：官方 API 中不存在此字段。
- **ToolBox 方法移除**：`save_drawings_under()`、`load_drawings()`、`import_drawings()`、`export_drawings()` 已移除。使用 `on_change` 回调自行实现持久化。

### Changed

- **`SeriesCommon.price_scale()` 重写**：f-string 拼接改为 dict 构建 + `js_json()` 序列化，可读性和可维护性大幅提升。同时修复了 `borderColor`/`textColor` 引号拼接 bug（旧代码未对值加引号）。
- **`SeriesCommon.price_scale()` 参数默认值改为 `None`**：所有参数不再硬编码默认值，不传则由 JS 端使用官方默认值。`scale_margin_top` / `scale_margin_bottom` 互锁：必须同时指定或同时省略。
- **`CandleSeries.price_scale()` 删除**：与 `SeriesCommon.price_scale()` 完全相同，改为直接继承，减少 ~60 行重复代码。
- **`price_scale()` 新增参数 `ensure_edge_tick_marks_visible`**：始终在价格轴顶部和底部绘制刻度线。
- **ToolBox `_delete()` 顺序修复**：先 JS 清理再移除 Python handler，避免 JS 清理过程中触发的回调找不到 handler。
- **子类冗余 `delete()` 清理**：7 个子类的 `delete()` 纯透传 override 全部删除，直接继承 SeriesCommon。
- **`_apply_options()` 通用方法**：SeriesCommon 新增 `_apply_options(options)` 统一 `series.applyOptions()` 入口。
- **测试修复**：`_clear_handlers()` → `_remove_my_handlers()`，避免多图表场景误杀其他图表的 handler。

### Migration Guide

| 旧 API | 新 API |
|--------|--------|
| `Line(...)` | `LineSeries(...)` |
| `Histogram(...)` | `HistogramSeries(...)` |
| `series.update_from_tick(s)` | `series.update_tick(s)` |
| `series.update_from_ticks(df)` | `series.update_ticks(df)` |
| `chart.update_from_tick(s)` | `chart.update_tick(s)` |
| `chart.update_from_ticks(df)` | `chart.update_ticks(df)` |
| `series.update(s)` | `series.update_bar(s)` |
| `chart.update(s)` | `chart.update_bar(s)` |
| `chart.price_scale(perm_width=N)` | 已删除，无替代 |
| `chart.toolbox.save_drawings_under(w)` | 用 `on_change` 回调自行实现 |
| `chart.toolbox.load_drawings(tag)` | 用 `on_change` 回调自行实现 |
| `chart.toolbox.import_drawings(path)` | 用 `on_change` 回调自行实现 |
| `chart.toolbox.export_drawings(path)` | 用 `on_change` 回调自行实现 |

> **注意**：`price_scale()` 参数默认值从硬编码值改为 `None`。如果你依赖旧默认值（如 `border_visible=False`、`scale_margin_top=0.2`），需要显式传入。

---

## [v2.8.2] - 2026-06-28

### Breaking Changes

- **ToolBox 回调重构**：新增 `chart.toolbox.on_change += func` / `-= func` 回调注册方式。回调签名为 `func(drawings: list[DrawingInfo])`。旧的 `save_drawings_under` 持久化机制已在 v2.8.3 移除。
- **Ctrl+Z 撤销移除**：ToolBox 不再监听 Ctrl+Z 撤销快捷键。
- **ToolBox 生命周期**：`_cleanup()` 方法已移除，改用 `_delete()`（销毁）/ `_build()`（重建）模式。

### Added

- **Pane Primitive 架构**：Drawing 从 `ISeriesPrimitive` 改为 `IPanePrimitive`，直接附着到 pane 而非 series。
  - 新文件 `src/pane-plugin-base.ts`：实现 `IPanePrimitive` 接口
  - 所有 pane 的 drawing 都可见，不再依赖 series 数据状态
  - 坐标转换通过 `pane.getSeries()[0].coordinateToPrice()` 实现
- **ToolBox on_change 回调系统**：`_CallbackList` 支持 `+=` / `-=` 注册/卸载多个回调
- **ToolBox DrawingInfo 追踪**：`chart.toolbox.drawings_list` 返回当前所有 drawing 的元信息（id/type/points/options）
- **ToolBox 生命周期管理**：`_delete()` 销毁 JS toolBox + 清空所有状态，`_build()` 注册 handler + 创建 JS toolBox
- **跨 pane 拖拽修复**：`_isMouseInMyPane()` 利用 `MouseEventParams.paneIndex` 检查鼠标所在 pane，拖拽中不检查边界
- **RayLine 数据范围外可拖拽**：坐标转换 null 时跳过该维度检查，不再直接 return false
- **show(wait=N) 消息循环修复**：改为后台超时线程 + 主线程运行 `show_async()`，JS 回调正常触发
- **Audit 补充**：Python 端新增 volume_oi/toolbox/drawing_series/interval/offset/period_locked，JS 端新增 paneCount/pane.N.seriesCount/pane.N.height/toolboxDrawings/toolboxHasOnChanged

### Fixed

- **`__init__` AttributeError**：移除 `__init__` 中多余的 `self.toolbox._build()` 调用（在 `self.toolbox` 赋值之前引用）
- **reset() handler 恢复**：`_save_drawings` → `_on_callback`（方法重命名后未同步）
- **reset_sub() toolbox 重建**：销毁后自动 `_build()` 重建

### Changed

- **DrawingSeries 精简**：移除 `_ensure_js_series` 和 dummy 数据，仅作 per-pane drawing 管理器（~70 行）
- **ToolBox 不再创建独立 DrawingSeries**：直接使用主 chart 的 pane（`chart.panes()[0]`）

---

## [v2.8.1] - 2026-06-27

### Breaking Changes

- **Drawing 重构**：`chart._drawings` 列表已移除，改为 `chart._drawing_series` 字典（`{pane_index: DrawingSeries}`）。`chart.drawings` 属性保留兼容性，遍历所有 pane 的 drawing 列表。

### Added

- **DrawingSeries 绘图管理重构**：每个 pane 拥有独立的 `DrawingSeries(Pane)` 管理 drawing 对象
  - 新文件 `drawing_series.py`：惰性创建不可见 JS LineSeries，5 个工厂方法
  - AbstractChart 用 `_drawing_series` 字典按 pane_index 管理
  - ToolBox 持有独立的 DrawingSeries，与 chart 完全隔离
  - Drawing 基类改为持有 `drawing_series`（不再直接持有 chart）
  - 工厂方法新增 `pane_index` 参数：`chart.horizontal_line(price, pane_index=1)`
- **`chart.show(wait=5)`**：显示窗口后等待指定秒数自动关闭，适用于截图/演示场景
  - 内部使用 `Process.join(timeout=wait)` 替代 `time.sleep`，窗口被用户关闭时会提前返回
  - PyWV 事件循环在 `queue.get` 超时后增加 `is_alive` 二次检查，窗口关闭后最多等待 2 秒即退出
- **AreaSeries（面积图）**：折线+渐变填充，支持 topColor/bottomColor/relativeGradient/invertFilledArea
  - 工厂方法：`chart.create_area(name, color, style, width, top_color, bottom_color, ...)`
  - Python 类：`AreaSeries(SeriesCommon)`，数据输入与 LineSeries 完全一致（time + value）
  - 全部继承 SeriesCommon 的 set/update_bars/update_ticks/delete/marker
  - 示例：`examples/37_more_series_types/`

- **OHLCBarSeries（美国线）**：横向 OHLC 柱状图，open 左 close 右
  - 工厂方法：`chart.create_ohlc_bar(name, up_color, down_color, open_visible, thin_bars, ...)`
  - Python 类：`OHLCBarSeries(CandleSeries)`，继承 CandleSeries 共享全部 OHLC 数据处理逻辑
  - 覆盖 `__init__`（调 createOHLCBarSeries）+ `_build()` + `bar_style()`（美国线专属样式）
  - 覆盖 `candle_style()` 抛出 AttributeError 提示使用 `bar_style()`
  - 数据输入与 CandleSeries 完全一致（time + open + high + low + close）
  - 示例：`examples/37_more_series_types/`

- **BaselineSeries（基准线）**：以基准值为界上下分色
  - 工厂方法：`chart.create_baseline(name, base_value, top_fill_color1/2, bottom_fill_color1/2, ...)`
  - Python 类：`BaselineSeries(SeriesCommon)`，数据输入为 time + value
  - 全部继承 SeriesCommon 的 set/update_bars/update_ticks/delete/marker
  - 示例：`examples/37_more_series_types/`

- **Legend OHLC 支持**：legend.ts 的 `legendHandler` 新增对 Bar/Candlestick 类型 series 的 OHLC 格式显示
  - lines 遍历中根据 `seriesType()` 判断：Bar/Candlestick → `O ... | H ... | L ... | C ...`
  - 修复 OHLCBarSeries 在 legend 中只显示眼睛图标无内容的问题

### Changed

- **handler.ts import**：新增 AreaSeries、BarSeries、BaselineSeries 及其 StyleOptions 类型导入
- **handler.ts SKIP_KEYS**：新增 `createAreaSeries`、`createOHLCBarSeries`、`createBaselineSeries`
- **handler.ts GLOBALS_RE**：新增 `AreaSeries_\d`、`OHLCBarSeries_\d`、`BaselineSeries_\d` 模式
- **series.py**：新增 AreaSeries、OHLCBarSeries、BaselineSeries 三个类
- **abstract.py**：新增 `create_area_series()`、`create_ohlc_bar_series()`、`create_baseline_series()` 工厂方法
- **__init__.py**：导出 AreaSeries、OHLCBarSeries、BaselineSeries

### 设计决策

- **OHLCBarSeries 继承 CandleSeries**：两者 95% 代码相同（OHLC 数据处理），仅 JS 创建方法和样式配置不同。通过覆盖 `__init__`/`_build()`/`bar_style()` + 覆盖 `candle_style()` 抛错，避免 ~80 行重复代码
- **AreaSeries/BaselineSeries 继承 SeriesCommon**：与 LineSeries 相同的数据输入（time + value），只需覆盖 `__init__` 调不同的 JS 创建方法
- **legend OHLC 支持**：在 legendHandler 的 lines 遍历中，通过 `seriesType()` 检测 Bar/Candlestick 类型，显示 OHLC 四个数字而非 value

### Fixed

- **PyWV 事件循环退出延迟**：窗口关闭后 `_event_loop` 最多等待 4 秒才退出（`queue.get` 2s + `while` 2s）。修复：在 `queue.get` 超时后增加 `is_alive` 二次检查，窗口关闭后最多 2 秒即退出
- **`chart.show(wait=N)` 提前返回**：旧实现用 `time.sleep(wait)` 傻等，用户关窗口后仍需等满 N 秒。修复：改用 `Process.join(timeout=wait)`，进程结束时立即返回

---

## [v2.8.0] - 2026-06-26

### Breaking Changes

- **函数重命名**：`update_from_tick()` → `update_tick()`，`update_from_ticks()` → `update_ticks()`（旧名已在 v2.8.3 移除）
- **类重命名**：`Line` → `LineSeries`，`Histogram` → `HistogramSeries`（旧名已在 v2.8.3 移除）
- **normal_df 精简**：不再自动将列名转为小写，不再自动将 `date` 列重命名为 `time`
- **AbstractChart 不联动 _lines**：`set()`/`update_bars()`/`update_ticks()` 不再自动转发数据给 Line/Histogram
- **统一输入列**：所有系列的 `set()`/`update_bars()`/`update_ticks()` 统一接受 `time` + `value` 列
- **VolumeSeries 要求 open/close**：`_prepare_vol_df` 要求 `open`/`close` 列用于涨跌着色，缺失时抛 `ValueError`
- **移除 cumulative_volume**：`AbstractChart.update_ticks()` 不再接受 `cumulative_volume` 参数

### Added

- **`chart.data` 始终 7 列**：返回 `time, open, high, low, close, volume, open_interest`，缺失系列对应列填 NaN
- **`chart.vol_data`**：只返回 `time, value`（不暴露 open/close/color）
- **`chart.oi_data`**：返回 `time, value`
- **VolumeSeries 维护 open/close**：`self.data` 存储 `time, value, open, close, color`，tick 累积时保留 open、更新 close、重算 color
- **VolumeSeries.update_ticks 自动聚合 open/close**：从 tick 的 `price` 列聚合 `open`(first)/`close`(last) 供着色

### Changed

- **SeriesCommon set→update_bars 委托**：`set()` 简化为清空 + 委托 `update_bars()` + markers，约 8 行
- **SeriesCommon update_bars 智能分支**：空数据用 `setData` 批量写入（高效），有数据用 per-row `update`
- **OpenInterestSeries 大幅精简**：删除 ~90 行重复代码，`set`/`update_bars`/`update_ticks`/`delete` 全部继承自 SeriesCommon
- **OI 只保留 `__init__` + `_build` + `config`**：三个特有方法，其余全部继承
- **VolumeSeries _prepare_vol_df**：输出从 `time, value, color` 扩展为 `time, value, open, close, color`
- **AbstractChart.update_ticks 转发**：candle 用 `price→value`，volume 用 `volume→value` + `open/close` from `price`，OI 用 `open_interest→value`
- **AbstractChart.reset() 清理**：移除重复的 `series.data = pd.DataFrame()`，`markers.clear()` 移入循环
- **`lines()` 返回类型**：`list[LineSeries]` → `list[SeriesCommon]`
- **`vertical_span`**：不再绕道 `self.candle._single_datetime_format`，直接用 `self._single_datetime_format`

---

## [v2.7.3] - 2026-06-23

### Added

- **Histogram 任意颜色支持**：Histogram 内置 `_option_columns=['color']`，set/update_bars 时若输入 DataFrame 中存在 `color` 列则自动携带到 JS 端，支持每根柱子独立着色
  - 新增 `_check_value_name_conflict_and_rename()` 方法：统一处理 value 列和系列名的冲突检测与重命名
  - 方法返回新 df（非 inplace），防止多 line 共享同一个 df 时互相污染
  - `SeriesCommon.set()` 和 `update_bars()` 均支持 `_option_columns` 参数
  - 新增示例 `examples/36_histogram_colors/`：买卖量差正负渐变色演示

### Changed

- **AbstractChart 常驻系列重构**：`candle`/`volume`/`oi` 始终存在（reset 后自动重建），消除所有 `if self.volume:` / `if self.oi:` / `if self.candle else` 守卫代码
  - `reset()` 末尾自动重建三者（CandleSeries / VolumeSeries / OpenInterestSeries）并重新赋值 Handler 引用
  - `set()` 移除 10 行"检测并重建被 reset() 删除的 series"代码块
  - `update_bars()` / `update_from_ticks()` / `clear_data()` 各移除 None 守卫，只保留 `'volume' in df.columns` 列检查
  - `candle_data` / `data` / `markers` 三个属性去掉 `if self.candle else` 三元判断
  - `hide_data()` / `show_data()` 去掉 volume/oi 的 None 守卫
  - 类 docstring 从"可选挂载"改为"始终存在"

- **SeriesCommon.clear_data() 统一清空逻辑**：基类新增 `clear_data()` 方法（清空 JS 数据 + 重置 `self.data` + `clear_markers()`）
  - VolumeSeries / OpenInterestSeries 继承基类默认实现，无需额外定义
  - CandleSeries `clear_data()` 改为 `super().clear_data()` + 清理 `candle_data` 和 `_last_bar`
  - AbstractChart `clear_data()` 简化为统一调用三个系列的 `clear_data()`

- **abstract.py 拆分**：SeriesCommon + VolumeSeries + OpenInterestSeries + CandleSeries 移入新文件 `series.py`（1198 行），abstract.py 从 2795 行缩减到 1553 行（-45%），零继承链变化

- **SeriesCommon.delete() 基类统一**：基类新增 `delete()` 方法（clear_markers + 重置 _last_bar/data + JS 清理），5 个子类（Line/Histogram/VolumeSeries/OI/CandleSeries）全部简化为 `super().delete()`
  - 修复 Line/Histogram 的 JS bug：`{self.id}legendItem` 变量名含 `.` 导致 JS 语法错误，统一为 `var _legendItem`
  - delete 时调用 `clear_markers()` 清除 Python 和 JS 端标记，防止 removeSeries 失败后残留

- **三个系列类 _build() 提取 + 参数存储**：CandleSeries / VolumeSeries / OpenInterestSeries 的 `__init__` 将 JS 创建逻辑提取到 `_build()` 方法，构造参数存储为实例属性
  - `config()` / `candle_style()` 同步更新 Python 属性 + JS，确保 `_build()` 重建时使用最新值

- **CandleSeries candle_data → data 合并**：移除 `self.candle_data`，统一使用基类的 `self.data`，消除每次更新的 `.copy()` 开销
  - `AbstractChart.candle_data` property 保留兼容性，返回 `self.candle.data`

- **CandleSeries 删除多余 volume/OI 检测**：`update_from_ticks()` 中移除 ~20 行 volume/OI 聚合逻辑（CandleSeries 只处理 OHLC，聚合后会被 `update_bars()` 丢弃）

- **AbstractChart toolbox 始终存在**：`self.toolbox = ToolBox(self) if toolbox else None`，不再使用 `hasattr` 检查
  - ToolBox 新增 `clear_drawings()` / `reposition_drawings()` 方法，封装 JS 细节

- **run_tests.py 补全**：新增 4 个缺失测试（test_candle_series / test_data_aggregation / test_position / test_reset_sub），现在 7/7 test suites 全部覆盖

---

## [v2.7.2] - 2026-06-21

### Fixed

- **`update()`/`update_batch()`/`update_from_ticks()` 不转发 volume/OI 给独立 series**：v2.7.0 组合架构重构后，`AbstractChart.update_batch(df)` 只委托给 `self.candle.update_batch(df)`，后者只处理 OHLC 列，volume/OI 数据被静默丢弃。`set()` 正确转发了 volume/OI，但更新方法遗漏了
  - **`update()`**：新增 volume/OI 转发给 `self.volume`/`self.oi`
  - **`update_batch()`**：新增 volume/OI 转发给 `self.volume`/`self.oi`
  - **`update_from_ticks()`**：重写——先在 AbstractChart 层聚合 volume/OI 转发给独立 series，再将不含 volume/OI 的 DataFrame 交给 CandleSeries 处理 OHLC，避免 volume 被重复聚合
  - **`update_from_tick()`**：委托给 `update_from_ticks()` 统一处理，避免重复转发
  - **`update_bar`/`update_bars` 别名**：从 `property(lambda: self.candle.xxx)` 改为普通方法，委托给 `update()`/`update_batch()`，确保 volume/OI 转发不被绕过

- **`CandleSeries.set()` 调用 `time_to_bar_time()` 缺少参数**：直接调用模块级函数缺少 `offset`/`interval`，改为 `self._chart._time_to_bar_time(df)`

- **TypeScript 编译警告消除（11 → 0）**：v2.7.0 重构将 `Handler.series` 改为 `ISeriesApi | null`（惰性创建），但使用处缺少 null guard，导致 11 个 TS2345/TS2531 警告
  - **`createToolBox()`**：添加 `if (!this.series) return` 提前返回
  - **`syncChartsAll` ×2**：crosshair 回调中对 `source.series` 和 `target.series` 添加 null guard
  - **`syncCharts`**：`crosshairHandler()` 顶部加 `if (!chart.series) return`；`getPoint()` 签名改为 `series: ISeriesApi | null`，内部 guard
  - **`_syncCharts`**：crosshair 回调中对 `chart.series` 和 `target.series` 添加 null guard
  - **`legend.ts legendHandler()`**：顶部加 `if (!this.handler.series) return`
  - 所有 guard 均为防御性编程——运行时 series 一定已设置（Python 端先创建，用户交互在后）

---

## [v2.7.1] - 2026-06-21

### 清理

#### 移除 Handler 级别 `seriesMarkers`
- **问题**：v2.7.0 重构后，Handler 的 `seriesMarkers` 属性从未被功能性使用——Python 勤奋赋值，JS 端从不读取（audit 中的 `markersCount` 因 `.length` 不存在永远返回 0）
- **清理内容**：
  - **JS**：移除 `seriesMarkers` 属性声明、构造函数初始化、SKIP_KEYS 条目、`createSeriesMarkers` import 和调用
  - **JS**：`createCandleSeries()` 不再返回 `seriesMarkers`，改为 `_update_markers()` 按需在 series 级别创建
  - **JS**：移除 audit 中坏掉的 `markersCount` 读取
  - **Python**：移除 `AbstractChart.__init__` 和 `set()` 中 `{self.id}.seriesMarkers = {self.candle.id}.seriesMarkers` 赋值
  - **Python**：移除 `reset()` 中 `seriesMarkers` 清理（随 series 删除自动清理）
- **设计变更**：`seriesMarkers` 从"Handler 级别持有 + 全局复制"改为"按需在 series 级别创建"——`_update_markers()` 首次调用时自动创建，`delete series` 时自动清理

#### `_marker_auto_scale` 修复
- **问题**：Handler 构造函数接收 `marker_auto_scale` 参数但从未存储或使用，`_update_markers()` 中 `autoScale` 硬编码为 `true`
- **修复**：
  - **Python**：`AbstractChart.__init__` 存储 `self._marker_auto_scale = marker_auto_scale`
  - **Python**：`_update_markers()` 使用 `self._chart._marker_auto_scale` 替代硬编码 `true`
  - **JS**：移除 Handler 构造函数中的 `marker_auto_scale` 参数（纯 Python 侧逻辑）

#### 移除 Handler 构造函数中忽略的参数
- **`paneIndex`**：pane_index 在系列创建时（`createLineSeries` 等）传入，Handler 层面不需要，已移除
- **`_marker_auto_scale`**：纯 Python 侧逻辑（`AbstractChart._marker_auto_scale` 存储 + `_update_markers()` 读取），已移除
- Handler 构造函数从 8 个参数精简为 7 个

---

## [v2.7.0] - 2026-06-21

### 核心架构变更

#### 固定 ID + 按需重建
- **主 series 使用固定 ID**：`window.Chart_1_candle` / `window.Chart_1_volume` / `window.Chart_1_oi`
  - ID 不由 IDGen 自动生成，但 audit 的 `GLOBALS_RE`（`Chart_\d` 前缀）能正确捕获
  - 删除后按同名重建，JS 全局变量名一致
- **Handler 构造函数惰性创建**：`this.series`/`this.volumeSeries`/`this.openInterestSeries` 全部设为 `null`
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
