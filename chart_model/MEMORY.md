# chart_model 子系统记忆

> **状态**：🚧 开发中（v0.3+，主序列映射 + 示例完善）
> **最后更新**：2026-07-06（Drawing 支持 + 参数提示 + bug 修复）
> **注意**：此文件是 chart_model 内部记忆，不写入主 README 等正式文档

---

## 当前状态

| 阶段 | 状态 |
|------|------|
| 设计文档 v0.3 | ✅ 完成 |
| 3 个核心 dataclass | ✅ 完成 |
| Model.build() + Layout | ✅ 完成 |
| Adapter.render() | ✅ 完成 |
| 链式 API (SeriesAccessor) | ✅ 完成 |
| Marker (add_marker/add_markers) | ✅ 完成 |
| live 动态同步（互斥锁保护） | ✅ 完成 |
| 冒烟测试 | ✅ 10+ 项全过 |
| 示例 1 — hello_world | ✅ `examples/01_hello_world/minimal.py`（1Chart/2Pane/candle+vol/240次0.25s更新） |
| 示例 2 — multi_window_dashboard | ✅ `examples/02_multi_window_dashboard/demo.py`（2Window/5Chart/22Series/30次随机更新，多 Window 渲染） |
| 多 Window 渲染 | ✅ 遍历全部 Window，单 Window 返回 Chart，多 Window 返回 tuple[Chart, ...] |
| 同步线程 _render_ready 标志 | ✅ 从 `_render_chart` 改为 `_render_ready: bool`，支持多 chart 同步 |
| 示例 2 — demo 全更新 | ✅ 22 个 series 全部动态更新（含 MACD + 四品种 candle/OHLCBar） |
| 同步线程竞态修复 | ✅ `_series_locks` 互斥锁 + 版本号 + 三路同步 |
| 适配器 price_scale_id 修复 | ✅ `create_histogram` 不再接收 `price_scale_id`，仅支持的类型传递 |
| 适配器 ohlc_bar 主 series | ✅ 非 K线主 series 用工厂方法创建，不调 `chart.set()` |
| **主序列映射** | ✅ `_main_mapping` 替代 `primary_series`，`chart.candle/volume/oi.set()` 显式操作 |
| **示例 2 — stock2/stock3 volume+oi** | ✅ stock2(222) 和 stock3(223) 新增 volume/oi 主序列，动态更新 |
| **示例 2 — 指标正确计算** | ✅ 全量数据正确计算 SMA/RSI/EMA/MACD，替代随机数 |
| Drawing 支持 | ✅ DrawingManager 访问器 + 5 种类型 + 增量同步 + 参数提示（help/错误信息完整展示必选+可选参数） |
| Drawing 示例 3 — drawing_live | ✅ `examples/03_drawing_live/drawing_demo.py`（5 种画线类型 + K线 + SMA + 60s实时动态增删） |
| 适配器 sync_state 初始化 | ✅ `_render_series` 渲染后初始化 `_sync_state`，消除 `filter_old_bars` 告警 |
| 主 candle 颜色应用 | ✅ `chart.candle.candle_style()` 应用 Series 配置的 up_color/down_color |
| K线 OHLC 生成修复 | ✅ open 在 close 上下随机波动，不再永远阳线 |
| 参数提示优化 | ✅ `DrawingManager.help(type)` + 错误信息展示必选/可选参数完整 schema |
| 回测引擎 self.MC 对接 | ⏳ 待研究 |
| 序列化 (JSON/YAML) | ⏳ 待研究 |

---

## 文件结构

```
chart_model/
├── __init__.py          # 导出 System/Window/Chart/Series/SeriesType/SeriesAccessor/Adapter/parse_interval
├── models.py            # 全部 dataclass + build() + Layout + SeriesAccessor + parse_interval
├── adapter.py           # Adapter.render() + _series_kwargs() + _apply_markers() + _render_drawings()
├── AGENTS.md            # 给未来 agent 的指引
├── CHART_MODEL_DESIGN.md    # 设计文档 v0.3
├── CHART_MODEL_NEXT_STEPS.md# 下一步指南 v0.3
├── MEMORY.md            # 本文件（子系统专属记忆）
├── examples/
│   ├── 01_hello_world/
│   │   └── minimal.py   # 最小闭环：1 Chart × candle + volume，同步线程动态更新
│   ├── 02_multi_window_dashboard/
│   │   └── demo.py      # 多窗口仪表盘：2Window/5Chart/22Series/4pane/EMA品种/30次随机更新
│   └── 03_drawing_live/
│       └── drawing_demo.py  # 画线工具：5 种画线类型（水平线/垂直线/趋势线/射线/方框）
└── tests/
    └── smoke_test.py    # 冒烟测试
```

---

## 核心 API

### 声明结构

```python
from chart_model import System, Window, Chart, Series, Adapter

model = Model(
    windows=[Window(name='main', display_name='Demo')],
    charts=[
        Chart(name='price', display_name='Price', window='main',
              interval='1day', precision=2, position=211, sync_id='main'),
        Chart(name='ind', display_name='RSI', window='main',
              interval='1day', precision=4, position=212, sync_id='main'),
    ],
    series=[
        Series(name='candle', display_name='K线', chart='price', pane=0, type='candle'),
        Series(name='sma50', display_name='SMA50', chart='price', pane=0, type='line', color='#FF6F00'),
        Series(name='vol', display_name='Volume', chart='price', pane=1, type='volume'),
        Series(name='rsi', display_name='RSI', chart='ind', pane=0, type='line'),
    ],
)
```

### 数据操作（链式 API）

```python
model['candle'].set(df)                    # 设置全量 bar 数据
model['candle'].append(df_new)             # 追加（replace-or-append：仅替换最后一条）
model['candle'].pop(2)                     # 从末尾移除 2 根
model['candle'].data                       # → DataFrame
model['candle'].add_marker(time=..., position='below', shape='arrow_up', text='买入')
model['candle'].add_markers([{...}, {...}])
model['candle'].markers                    # → list[dict]
```

### 构建 + 渲染

```python
layout = model.build(live=True)            # 构建关系图 + 启动同步线程
chart = Adapter.render(layout, width=1000, height=800)  # 渲染到主库
chart.show(block=True)                       # 阻塞直到窗口关闭，同步线程持续工作
# ... 后续 model['name'].append() 自动同步到 chart ...
model.stop_sync()                          # 停止同步线程
```

---

## 实体类设计

### Window（极简）
| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| name | str | — | 标识名 |
| display_name | str | — | 显示名 |

### Chart
| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| name | str | — | 标识名 |
| display_name | str | — | 显示名 |
| window | str | — | 所属 Window 引用 |
| interval | int\|str | — | **必选**。秒数或 '1day'/'5min'/'15sec' |
| precision | int | 2 | 价格精度 |
| position | int | 111 | 网格位置 (211=2行1列第1格) |
| width | float | 1.0 | 相对网格单元宽度 |
| height | float | 1.0 | 相对网格单元高度 |
| xy | tuple\|None | None | 绝对坐标 (x,y)，设定后切换 set_position 模式 |
| sync_id | str\|None | None | 同步组名 |

### Series（8 种类型，全量属性）
| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| name | str | — | 标识名 |
| display_name | str | — | 显示名 |
| chart | str | — | 所属 Chart 引用 |
| pane | int | 0 | Pane 编号 |
| type | str | "line" | candle/ohlc_bar/line/area/baseline/histogram/volume/open_interest |
| visible | bool | True | |
| color | str | "#2962FF" | |
| line_width | int | 2 | |
| line_style | str | "solid" | |
| price_scale_id | str\|None | "right" | left/right/None(独立) |
| price_line | bool | False | |
| price_label | bool | True | |
| legend | bool | True | |
| group | str\|None | None | 图例分组 |

Candle/OHLCBar 独有：up_color, down_color, border_visible, wick_visible, crosshair_marker
OHLCBar 独有：open_visible, thin_bars
Area 独有：top_color, bottom_color, relative_gradient, invert_filled_area
Baseline 独有：base_value, top/bottom_fill_color1/2, top/bottom_line_color
Histogram 独有：scale_margin_top, scale_margin_bottom（+ data 中 color 列）

**注意**：Series 声明时**不带 data**，数据通过 `model['name'].set()` 设置。

---

## 设计决策

| # | 决策 | 说明 |
|---|------|------|
| 1 | 声明式扁平化 | Model 持有同级 Window/Chart/Series 列表，名称引用关联 |
| 2 | 结构不可变 | 声明后不能增删实体，只能改数据/属性 |
| 3 | Series 不带 data | 声明时只描述结构，数据通过链式 API 设置 |
| 4 | interval 必选 | 每个 Chart 必须指定时间级别（int 或 str） |
| 5 | 每 pane 一个 K线 | build() 中 Indicator 约束验证 |
| 6 | 统一输入契约 | 所有 Series 统一 time + value 列 |
| 7 | 其他实体暂不实现 | Marker 已实现（通过 SeriesAccessor），Drawing/PriceLine/TopBar/Table 暂不实现 |
| 8 | append 是 replace-or-append | 新数据首条时间 == 已有最后时间 → 替换最后一条；否则纯追加 |
| 9 | 同步线程是唯一渲染通道 | 不允许直连渲染层，所有更新必须通过同步线程 |

---

## live 动态同步机制

**触发**：`model.build(live=True)` 启动守护线程（检测频率 0.1 秒）

**核心设计**：每个 series 独立版本号 + 互斥锁，精细化检测

### 版本号机制

- `_series_versions[name]` — 每 series 当前版本号（`set/append/pop/add_marker` 递增）
- `_sync_last_versions[name]` — 每 series 上次同步时的版本号
- 同步线程通过比较两者，只同步有变化的 series，不遍历全部

### 互斥锁保护

- `_series_locks[name]` — 每个 series 一把 `threading.Lock`（`defaultdict` 自动管理）
- 在 `_do_sync()` 中推送渲染层前加锁，推送完成后解锁
- 确保同一 series 的渲染层调用不会被其他线程打断

### 三路数据同步分支

| 条件 | 行为 | 场景 |
|------|------|------|
| `rows↑`（追加） | `update_bars(新增部分)` | 追加新 bar |
| `rows↓`（删除） | `set(全量重置)` | pop 或全量 set 替换 |
| `rows＝`（修改） | `update_bar(最后一根bar)` | 行数不变但数据变了 |

### Marker 同步

- `_sync_last_marker_counts[name]` — 每 series 上次同步的标记数量
- 同步时比较当前数量，只增量推送新增标记

### 同步流程

```
_sync_last_versions[name] != _series_versions[name] ?
  ↓ 有变化
lock = _series_locks[name]  # 获取互斥锁
with lock:
  同步数据：
    _sync_state[name] vs len(df)
    ├── 多了 → update_bars(新增)
    ├── 少了 → set(全量)
    └── 没变 → update_bar(最后)
  同步 markers：
    _sync_last_marker_counts[name] vs len(markers)
    └── 多了 → add_marker(新增 ×N)
  更新 _sync_last_versions / _sync_state / _sync_last_marker_counts
```

### 关键属性（System 内部）

- `_series_versions: dict` — {series_name: version}
- `_sync_state: dict` — {series_name: last_synced_row_count}
- `_sync_last_versions: dict` — {series_name: last_synced_version}
- `_sync_last_marker_counts: dict` — {series_name: last_synced_marker_count}
- `_series_locks: dict` — {series_name: Lock}（defaultdict 自动管理）
- `_render_chart: object` — 主库 chart 引用（Adapter.render 设置）
- `_series_map: dict` — {series_name: 主库 series 对象}
- `_sync_thread / _stop_event` — 线程控制

**容错**：同步失败不影响数据层（try/except）

---

## 适配器翻译规则

| chart_model | 主库 API |
|---------|---------|
| Window | Chart（独立桌面窗口），`render()` 返回单 Chart 或 tuple |
| Chart.position | Chart(position=...) / create_subchart(position=...) |
| Chart.interval | chart.set_period(parse_interval(interval)) |
| Chart.precision | chart.price_scale(price_format={...}) |
| Chart.xy | chart.set_position(x, y, width, height) |
| Chart.sync_id | Chart(sync_id=...) / create_subchart(sync_id=...) |
| Series(主K线) | chart.set(df) |
| Series(volume) | chart.volume.set(df) |
| Series(open_interest) | chart.oi.set(df) |
| Series(其他) | chart.create_line/area/...(**kwargs) + .set(df) |
| Marker | series.add_marker(**marker_dict) |
| Series.pane | pane_index 参数 |

---

## interval 字符串解析

`parse_interval()` 支持的格式：
- `'15sec'` / `'15s'` → 15
- `'5min'` / `'5mins'` → 300
- `'1hour'` / `'1h'` → 3600
- `'1day'` / `'1d'` → 86400
- `'1week'` / `'1w'` → 604800
- 纯数字 `60` → 60（秒）

---

## 已知限制

1. **live 同步只处理 bar 数据**（append/set/pop），不处理 tick
2. **Marker 只存储不验证**（time 是否在 series 数据范围内不检查）
3. **Drawing/PriceLine/TopBar/Table** 暂不实现

---

## 版本演进

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.1 | 07-03 | 概念探索，11 条决策，5 种 Series |
| v0.2 | 07-03 | 对齐主库 v3.0.1，12 项差距修复，8 种 Series + Drawing + TopBar/Table |
| v0.3 | 07-03 | 大幅简化为最小可用：Window 极简 / Chart 精简 / Series 全量 / 其他砍掉 |
| v0.3+ | 07-03 | 实现：3 dataclass + build() + Adapter + 链式API + Marker + live同步 |
| v0.3+ | 07-03 | 精细化同步：全局_version→series级别_series_versions / marker同步 / 追加时保护旧bar / 行数不变时update_bar |
| v0.3+ | 07-04 | 复杂示例完成：2Window/5Chart/22Series/4pane/EMA品种/随机30次更新 / 数据层唯一数据源 / 同步线程部分修复 |
| v0.3+ | 07-04 | 修复同步线程竞态：加 `_series_locks` 互斥锁 + 去掉直连 + `chart.show(block=True)` |
| v0.3+ | 07-04 | append_data 改为 replace-or-append 模式；同步线程检测频率 0.1s；示例交换序号 |
| v0.3+ | 07-06 | 主序列映射 `_main_mapping`：替代 `primary_series`，`chart.candle/volume/oi.set()` 显式操作 |
| v0.3+ | 07-06 | 适配器重写：`_render_series()` 使用 `_main_mapping`，移除 `chart.set()` 自动分发 |
| v0.3+ | 07-06 | demo 完善：stock2/stock3 新增 volume/oi 主序列 + 指标正确计算 + K线随机红绿 |
| v0.3+ | 07-06 | 修复：live_feed 中 `if idx==2 or idx==3` 缩进错误导致 volume/oi 从未更新 |

---

*chart_model 子系统记忆，泰斗先生 × 小音，2026-07-04*
