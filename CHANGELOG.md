# Changelog

所有重要的项目更改都将记录在此文件中。

---

## [Unreleased]

### Added

- **图表同步功能**: `create_subchart()` 新增 `sync_id` 参数，支持多图表同步时间轴和十字光标
- **图表同步示例**: 新增示例 `31_chart_sync`，演示 `sync_id` 和 `sync_crosshairs_only` 参数的使用
- **表格组件改进**: `create_table()` 支持 `height=None` 和 `width=None` 实现自动适应内容大小
- **网格布局系统**: `position` 参数支持三种格式：整数（如 `111`）、元组（如 `(2,2,1)`）、字符串（已弃用）
- **运行时位置控制**: 新增 `get_position()` 和 `set_position()` 方法，支持动态调整图表位置
- **相对大小控制**: `width`/`height` 参数相对于网格单元，支持内缩（<1.0）和侵占（>1.0）

### Changed

- **表格 position 参数变更**: `create_table()` 的 `position` 参数字符串输入已废弃，输入任何字符串等效于输入 `(0, 0)`，会发出 `DeprecationWarning`
- **表格位置处理逻辑**: 统一 position 参数处理，移除重复的类型检查
- **Table 类默认位置**: 默认值从 `'left'` 改为 `(0, 0)`

### Fixed

- **表格布局问题**: 修复了表格内容不显示、表头与表内容重叠的问题
- **表格拖动区域问题**: 修复了表格可拖动区域过大超出表格大小的问题
- **回调 KeyError**: 修复了表格点击时 `KeyError: 'null'` 的问题
- **表格样式修复**: 添加 `overflowWrapper.style.flex = '1'` 和 `overflowWrapper.style.minHeight = '0'`
- **代码质量**: 清理了多处 TODO 注释，添加了详细说明和类型定义

### Deprecated

- **表格 position 字符串**: `create_table()` 的 `position` 参数不再支持字符串（`'left'`, `'right'`, `'top'`, `'bottom'`），建议使用元组格式 `position=(x, y)`

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
