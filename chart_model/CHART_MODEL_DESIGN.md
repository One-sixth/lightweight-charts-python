# 指标系统（chart_model）设计文档

> **版本**：0.3（最小可用版本）
> **日期**：2026-07-03
> **状态**：✅ 设计已确定，待实现
> **变更**：v0.2 → v0.3，大幅简化，聚焦 Series + 基础容器

---

## 一、设计理念

**声明式、扁平化、引用式的纯数据模型。最小可用。**

```
              System (根容器)
             ╱              ╲
        Window              Series
          │                   │
       (tile+名字)      (8种类型，全量属性)
          │
        Chart
      (precision+
      set_period+
      少量基本属性)
```

- 所有实体同级，通过名称引用关联
- **纯数据类**，零渲染逻辑，零外部依赖
- 当前只实现 3 个实体类：**Window / Chart / Series**
- 其他实体（Marker / Drawing / PriceLine / TopBar / Table）暂不实现，留到后续版本

### v0.2 → v0.3 简化原则

| 原则 | 说明 |
|------|------|
| **Series 全量** | 8 种类型 + 完整属性，因为已统一结构，全部支持 |
| **Window 极简** | 只保留 tile（分屏布局）+ 名字 |
| **Chart 精简** | 少量基本属性 + precision + set_period |
| **其他砍掉** | Marker/Drawing/PriceLine/TopBar/Table 暂不抽象 |
| **目标** | 简单快速，生成可用的指标系统 |

---

## 二、设计决策

| 序号 | 决策事项 | 结论 |
|------|----------|------|
| 1 | **模型风格** | 声明式、扁平化、引用式 |
| 2 | **结构可变性** | 声明后结构不可变，只能改数据和属性 |
| 3 | **Window** | 只支持 tile + 名字，其他属性全部砍掉 |
| 4 | **Chart** | 少量基本属性 + precision + set_period |
| 5 | **Series** | 全量支持，8 种类型 + 完整属性 |
| 6 | **其他实体** | 暂不实现（Marker/Drawing/PriceLine/TopBar/Table） |
| 7 | **Pane** | 纯数字编号，0 = 主 pane |
| 8 | **统一输入契约** | 所有 Series 统一 `time` + `value` 列 |
| 9 | **主图判定** | Window 内首个 Chart = 主图；pane 0 首个 candle = 主 series |
| 10 | **Indicator 约束** | 每个 pane 只能一个 K线类型（candle / ohlc_bar） |
| 11 | **Indicator 三类型** | K线（OHLCVo）/ 画线 / 标记 → 对应 Series（标记暂不实现） |
| 12 | **self.MC 对接** | 值=简易模式，字典=详细模式 |

---

## 三、核心类设计

### 3.1 `Model` — 根容器

```python
@dataclass
class System:
    windows: list[Window]
    charts: list[Chart]
    series: list[Series]

    def set_data(self, series_name: str, data) -> None: ...   # 预留
    def update(self, series_name: str, data) -> None: ...     # 预留
    def build(self) -> "Layout": ...
```

### 3.2 `Window` — 窗口（极简）

```python
@dataclass
class Window:
    name: str                     # 内部标识名（全局唯一）
    display_name: str             # 显示名
    tile: tuple[int, int] = (1, 1)  # 分屏布局 (rows, cols)
```

- `tile` 描述窗口的分屏规格，如 `(2, 2)` = 2行2列共 4 个区域
- 默认 `(1, 1)` = 单图满屏
- 其他属性（width/height/title/toolbox 等）暂不支持

### 3.3 `Chart` — 图表（精简）

```python
@dataclass
class Chart:
    name: str                     # 内部标识名（全局唯一）
    display_name: str             # 显示名
    window: str                   # 所属 Window 的名称引用
    tile_index: int = 0           # 在 Window.tile 中的位置索引（0-based，左上→右下）

    # ── 基本属性 ──
    precision: int = 2            # 价格精度（小数位数）
    set_period: int | None = None # 锁定时间级别（秒数），None = 自动推断
```

- `tile_index` 对应 Window.tile 网格中的位置（行优先排列）
- `precision` 对应主库的 `price_format={'type': 'price', 'precision': N}`
- `set_period` 对应主库的 `chart.set_period(seconds)`，None 时自动推断
- 其他样式属性（background_color/crosshair/grid/legend 等）暂不支持

### 3.4 `Series` — 数据系列（全量支持）

```python
@dataclass
class Series:
    name: str                     # 内部标识名（全局唯一）
    display_name: str             # 显示名（用于图例）
    chart: str                    # 所属 Chart 的名称引用
    pane: int = 0                 # Pane 编号（0=主pane）
    type: str = "line"            # 系列类型（见 3.4.1）
    data: pd.DataFrame | None = None  # 数据（统一 time + value 契约）

    # ── 通用属性 ──
    visible: bool = True
    color: str = "#2962FF"
    line_width: int = 2
    line_style: str = "solid"     # solid / dotted / dashed / large_dashed / sparse_dotted
    price_scale_id: str | None = "right"  # left / right / None(独立价格轴)
    price_line: bool = False      # 是否显示价格线
    price_label: bool = True      # 是否显示价格标签
    legend: bool = True           # 是否在图例中显示
    group: str | None = None      # 图例分组名

    # ── Candle / OHLCBar 独有 ──
    up_color: str = "rgba(39,157,130,100)"
    down_color: str = "rgba(200,97,100,100)"
    border_visible: bool = True
    wick_visible: bool = True
    crosshair_marker: bool = True

    # ── OHLCBar 独有 ──
    open_visible: bool = True
    thin_bars: bool = True

    # ── Area 独有 ──
    top_color: str = "rgba(33,150,243,0.4)"
    bottom_color: str = "rgba(33,150,243,0)"
    relative_gradient: bool = False
    invert_filled_area: bool = False

    # ── Baseline 独有 ──
    base_value: float = 0
    top_fill_color1: str = "rgba(38,166,154,0.28)"
    top_fill_color2: str = "rgba(38,166,154,0.05)"
    top_line_color: str = "rgba(38,166,154,1)"
    bottom_fill_color1: str = "rgba(239,83,80,0.05)"
    bottom_fill_color2: str = "rgba(239,83,80,0.28)"
    bottom_line_color: str = "rgba(239,83,80,1)"

    # ── Histogram 独有 ──
    # data 中的 color 列支持每根柱子独立着色
    scale_margin_top: float = 0.0
    scale_margin_bottom: float = 0.0
```

#### 3.4.1 支持的 Series 类型（8 种）

| `type` 值 | 对应主库实体 | 数据列要求 | 说明 |
|-----------|------------|-----------|------|
| `"candle"` | CandleSeries | `time, open, high, low, close` | K线 |
| `"ohlc_bar"` | OHLCBarSeries | `time, open, high, low, close` | 美国线 |
| `"line"` | LineSeries | `time, value` | 折线 |
| `"area"` | AreaSeries | `time, value` | 面积图 |
| `"baseline"` | BaselineSeries | `time, value` | 基准线 |
| `"histogram"` | HistogramSeries | `time, value, [color]` | 柱状图 |
| `"volume"` | VolumeSeries | `time, value, open, close` | 成交量 |
| `"open_interest"` | OpenInterestSeries | `time, value` | 持仓量 |

> **统一输入契约**：所有 Series 统一 `time` + `value`。
> Candle/OHLCBar 额外需 OHLC；Volume 额外需 open/close；Histogram 可选 color 列。

### 3.5 其他实体（暂不实现）

以下实体在 v0.3 中**不实现**，留到后续版本：

| 实体 | 主库对应 | 恢复优先级 | 说明 |
|------|---------|-----------|------|
| Marker | `series.add_marker()` | 高 | 标记点，指标常用 |
| Drawing | `chart.horizontal_line()` 等 | 中 | 绘图对象 |
| PriceLine | `chart.create_price_line()` | 中 | 价格线 |
| TopBar | `chart.topbar.textbox()` 等 | 低 | 顶栏组件 |
| Table | `chart.create_table()` | 低 | 浮动表格 |

> v0.2 中有这些实体的完整设计，恢复时可参考 `CHART_MODEL_NEXT_STEPS.md` 的 v0.2 归档。

---

## 四、关系解析机制

```python
def build(self) -> "Layout":
    # 1. 验证名称唯一性
    assert_unique_names(self.windows, "window")
    assert_unique_names(self.charts, "chart")
    assert_unique_names(self.series, "series")

    # 2. 构建 Window → Chart 映射
    window_charts = group_by(self.charts, lambda c: c.window)

    # 3. 构建 Chart → Series 映射
    chart_series = group_by(self.series, lambda s: s.chart)

    # 4. 构建 Chart → Pane 映射
    pane_info = {}
    for chart_name, series_list in chart_series.items():
        pane_info[chart_name] = group_by(series_list, lambda s: s.pane)

    # 5. Indicator 约束验证：每 pane 只能一个 K线类型
    for chart_name, panes in pane_info.items():
        for pane_num, series_list in panes.items():
            kline_count = sum(1 for s in series_list if s.type in ("candle", "ohlc_bar"))
            assert kline_count <= 1, \
                f"Chart '{chart_name}' pane {pane_num} 有 {kline_count} 个 K线类型，限制 1 个"

    # 6. 确定主图：每个 Window 内的首个 Chart
    primary_charts = {w.name: window_charts[w.name][0].name
                      for w in self.windows if window_charts.get(w.name)}

    # 7. 确定主 series：pane 0 首个 candle/ohlc_bar
    primary_series = {}
    for chart_name, panes in pane_info.items():
        pane0 = panes.get(0, [])
        candle = next((s for s in pane0 if s.type in ("candle", "ohlc_bar")), None)
        if candle:
            primary_series[chart_name] = candle.name

    return Layout(
        windows=self.windows, charts=self.charts, series=self.series,
        pane_info=pane_info,
        primary_charts=primary_charts,
        primary_series=primary_series,
    )
```

### ModelLayout

```python
@dataclass
class Layout:
    windows: list[Window]
    charts: list[Chart]
    series: list[Series]
    pane_info: dict[str, dict[int, list[Series]]]  # chart → {pane → [series]}
    primary_charts: dict[str, str]                  # window → 主 chart name
    primary_series: dict[str, str]                  # chart → 主 series name
```

---

## 五、与 lightweight-charts 的适配器（未来）

```python
class Adapter:
    @staticmethod
    def render(layout: Layout):
        """翻译 Layout → lightweight-charts 渲染实例。"""
        for window in layout.windows:
            # 1. 创建窗口（Chart / HtmlTabChart）
            chart = Chart(width=..., height=...)

            # 2. 配置 precision
            chart.price_scale(price_format={'type': 'price', 'precision': chart_obj.precision})

            # 3. 配置 set_period
            if chart_obj.set_period is not None:
                chart.set_period(chart_obj.set_period)

            # 4. 创建子图（tile_index > 0 的 Chart）
            for chart_obj in window_charts[1:]:
                chart.create_subchart(position=tile_to_position(window.tile, chart_obj.tile_index))

            # 5. 创建 Series
            for series in chart_series:
                if series.name == primary_series:  # 主K线
                    chart.set(series.data)
                else:
                    factory = TYPE_FACTORY[series.type]  # create_line / create_area / ...
                    s = factory(chart, **series_attrs)
                    s.set(series.data)
```

**翻译规则（精简版）：**

| chart_model | 主库 API |
|---------|---------|
| `Window.tile` | `Chart(position=...)` 网格布局 |
| `Chart.precision` | `chart.price_scale(price_format={...})` |
| `Chart.set_period` | `chart.set_period(seconds)` |
| `Chart.tile_index` | `create_subchart(position=...)` |
| Series (主K线) | `chart.set(df)` |
| Series (附加) | `chart.create_line/area/...(**attrs)` + `s.set(df)` |
| `Series.pane` | `pane_index` 参数 |
| `Series.group` | `group` 参数 |

---

## 六、待实现事项

### 当前版本（v0.3）待实现

| 事项 | 状态 |
|------|------|
| 3 个 dataclass（Window/Chart/Series） | ⏳ 待编码 |
| ModelLayout + build() | ⏳ 待编码 |
| 适配器 Adapter.render() | ⏳ 待编码 |
| self.MC 简易/详细模式格式 | 🟡 待确认属性全集 |

### 后续版本待恢复

| 事项 | 目标版本 | 说明 |
|------|---------|------|
| Marker | v0.4+ | 标记点，指标常用，优先恢复 |
| Drawing | v0.5+ | 6 种绘图类型 |
| PriceLine | v0.5+ | 价格线 |
| TopBar / Table | v0.6+ | UI 组件 |
| 事件回调 | v0.6+ | on_click / on_search 等 |
| 动态更新（场景B） | v0.6+ | 实时增量推送 |
| 序列化 | v0.7+ | JSON/YAML 导入导出 |

---

## 七、给新会话的指引 👋

1. **读这份文档**，了解 v0.3 最小可用设计
2. **项目路径**：`D:\Data\github_repo\lightweight-charts-onesixth`
3. **Python 环境**：`D:\Software\miniconda3\envs\normal\python.exe`
4. **主库 API 参考**：`QUICK_REFERENCE.md`
5. **下一步**：用 dataclass 实现 3 个类 + build() + 适配器
6. **v0.2 完整设计**（含 Marker/Drawing/TopBar/Table）：见 `CHART_MODEL_NEXT_STEPS.md` 归档

### v0.2 → v0.3 变更摘要

| 变更 | 说明 |
|------|------|
| Window 简化 | 15+ 属性 → 只保留 name + tile |
| Chart 简化 | 15+ 属性 → 精简 + precision + set_period |
| Series 不变 | 8 种类型 + 完整属性（全量保留） |
| Marker 砍掉 | 暂不实现，v0.4+ 恢复 |
| Drawing 砍掉 | 暂不实现，v0.5+ 恢复 |
| PriceLine 砍掉 | 暂不实现 |
| TopBar 砍掉 | 暂不实现 |
| Table 砍掉 | 暂不实现 |
| build() 简化 | 13 步 → 7 步 |
| 适配器简化 | 18 条规则 → 精简版 |

---

*2026-07-03*
*v0.3：最小可用版本，大幅简化*
