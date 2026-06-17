# AGENT.md - Agent 操作指南

本文件指导 AI Agent 如何在 lightweight-charts-onesixth 项目中安全高效地工作。

---

## 🔴 最高优先级规则

### ⚠️ run_script 必须加 `;0`
所有通过 `run_script` 执行的 JS 代码，如果返回值可能包含 lightweight-charts API 对象（ISeriesApi/IChartApi 等），**必须在末尾加 `;0`**。否则 pywebview 的 `evaluate_js` 会永久卡死。

```python
# ❌ 危险 - 返回 {name, series} 会卡死
self.run_script(f'{self.id} = {chart.id}.createCandleSeries(...)')
# ✅ 安全 - 加 ;0 阻止返回值
self.run_script(f'{self.id} = {chart.id}.createCandleSeries(...);0')
```

### ⚠️ 消息循环不能终止
修改 `chart.py` 消息循环时，异常处理中**绝对不能有 `return`**。只能跳过当前消息，让循环继续。

### ⚠️ return_queue 值必须是简单类型
`evaluate_js` 返回值必须 `str()` 转换后再 `put` 到 `return_queue`。

---

## 🛠️ 开发流程

### 新增 JS 功能
1. 在 `src/general/handler.ts` 中添加方法
2. 更新 `GLOBALS_RE`（audit 正则）和 `SKIP_KEYS`（audit 跳过列表）
3. 执行 `npx rollup -c rollup.config.js` 编译
4. 复制 `dist/bundle.js` → `lightweight_charts/js/bundle.js`

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
python test/test_candle_series.py
```

---

## 📁 项目结构

```
lightweight-charts-onesixth/
├── lightweight_charts/         ← Python 后端
│   ├── abstract.py             # 核心类: Window, AbstractChart, Candlestick, CandleSeries, Line, Histogram
│   ├── chart.py                # Chart (pywebview) + CrossProcessChart
│   ├── widgets.py              # JupyterChart, HTMLChart, HtmlTabChart, QtChart
│   ├── js/bundle.js            # 编译后前端
│   └── __init__.py             # 导出
├── src/                        ← TypeScript 前端
│   ├── general/handler.ts      # Handler 类 (核心)
│   ├── general/legend.ts       # 图例
│   └── general/toolbox.ts      # 绘图工具箱
├── test/                       ← 测试
├── examples/                   ← 示例 (34 个)
├── MEMORY.md                   # 项目长期记忆
└── AGENT.md                    # 本文件
```

---

## 🔍 调试技巧

### run_script_and_get 超时
1. 先检查是否加了 `;0`（最常见原因）
2. 检查 JS 函数是否抛异常（查看消息循环日志）
3. 检查 `_return_q` 是否初始化
4. 尝试用 `run_script` 写入 window 变量，再用 `run_script_and_get` 读取

### audit 不返回
1. 检查 `chart.py` 消息循环是否有 `return` 终止了循环
2. 检查 `evaluate_js` 返回值类型
3. 用 `run_script_and_get('Lib.Handler.audit()')` 单独测试

### 标记不显示
1. 检查 `_update_markers` 是否有 try/catch 保护
2. 检查 `seriesMarkers` 是否在 JS 端正确创建
3. 检查 async IIFE 中是否有脚本报错中断了执行链

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

---

## 🔴 已排除的修改（确认不必要）

- `handler.ts` audit 函数的 try-catch 包装 — 根因是 `;0` 后缀，不是 audit 函数
- `Window.__init__` 中 `import multiprocessing` + `self._return_q = multiprocessing.Queue()` — 多余
- `chart.py` 中 `str(result) if result is not None else None` — evaluate_js 返回值 pywebview 已正确处理
