# MEMORY.md - 项目长期记忆

本文件记录 lightweight-charts-onesixth 项目的核心经验、决策和教训。

---

## ⚠️ pywebview 关键陷阱（最高优先级）

### evaluate_js 无法序列化 lightweight-charts API 对象
- **问题**: JS 函数返回包含 ISeriesApi/IChartApi 等对象的结构时，pywebview 的 `evaluate_js` 无法序列化，导致**整个消息链路永久卡死**
- **表现**: `run_script_and_get` 永远超时，连简单的 `Object.keys(window).length` 也无法执行
- **修复**: Python 端 `run_script` 调用末尾加 `;0`，阻止返回值传播
- **示例**:
  ```python
  # ❌ 错误 - 返回 {name, series} 对象会导致卡死
  self.run_script(f'{self.id} = {chart.id}.createCandleSeries(...)')
  
  # ✅ 正确 - 加 ;0 阻止返回值
  self.run_script(f'{self.id} = {chart.id}.createCandleSeries(...);0')
  ```
- **影响范围**: `createCandleSeries`、`createLineSeries`、`createHistogramSeries` 等所有返回 `{name, series}` 结构的 JS 函数
- **已有隐患**: `createLineSeries` 和 `createHistogramSeries` 也返回 `{name, series}`，目前 Python 端调用时也没加 `;0`

### 消息循环异常处理不能终止循环
- **问题**: `chart.py` 消息循环中 `KeyError` 和 `Exception` 的 `return` 会**终止整个消息处理**
- **表现**: 某个 `evaluate_js` 抛异常后，后续所有 `run_script_and_get` 全部超时
- **修复**: 移除 `return`，只 `put(None)` 到 return_queue，让循环继续
- **教训**: ⚠️ 消息循环中的异常处理**绝对不能终止循环**

### return_queue 值类型安全
- `evaluate_js` 返回的是简单类型（string/number/boolean/None），pywebview 已正确处理
- `multiprocessing.Queue` 可以序列化这些简单类型
- **不需要额外的 `str()` 转换**

---

## 🔧 架构决策

### JS 命名空间
- bundle IIFE 中 `lightweightCharts` 是参数名（= 全局 `LightweightCharts`），不是导入的具名变量
- TypeScript 编译时 `lightweightCharts` 报 `Cannot find name` 警告，但运行时在 IIFE 闭包内可以正常访问

### async IIFE 脚本链
- `on_js_load()` 将所有排队脚本拼接成一个 async IIFE 执行
- 链中任何脚本报错会中断整个 async 函数，后续脚本不执行
- 关键操作（如 `setMarkers`）必须用 try/catch 保护

### seriesMarkers 创建位置
- 必须在 JS 端创建（`createSeriesMarkers` 在 IIFE 闭包内），Python 端不能直接调用
- 通过返回对象传递给 Python：`{name, series, seriesMarkers}`

---

## 📊 CandleSeries 设计

### 为什么继承 SeriesCommon 而不是 Candlestick？
- Candlestick 自带 volume/open interest，Candlestick.__init__ 创建主K线
- CandleSeries 只需要 OHLC，更轻量
- SeriesCommon 提供 `_normal_df`/`_set_interval`/`_time_to_bar_time`/`_merge_value_by_time` 等工具方法

### JS 端 createCandleSeries
- 调用 `chart.addSeries(CandlestickSeries, options, paneIndex)`
- 注册到 `_seriesList` 和 `legend`
- 创建 `seriesMarkers`（通过 `createSeriesMarkers`）
- 返回 `{name, series, seriesMarkers}`

---

## 📝 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `src/general/handler.ts` | `createCandleSeries` 方法 + GLOBALS_RE + SKIP_KEYS（audit 函数未改动） |
| `lightweight_charts/js/bundle.js` | 重新编译 |
| `lightweight_charts/abstract.py` | `CandleSeries` 类 + `create_candle_series()` + `_update_markers` try/catch + `;0` 后缀 |
| `lightweight_charts/__init__.py` | 导出 `CandleSeries` |
| `lightweight_charts/chart.py` | 消息循环 KeyError/Exception 改为 break + put(None) |
| `test/test_candle_series.py` | 6 个测试用例 |
| `examples/34_candle_series/` | 3 个示例（静态/实时/批量） |
