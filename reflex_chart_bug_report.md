# ReflexChart 幽灵图表 Bug 调查报告

> **日期**：2026-07-02
> **项目**：lightweight-charts-onesixth
> **版本**：v3.0.1
> **文件**：`lightweight_charts/reflex_chart.py`
> **示例**：`examples/27_reflex_chart/`

---

## 一、问题描述

### 症状

在 Reflex 示例（`examples/27_reflex_chart`）中，首次启动 Reflex 服务器后：

1. **页面加载正常**：图表正常显示，交互正常
2. **首次点击 +1Bar**：图表背后出现另一个静止的图表（幽灵图表）
3. **幽灵图表特征**：
   - 精确复制了用户对正面图表的交互状态（如拉起、缩放）
   - 不响应后续更新（死图表）
   - 位置与正面图表完全重叠，只有拉开后才能发现
4. **刷新页面后**：幽灵图表消失，后续点击 +1Bar 不会再出现
5. **重启 Reflex 服务器**：幽灵图表再次出现

### 触发条件

- ✅ 首次启动 Reflex 服务器 + 首次点击 +1Bar
- ❌ 页面刷新后（无论点击多少次）
- ❌ 关掉页面重新打开
- ❌ 浏览器硬刷新

**结论**：问题与 **Reflex 服务器首次启动**相关，而非浏览器缓存或页面生命周期。

---

## 二、环境信息

- **Reflex 版本**：未知（通过 `rx.__version__` 获取失败）
- **Python 版本**：3.14t（miniconda env: normal）
- **lightweight-charts 版本**：v3.0.1
- **浏览器**：未指定
- **操作系统**：Windows 11 (AMD64)

---

## 三、代码架构

### ReflexChart 类层次

```
StaticLWC (widgets.py) — 静态 HTML/JS 图表基类
  └─ ReflexChart (reflex_chart.py) — Reflex 框架适配
```

### 核心方法

| 方法 | 说明 |
|------|------|
| `__init__()` | 初始化 `_pending`、`_html_frozen`、`_auto_flush` |
| `run_script()` | 缓存 JS 脚本到 `_html` 和 `_pending`；Handler 构造脚本加 guard |
| `get_html()` | 生成完整自包含 HTML 字符串 |
| `_build_html()` | 构建 iframe 内的 HTML（库 JS + init 脚本 + message 监听） |
| `to_reflex()` | 返回 Reflex 可渲染的 iframe 组件 |
| `flush()` | 将 `_pending` 脚本经 postMessage 发送到 iframe |

### 示例代码关键流程

```python
chart = ReflexChart(width=1000, height=600, auto_flush=True)
chart.set(ohlcv_df)           # 设置数据 → run_script → _pending
chart.layout(...)              # 样式 → run_script → _pending
chart.candle_style(...)        # K线样式 → _pending
chart.volume_config(...)       # 成交量样式 → _pending
chart.watermark(...)           # 水印 → _pending
chart.legend(visible=True)     # 图例 → _pending
sma = chart.create_line(...)   # 创建均线 → _pending
sma.set(...)                   # 均线数据 → _pending
# 此时 _pending 有 25+ 条初始化脚本

def index():
    return rx.vstack(
        ...,
        chart.to_reflex(id='lwc-frame'),  # ← 关键：渲染图表
        ...,
    )

class ChartState(rx.State):
    def tick(self):
        chart.update_bar(bar)     # → _pending (2条更新脚本)
        self.bar_count += 1       # → 状态变更
        return chart.flush()      # → rx.call_script(postMessage)
```

---

## 四、调查过程

### 阶段 1：确认 Python 侧逻辑

**验证内容**：
- `_pending` 在 `to_reflex()` 后被正确清空 ✅
- `update_bar()` 后 `_pending` 只有数据更新脚本 ✅
- `get_html()` 输出多次调用完全一致 ✅
- `flush()` 正常返回 `rx.call_script` ✅

**结论**：Python 侧数据生成逻辑没有问题。

### 阶段 2：尝试缓存组件（失败）

**方案**：`to_reflex()` 首次构建 `rx.el.iframe` 后缓存，后续返回同一对象

**代码**：
```python
if not self._html_frozen:
    self._cached_reflex_component = rx.el.iframe(...)
return self._cached_reflex_component
```

**结果**：❌ 幽灵图表仍在

**分析**：Reflex 序列化组件树时使用 JSON，Python 对象引用不保留。前端 React 无法感知"同一对象"。

### 阶段 3：尝试 div 容器 + rx.script 注入（部分失败）

**方案**：React 只管理 div 容器，iframe 由 JS 动态创建（React 不碰 iframe）

**代码**：
```python
return rx.fragment(
    rx.el.div(id=container_id),
    rx.script(inject_script),  # JS 创建 iframe
)
```

**inject_script 含超长 base64 字符串** → ❌ **React Helmet 语法错误**

```
SyntaxError: Failed to execute 'appendChild' on 'Node': missing ) after argument list
    at react-helmet.js:1023
```

**根因**：`rx.script()` 在 Reflex 中走 React Helmet 管道管理 `<script>` 标签。超长脚本内容（含 1.5MB base64）导致解析错误。

### 阶段 4：加 React key prop（失败）

**方案**：`rx.el.iframe(key='lwc-chart-key')` 帮助 React reconciliation 正确匹配

**代码**：
```python
return rx.el.iframe(id=id, key='lwc-chart-key', src=..., style=...)
```

**结果**：❌ 幽灵图表仍在

**分析**：可能 Reflex 的序列化/前端不传递 `key` prop，或全量重建时 key 不足以阻止旧 iframe 残留。

### 阶段 5：rx.script 简短自愈脚本（语法错误）

**方案**：短脚本（不含 base64）定期清理重复 iframe

**代码**：
```python
rx.script('setInterval(function(){...}, 500);')
```

**结果**：❌ 同样的 React Helmet 语法错误

```
SyntaxError: missing ) after argument list
    at react-helmet.js:1023
```

**分析**：即使是短脚本，`rx.script()` 走 React Helmet 管道时仍可能因特殊字符导致解析错误。

### 阶段 6：flush() 内嵌清理（语法错误）

**方案**：将清理逻辑嵌入 `flush()` 返回的 `rx.call_script`，完全避开 `rx.script`

**代码**：
```python
full_script = (
    f'var a=document.querySelectorAll("iframe[id={_json.dumps(_id_str)}]");'
    ...
)
return rx.call_script(full_script)
```

**首次结果**：❌ 语法错误

```
SyntaxError: missing ) after argument list
    at applyEvent (state.js:364)
```

**根因分析**：
```javascript
// _json.dumps('lwc-frame') → '"lwc-frame"'
// 生成的脚本：
querySelectorAll("iframe[id="lwc-frame"]")
//                   ↑外层"和内部"冲突！
// JavaScript 解析为：字符串 "iframe[id=" + 变量 lwc-frame + 字符串 "]"
```

**修复**：CSS 选择器中用单引号，外层用双引号
```python
f'querySelectorAll("iframe[id=\'{_id_str}\']")'
// 生成：querySelectorAll("iframe[id='lwc-frame']") ✅
```

**再次尝试**：✅ 没有语法错误，但幽灵图表仍在

### 阶段 7：占位符策略 + flush() 动态创建 iframe

**方案**：`to_reflex()` 首次渲染返回空 div（占位符），没有 iframe；`flush()` 首次调用时动态创建 iframe 替换占位符

**关键假设**：Reflex 首次状态变更会**全量重建页面**，旧 iframe 因独立浏览上下文未被移除。首次不渲染 iframe 则没有旧 iframe 可以残留。

**代码**：
```python
def to_reflex(self, ...):
    if not self._html_frozen:
        # 首次：构建 HTML 缓存，返回占位符
        ...
        return rx.el.div(style=style, data_lwc_placeholder='')
    # 后续：返回真实 iframe
    return rx.el.iframe(id=id, src=..., style=style)
```

**结果**：
- ✅ 没有幽灵图表（占位符策略有效）
- ❌ **也没有正常图表**（首次点击 +1Bar 后图表未出现）

**分析**：`flush()` 返回的 `rx.call_script` 可能在 Reflex 重渲染**之前**执行，此时 iframe 尚未创建（占位符还在），而 `flush()` 的创建逻辑因未知原因未生效。

---

## 五、关键洞察

### 5.1 幽灵图表只在服务器首次启动后出现

这是最重要的线索。暗示问题根源在 **Reflex 的初始化/编译过程**，而非常规渲染周期。

推测：Reflex 首次启动时，首次状态变更触发**全量页面重建**（full delta），创建新 DOM 树。旧 iframe 因独立浏览上下文未被正确移除。

### 5.2 占位符策略有效但执行时机不对

占位符策略**确实阻止了幽灵图表**，说明"首次不渲染 iframe"的方向正确。

但 `flush()` 的创建逻辑未生效，可能因为：
- `rx.call_script` 在重渲染之前执行（此时 iframe 还不存在）
- 创建脚本有语法错误或逻辑错误
- Reflex 处理 EventSpec 与重渲染的顺序不确定

### 5.3 rx.script 与 React Helmet 不兼容

Reflex 的 `rx.script()` 组件走 React Helmet 管道管理 `<script>` 标签。即使简短脚本也可能触发 React Helmet 错误。

**建议**：`rx.script()` 在 Reflex 中不可靠，应完全避免。

### 5.4 `_json.dumps` 双引号陷阱

`json.dumps('lwc-frame')` 产生 `"lwc-frame"`（含双引号）。嵌入 `querySelectorAll("iframe[id=...]")` 时导致双引号冲突。

**正确做法**：
```python
# ❌ 错误：双引号冲突
f'querySelectorAll("iframe[id={json.dumps(id)}]")'
# 输出: querySelectorAll("iframe[id="lwc-frame"]")  ← 语法错误

# ✅ 正确：CSS 选择器内用单引号
f'querySelectorAll("iframe[id=\'{id}\']")'
# 输出: querySelectorAll("iframe[id='lwc-frame']")  ← 正确
```

---

## 六、未解决的问题

### 6.1 flush() 创建 iframe 未生效

占位符策略下，`flush()` 的创建逻辑为何未执行？

可能的原因：
1. `rx.call_script` 执行时机早于 React 渲染占位符？→ `querySelector` 找不到占位 div
2. 创建脚本的 `!document.getElementById(...)&&(function(){...})()` 语法有问题
3. Reflex 的 `applyEvent` 处理 `call_script` 时有特殊限制

### 6.2 如果不使用占位符，能否修复？

如果可以找到一种方式让 React 在重渲染时不遗留旧 iframe，就可以直接渲染 iframe。

尝试过的方案（均失败）：
- `key` prop → 不确定 Reflex 是否传递
- 组件缓存 → Reflex 序列化不保留引用
- `rx.script` 清理 → React Helmet 错误
- `flush()` 内嵌清理 → 双引号修复后无语法错误但幽灵仍在

### 6.3 是否可以修改 Reflex 示例代码？

如果可以修改 `rx_chart.py`，可以尝试：

```python
# 方案 A：使用 rx.cond 条件渲染
rx.cond(ChartState.bar_count > 0, chart.to_reflex(...))

# 方案 B：在 mount() 中动态创建 iframe
def mount(self):
    return rx.sequence(
        rx.call_script("...创建 iframe..."),
        rx.call_script("...设置消息监听..."),
    )
```

---

## 七、尝试过的所有方案汇总

| # | 方案 | 修改位置 | 结果 | 失败原因 |
|---|------|---------|------|---------|
| 1 | `_pending` 守卫：重渲染时不清空 | `to_reflex()` | ❌ | 非根本原因 |
| 2 | 组件缓存：首次构建后缓存返回 | `to_reflex()` | ❌ | Reflex 序列化不保留引用 |
| 3 | div + `rx.script` 注入（含 base64） | `to_reflex()` | ❌ 报错 | React Helmet 解析超长脚本失败 |
| 4 | `rx.el.iframe` 加 `key` prop | `to_reflex()` | ❌ | `key` 不被 Reflex 传递 |
| 5 | `rx.script` 简短自愈脚本 | `to_reflex()` | ❌ 报错 | React Helmet 仍报错 |
| 6 | `flush()` 内嵌清理 + IIFE | `flush()` | ❌ 报错 | 双引号冲突语法错误 |
| 7 | `flush()` 内嵌清理 + 单引号 | `flush()` | ❌ 幽灵仍在 | 清理未覆盖到正确时机 |
| 8 | 占位符 div + `flush()` 创建 iframe | `to_reflex()` + `flush()` | ❌ 无图表 | 创建逻辑未生效 |

---

## 八、推荐后续方向

### 方向 A：修复占位符方案（最直接）

解决 `flush()` 创建 iframe 未生效的问题：

1. **验证创建脚本语法**：用 Node.js 验证生成脚本是否正确
2. **验证占位符存在**：在创建前加 `console.log` 确认占位符 DOM 状态
3. **调整执行时机**：将创建逻辑移到 Reflex 的 `mount()` 或别的生命周期

### 方向 B：从 Reflex 角度解决

研究 Reflex 首次状态变更的全量重建机制：
1. 是否有配置项控制首次状态变更发送 delta 而非全量？
2. 是否可以提前触发一次"空状态变更"完成初始化？
3. 是否可以利用 Reflex 的 `on_load` 钩子预先创建 iframe？

### 方向 C：修改示例代码

既然库层面的修改都受限，可以考虑修改示例代码：

```python
# rx_chart.py
class ChartState(rx.State):
    chart_ready: bool = False
    
    def init_chart(self):
        """首次加载时创建 iframe"""
        self.chart_ready = True
        # 此时 to_reflex() 的第二次调用会返回真实 iframe
    
    def tick(self):
        ...
```

并在 `index()` 中使用 `rx.cond(chart_ready, chart.to_reflex())`。

### 方向 D：放弃 postMessage 方案

完全改变通信方式：
1. iframe 的 `src` 初始设为 `about:blank`
2. `flush()` 先 `document.write()` 图表 HTML 到 iframe
3. 后续更新通过 `postMessage` 发送

---

## 附录：关键代码片段

### _json.dumps 双引号问题

```python
import json

# json.dumps 给字符串加双引号
json.dumps('lwc-frame')
# → '"lwc-frame"'  （注意外层单引号是 Python 的字符串定界符，实际值是 "lwc-frame"）

# 嵌入 JavaScript 时的问题：
querySelectorAll("iframe[id="lwc-frame"]")
#                    ↑ JS 字符串结束  ↑ 新的 JS 标识符
# JavaScript 看到的是：字符串 "iframe[id=" + 标识符 lwc-frame + 字符串 "]"

# 正确做法：CSS 选择器内用单引号
querySelectorAll("iframe[id='lwc-frame']")
#                    ↑ 单引号不冲突 ✅
```

### getElementById 用双引号

```python
json.dumps('lwc-frame')  # → '"lwc-frame"'
document.getElementById("lwc-frame")  # ✅ 这里双引号是正确的
```

### Python f-string 大括号转义

```python
# {{ → {,  }} → }
f'while(x>1){{x--;}}'  # → while(x>1){x--;}
```

---

*文档结束*
