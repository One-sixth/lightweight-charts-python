# chart_model 下一步指南

> v0.3+ — 主序列映射 + 多 Window 渲染 + 示例完善已完成
> 设计文档：`CHART_MODEL_DESIGN.md`（v0.3）

---

## 当前状态

| 阶段 | 状态 |
|------|------|
| 设计文档 v0.3 | ✅ 完成 |
| 3 个核心 dataclass | ✅ 完成 |
| build() + Layout | ✅ 完成 |
| 链式 API (SeriesAccessor) | ✅ 完成 |
| Marker (add_marker/add_markers) | ✅ 完成 |
| live 动态同步 | ✅ 互斥锁 + 版本号 + 三路同步 |
| 多 Window 渲染 | ✅ 遍历全部 Window，单/多返回自适应 |
| 主序列映射 `_main_mapping` | ✅ 替代 `primary_series`，`chart.candle/volume/oi.set()` 显式操作 |
| 适配器重写 | ✅ `_render_series()` 使用 `_main_mapping`，移除 `chart.set()` 自动分发 |
| 同步线程竞态修复 | ✅ `_series_locks` 互斥锁 + 版本号 + 三路同步 |
| 适配器修复 | ✅ price_scale_id 仅支持的类型传递；ohlc_bar 主 series 用工厂方法 |
| 示例 2 — demo | ✅ 2 Window 多窗口渲染，26 series（含 volume/oi），全量动态更新 |
| 冒烟测试 | ✅ 10+ 项 |

---

## 实现计划

### 文件结构

```
chart_model/
├── __init__.py          # 导出公开类
├── models.py            # Window, Chart, Series, System（全部 dataclass）
├── layout.py            # ModelLayout
├── builder.py           # Model.build()
├── enums.py             # SeriesType 等常量
├── adapter.py           # 适配器（翻译 → lightweight-charts）
├── CHART_MODEL_DESIGN.md    # 设计文档（v0.3 ✅）
├── CHART_MODEL_NEXT_STEPS.md# 本文件
└── tests/
    ├── test_models.py
    ├── test_builder.py
    └── test_adapter.py
```

### 实现顺序

| 步骤 | 文件 | 内容 |
|------|------|------|
| 1 | `enums.py` | SeriesType(8种) / LineStyle |
| 2 | `models.py` | Window / Chart / Series / System |
| 3 | `layout.py` | ModelLayout |
| 4 | `builder.py` | build() — 7 步（§4） |
| 5 | `__init__.py` | 统一导出 |
| 6 | `adapter.py` | Adapter.render() |
| 7 | `tests/` | 3 个测试套件 |

---

## 快速开始（伪代码）

```python
from lightweight_charts.chart_model import System, Window, Chart, Series

sys = System(
    windows=[
        Window(name="main", display_name="主窗口", tile=(2, 1)),  # 2行1列
    ],
    charts=[
        Chart(name="price", display_name="价格", window="main",
              tile_index=0, precision=2, set_period=3600),
        Chart(name="indicator", display_name="指标", window="main",
              tile_index=1, precision=4),
    ],
    series=[
        # 主K线
        Series(name="candle", display_name="K线", chart="price",
               pane=0, type="candle", data=candle_df),
        # SMA 均线
        Series(name="sma20", display_name="SMA20", chart="price",
               pane=0, type="line", data=sma_df, color="#FF9800", group="MA"),
        # 成交量
        Series(name="vol", display_name="成交量", chart="price",
               pane=1, type="volume", data=vol_df),
        # RSI 指标（独立 Chart）
        Series(name="rsi", display_name="RSI", chart="indicator",
               pane=0, type="line", data=rsi_df, color="#9C27B0"),
    ],
)

layout = sys.build()
# render_chart = Adapter.render(layout)
```

---

## 后续版本待恢复

| 实体 | 版本 | 说明 |
|------|------|------|
| Marker | v0.4+ | 标记点，优先恢复 |
| Drawing | v0.5+ | 6 种绘图 |
| PriceLine | v0.5+ | 价格线 |
| TopBar / Table | v0.6+ | UI 组件 |
| 动态更新 | v0.6+ | 场景B |
| 序列化 | v0.7+ | JSON/YAML |

> v0.2 完整设计（含上述实体的 dataclass 定义）见 git 历史。

---

*v0.3：最小可用版本，2026-07-03*
