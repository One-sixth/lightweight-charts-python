# v2.5.1 → v3.0 迁移指南

**更新日期**：2026-07-01

本指南帮助 `lightweight-charts-python` 的 **v2.5.1（上次发布版本）** 用户平稳迁移到 **v3.0**。

---

## 一、版本演进速览

v2.5.1 → v3.0 经历了 **15 个子版本**、**21 天密集开发**。以下是关键里程碑：

| 版本 | 核心变更 |
|------|---------|
| v2.6.0 | `sync` → `sync_id` 组同步重构 |
| v2.7.0 | 组合架构重构（Volume/OI 独立化、固定 ID） |
| v2.8.0 | 统一输入契约（列名标准化、normal_df 精简） |
| v2.8.1 | 新增 Area/OHLCBar/Baseline 三种 Series |
| v2.8.2 | Pane Primitive 架构、ToolBox on_change |
| v2.8.3 | API 全面清理（旧别名/方法/参数移除） |
| v2.8.6 | TimeScaleApi、PriceScaleApi |

---

## 二、Breaking Changes 逐项迁移

### 2.1 同步机制：`sync` → `sync_id`

**旧写法（v2.5.1）：**
```python
chart = Chart()
sub = chart.create_subchart(sync=chart.id)  # 传入 chart.id
```

**新写法（v3.0）：**
```python
chart = Chart(sync_id='main')              # 主图加入 'main' 组
sub = chart.create_subchart(sync_id='main') # 子图加入同一组
```

**迁移说明：**
- `sync=chart.id` → `sync_id='组名'`（任意字符串）
- 同组图表自动互相同步，无需知道彼此的 ID
- `True` → 转为 `'True'` 作为组名
- `False/None` → 不同步
- 运行时动态加入：`chart.join_sync_group('组名')`

---

### 2.2 类重命名

| 旧名称（v2.5.1） | 新名称（v3.0） |
|------------------|---------------|
| `Line` | `LineSeries` |
| `Histogram` | `HistogramSeries` |
| `chart.create_line()` | **不变**（返回值从 `Line` → `LineSeries`） |
| `chart.create_histogram()` | **不变**（返回值从 `Histogram` → `HistogramSeries`） |
| `chart.lines()` | **不变**（返回值从 `list[Line|Histogram]` → `list[SeriesCommon]`） |

> ⚠️ `Line` 和 `Histogram` 类名已在 v2.8.3 正式移除。使用 `LineSeries` / `HistogramSeries`。

---

### 2.3 方法重命名

| 旧方法 | 新方法 | 说明 |
|--------|--------|------|
| `update_from_tick(series)` | `update_tick(series)` | Tick 单条更新 |
| `update_from_ticks(df)` | `update_ticks(df)` | Tick 批量更新 |
| `chart.update(series)` | `chart.update_bar(series)` | K 线单条更新 |
| `series.update(series)` | `series.update_bar(series)` | 系列单条更新 |
| `marker(...)` | `add_marker(...)` | 添加标记（v3.0 新增 `add_` 前缀） |
| `markers([...])` | `add_markers([...])` | 批量添加标记（v3.0 新增 `add_` 前缀） |
| `markers`（方法名） | `markers`（列表属性） | v3.0 中 `markers` 变为查看标记列表的属性 |

**迁移示例：**
```python
# ❌ v2.5.1
chart.update(tick)
chart.marker(time='2024-01-15', position='above', ...)
chart.markers([{time, position, ...}, ...])

# ✅ v3.0
chart.update_bar(new_bar)           # update → update_bar
chart.update_tick(tick)             # update_from_tick → update_tick
chart.add_marker(time='2024-01-15', position='above', ...)  # marker → add_marker
chart.add_markers([{time, position, ...}, ...])              # markers → add_markers
print(chart.markers)                # markers 属性：查看标记列表
```
```

---

### 2.4 组合架构变化（v2.7.0）

#### Volume / OI 管理变化

| 旧方式（v2.5.1） | 新方式（v3.0） |
|------------------|---------------|
| `candle.attach_volume(df)` | `chart.volume` 自动管理 |
| `candle.attach_open_interest(df)` | `chart.oi` 自动管理 |
| `chart.volume_config()` | ✅ 不变 |
| `chart.open_interest_config()` | ✅ 不变 |

**迁移示例：**
```python
# ❌ v2.5.1 — 手动 attach
df = pd.read_csv('data.csv')
chart.set(df[['time', 'open', 'high', 'low', 'close']])
chart.candle.attach_volume(df[['time', 'volume']])
chart.candle.attach_open_interest(df[['time', 'open_interest']])

# ✅ v3.0 — 自动管理
chart.set(df)  # volume/open_interest 列自动填充
# chart.volume 和 chart.oi 始终存在，直接使用
```

#### CandleSeries delete/clear_data 不再级联

| 操作 | v2.5.1 | v3.0 |
|------|--------|------|
| `candle.delete()` | 同时删除 volume/OI | 只删除自身 |
| `candle.clear_data()` | 同时清空 volume/OI | 只清自身 |
| `chart.clear_data()` | 不存在 | ✅ 统一清理三者 |

---

### 2.5 统一输入契约（v2.8.0）

#### normal_df 行为变化

| 场景 | v2.5.1 | v3.0 |
|------|--------|------|
| 列名自动小写 | ✅ 自动转小写 | ❌ 不再转换 |
| `date` → `time` | ✅ 自动重命名 | ❌ 需要手动 rename |
| 统一输入列 | 各系列格式不一 | ✅ 统一 `time` + `value` |

**迁移示例：**
```python
# ❌ v2.5.1 — 依赖自动转换
df = pd.read_csv('data.csv')  # 列名含 Date/Open/High...
chart.set(df)  # 自动转换

# ✅ v3.0 — 精确匹配列名
df = pd.read_csv('data.csv').rename(columns={
    'Date': 'time', 'Open': 'open', 'High': 'high',
    'Low': 'low', 'Close': 'close', 'Volume': 'volume'
})
chart.set(df)
```

#### VolumeSeries 着色要求

v3.0 中 VolumeSeries 要求输入包含 `open`/`close` 列用于涨跌着色：

```python
# ✅ v3.0 — 通过 chart.set() 自动带上 open/close
chart.set(df)  # df 含 open/close → 自动转发

# ✅ 直接设置 volume
vol_df = pd.DataFrame({
    'time': [...],
    'value': [...],
    'open': [...],   # 必需
    'close': [...]   # 必需
})
chart.volume.set(vol_df)
```

#### AbstractChart 不联动 `_lines`

```python
# ❌ v2.5.1 — 假设 chart.set() 自动填充 line
line = chart.create_line('SMA')
chart.set(df)  # 旧版会自动填充 line

# ✅ v3.0 — 手动为每个 line 设置数据
line = chart.create_line('SMA')
line.set(sma_df)  # 独立设置，df 需含 time + value 列
chart.set(df)
```

---

### 2.6 ToolBox 变化

#### 回调注册

```python
# ❌ v2.5.1 — save_drawings_under
chart.toolbox.save_drawings_under(chart.topbar['symbol'])

# ✅ v3.0 — on_change 回调（支持多回调）
def on_drawing_change(drawings):
    for d in drawings:
        print(f"Drawing {d.id}: type={d.type}")

chart.toolbox.on_change += on_drawing_change
info_list = chart.toolbox.drawings_list  # 获取当前所有绘图
```

#### 持久化方法移除

| 方法 | 替代方案 |
|------|---------|
| `save_drawings_under(widget)` | `on_change` 回调自行持久化 |
| `load_drawings(tag)` | `on_change` 回调自行持久化 |
| `import_drawings(path)` | `on_change` 回调自行持久化 |
| `export_drawings(path)` | `on_change` 回调自行持久化 |

#### Drawing 架构变化

| 旧 | 新 |
|----|----|
| `ISeriesPrimitive` | `IPanePrimitive`（直接附着 pane） |
| `chart._drawings` 列表 | `chart._drawing_series` 字典（按 pane_index） |
| Drawing 依赖 series 数据 | 不依赖 series 数据状态 |

```python
# ✅ v3.0 — 跨 Pane 绘图
h_line = chart.horizontal_line(price=200, pane_index=1)  # 指定 pane
box = chart.box(start_time, start_price, end_time, end_price, pane_index=1)
```

#### Ctrl+Z 撤销移除

ToolBox 不再内置 Ctrl+Z 撤销支持。如需撤销功能，请自行实现。

---

### 2.7 其他参数变化

| 参数 | 变化 | 迁移 |
|------|------|------|
| `chart.price_scale(perm_width=N)` | 已移除 | 删除该参数 |
| `chart.price_scale()` 默认值 | 硬编码 → `None` | 依赖旧默认值时需显式传入 |
| `cumulative_volume` | 已移除 | 无替代 |
| `sync` 参数 | 已移除 | 改为 `sync_id='组名'` |

---

## 三、新增功能速览

### 3.1 新增 Series 类型

| Series | 工厂方法 | 数据格式 | 版本引入 |
|--------|---------|---------|---------|
| **AreaSeries**（面积图） | `chart.create_area_series()` | time + value | v2.8.1 |
| **OHLCBarSeries**（美国线） | `chart.create_ohlc_bar_series()` | time + O/H/L/C | v2.8.1 |
| **BaselineSeries**（基准线） | `chart.create_baseline_series()` | time + value | v2.8.1 |

### 3.2 新增 API

| API | 说明 |
|-----|------|
| `chart.time_scale_api()` | 时间轴完整控制（14 方法） |
| `chart.price_scale_api(scale_id)` | 价格轴完整控制（6 方法） |
| `chart.fit()` | 数据适应视口 |
| `chart.show(wait=N)` | 计时自动关闭窗口 |
| `chart.toolbox.on_change += func` | 绘图变化回调 |
| `chart.toolbox.drawings_list` | 获取当前所有绘图 |
| `chart.marker_auto_scale(enable)` | 标记价格轴缩放 |

### 3.3 HtmlTabChart 增强

| 功能 | 说明 |
|------|------|
| **init 快照重放** | `new_window()` 自动重放全量 init 命令 |
| **ToolBox 支持** | 静态图表工具箱支持 |
| **多 tab legend 修复** | 切换 tab 后 legend 正常显示 |
| **iframe 嵌入** | 双文件方案（外壳 + 内容） |

### 3.4 Histogram 任意颜色

```python
hist = chart.create_histogram('Delta')
hist.set(pd.DataFrame({
    'time': [1, 2, 3],
    'value': [100, -200, 150],
    'color': ['#26a69a', '#ef5350', '#26a69a'],  # 每根柱子独立颜色
}))
```

---

## 四、常见迁移陷阱

### 4.1 列名不匹配

**症状**：K 线显示异常、volume 不显示

**原因**：v3.0 不再自动转小写和 `date→time`

**解决**：确保 DataFrame 列名精确为 `time, open, high, low, close, volume, open_interest`

### 4.2 ToolBox 回调未触发

**症状**：绘图后无响应

**原因**：使用了已移除的 `save_drawings_under()` 代替 `on_change`

**解决**：改用 `chart.toolbox.on_change += my_callback`

### 4.3 volume 颜色全灰

**症状**：成交量柱状图全部显示为灰色

**原因**：VolumeSeries 缺少 `open`/`close` 列无法着色

**解决**：确保 `chart.set(df)` 的 df 包含 `open` 和 `close` 列

### 4.4 Line 不显示数据

**症状**：`create_line()` 后折线不显示

**原因**：v3.0 不再由 `chart.set()` 自动转发数据给 line

**解决**：手动调用 `line.set(df)` 设置数据

### 4.5 update_ticks 卡死

**症状**：`update_ticks()` 调用后程序无响应

**原因**：pywebview 的 `evaluate_js` 无法序列化 lightweight-charts API 对象

**解决**：确保 JS 调用末尾有 `;0`（v2.6.1 已修复，更新到最新版即可）

### 4.6 多图表 handler 冲突

**症状**：多 Chart 实例共享 Window 时回调异常

**原因**：`_clear_handlers()` 清空了其他图表的 handler

**解决**：使用 `_remove_my_handlers()` 按 salt 精确清除

---

## 五、验证清单

迁移完成后，逐项验证：

### API 兼容性

- [ ] `sync_id` 代替 `sync`，同步组正常工作
- [ ] `chart.set(df)` 使用正确列名（不再依赖自动转换）
- [ ] `chart.update_bar()` 代替 `chart.update()`
- [ ] `chart.update_ticks()` 代替 `chart.update_from_ticks()`
- [ ] `chart.add_marker()`（代替旧 `chart.marker()`）正常工作
- [ ] `chart.add_markers()`（代替旧 `chart.markers()`）正常工作
- [ ] `chart.markers` 属性返回标记列表
- [ ] volume 数据正常显示（含涨跌着色）
- [ ] Line/Histogram 手动设置数据后正常显示
- [ ] ToolBox 绘图变化通过 `on_change` 回调获取
- [ ] 多图表场景 handler 无冲突

### 功能完整性

- [ ] K 线/成交量/持仓量数据显示正常
- [ ] 标记（marker）显示正常
- [ ] 子图表（subchart）创建和布局正常
- [ ] 图表同步（sync_id）正常工作
- [ ] reset_sub() 清除后重建正常
- [ ] ToolBox 跨 Pane 绘图正常
- [ ] Legend 图例（含分组）显示正常
- [ ] HtmlTabChart 多 tab 切换正常

### 可选项

- [ ] 使用新 API：`chart.time_scale_api()` / `chart.price_scale_api()`
- [ ] 使用新 Series：AreaSeries / OHLCBarSeries / BaselineSeries
- [ ] Histogram 任意颜色支持
- [ ] `chart.show(wait=N)` 计时自动关闭

---

## 六、相关文档

| 文档 | 位置 |
|------|------|
| CHANGELOG 完整版本历史 | `CHANGELOG.md` |
| QUICK_REFERENCE 快查文档 | `QUICK_REFERENCE.md` |
| 项目长期记忆 | `MEMORY.md` |
| Agent 操作指南 | `AGENT.md` |
