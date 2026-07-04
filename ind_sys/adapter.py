"""ind_sys 适配器 — 将 SystemLayout 翻译为 lightweight-charts 渲染实例"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import SystemLayout, Series, Chart
    from .models import parse_interval, Chart


# ═══════════════════════════════════════════════════════════════
#  Series → 工厂方法参数
# ═══════════════════════════════════════════════════════════════

def _series_kwargs(s: 'Series') -> dict:
    """根据 Series.type 生成对应 create_*() 工厂方法的参数"""
    common = dict(
        name=s.display_name,
        price_scale_id=s.price_scale_id,
        price_line=s.price_line,
        price_label=s.price_label,
        pane_index=s.pane,
    )
    t = s.type
    if t == "line":
        return {**common, "color": s.color, "width": s.line_width,
                "style": s.line_style, "legend": s.legend, "group": s.group}
    if t == "area":
        return {**common, "color": s.color, "style": s.line_style,
                "width": s.line_width, "top_color": s.top_color,
                "bottom_color": s.bottom_color,
                "relative_gradient": s.relative_gradient,
                "invert_filled_area": s.invert_filled_area}
    if t == "baseline":
        return {**common, "base_value": s.base_value,
                "top_fill_color1": s.top_fill_color1,
                "top_fill_color2": s.top_fill_color2,
                "top_line_color": s.top_line_color,
                "bottom_fill_color1": s.bottom_fill_color1,
                "bottom_fill_color2": s.bottom_fill_color2,
                "bottom_line_color": s.bottom_line_color,
                "line_width": s.line_width,
                "line_style": s.line_style,
                "relative_gradient": s.relative_gradient}
    if t == "histogram":
        return {**common, "color": s.color,
                "scale_margin_top": s.scale_margin_top,
                "scale_margin_bottom": s.scale_margin_bottom,
                "legend": s.legend, "group": s.group}
    if t == "candle":
        return {**common, "up_color": s.up_color, "down_color": s.down_color,
                "border_visible": s.border_visible,
                "wick_visible": s.wick_visible,
                "crosshair_marker": s.crosshair_marker}
    if t == "ohlc_bar":
        return {**common, "up_color": s.up_color, "down_color": s.down_color,
                "open_visible": s.open_visible, "thin_bars": s.thin_bars}
    raise ValueError(f"不支持的 Series type: '{t}'")


# 工厂方法名映射
_FACTORY = {
    "line":      "create_line",
    "area":      "create_area_series",
    "baseline":  "create_baseline_series",
    "histogram": "create_histogram",
    "candle":    "create_candle_series",
    "ohlc_bar":  "create_ohlc_bar_series",
}


# ═══════════════════════════════════════════════════════════════
#  Adapter
# ═══════════════════════════════════════════════════════════════

class Adapter:
    """将 SystemLayout 翻译为 lightweight-charts 渲染实例。"""

    @staticmethod
    def render(layout: 'SystemLayout', width: int = 800, height: int = 600):
        """
        渲染 SystemLayout，返回主库 Chart 实例。
        当前只处理首个 Window（v0.3 最小可用）。
        """
        from lightweight_charts import Chart as RenderChart
        from .models import parse_interval

        if not layout.windows:
            raise ValueError("System 中没有 Window")

        window = layout.windows[0]
        charts = layout.charts_of(window.name)
        if not charts:
            raise ValueError(f"Window '{window.name}' 中没有 Chart")

        primary_chart_name = layout.primary_charts.get(window.name, charts[0].name)
        primary_chart = next(c for c in charts if c.name == primary_chart_name)

        # ── 1. 创建主图 ──
        chart = RenderChart(
            width=width, height=height,
            position=primary_chart.position,
            sync_id=primary_chart.sync_id,
        )
        chart.legend(visible=True)
        chart.set_period(parse_interval(primary_chart.interval))
        chart.price_scale(price_format={'type': 'price',
                                        'precision': primary_chart.precision})
        # 绝对坐标模式
        if primary_chart.xy is not None:
            x, y = primary_chart.xy
            chart.set_position(x, y, primary_chart.width, primary_chart.height)

        # ── 2. 主图的 Series ──
        sys_obj = layout._system
        _render_series(chart, layout, primary_chart_name, sys_obj)

        # ── 3. 子图 ──
        for c in charts:
            if c.name == primary_chart_name:
                continue
            sub = chart.create_subchart(
                position=c.position,
                width=c.width, height=c.height,
                sync_id=c.sync_id,
            )
            sub.legend(visible=True)
            sub.set_period(parse_interval(c.interval))
            sub.price_scale(price_format={'type': 'price', 'precision': c.precision})
            if c.xy is not None:
                x, y = c.xy
                sub.set_position(x, y, c.width, c.height)
            _render_series(sub, layout, c.name, sys_obj)

        # ── 4. 激活同步（live 模式下，同步线程检测到 chart 后开始工作）──
        if sys_obj is not None:
            sys_obj._render_chart = chart

        return chart


def _apply_markers(series_obj, layout: 'SystemLayout', series_name: str):
    """将 ind_sys markers 应用到主库 series 上"""
    markers = layout.get_markers(series_name)
    for m in markers:
        m_clean = {k: v for k, v in m.items() if v is not None}
        series_obj.add_marker(**m_clean)


def _render_series(chart, layout: 'SystemLayout', chart_name: str, sys_obj=None):
    """在主库 chart 上渲染 ind_sys Series 列表。"""
    series_list = layout.series_of(chart_name)
    primary_s = layout.primary_series.get(chart_name)

    for s in series_list:
        df = layout.get_data(s.name)
        if df is None or df.empty:
            continue

        # 主K线 → chart.set()
        if s.name == primary_s:
            chart.set(df)
            _apply_markers(chart, layout, s.name)
            if sys_obj is not None:
                sys_obj._series_map[s.name] = chart
                sys_obj._sync_state[s.name] = len(df)
                sys_obj._sync_last_marker_counts[s.name] = len(sys_obj._markers.get(s.name, []))
            continue

        # volume → chart.volume
        if s.type == "volume":
            chart.volume.set(df)
            _apply_markers(chart.volume, layout, s.name)
            if sys_obj is not None:
                sys_obj._series_map[s.name] = chart.volume
                sys_obj._sync_state[s.name] = len(df)
                sys_obj._sync_last_marker_counts[s.name] = len(sys_obj._markers.get(s.name, []))
            continue

        # open_interest → chart.oi
        if s.type == "open_interest":
            chart.oi.set(df)
            _apply_markers(chart.oi, layout, s.name)
            if sys_obj is not None:
                sys_obj._series_map[s.name] = chart.oi
                sys_obj._sync_state[s.name] = len(df)
                sys_obj._sync_last_marker_counts[s.name] = len(sys_obj._markers.get(s.name, []))
            continue

        # 其他 → create_*() 工厂方法
        method_name = _FACTORY.get(s.type)
        if method_name is None:
            raise ValueError(f"不支持的 Series type: '{s.type}'")

        factory = getattr(chart, method_name)
        kwargs = _series_kwargs(s)
        created = factory(**kwargs)
        created.set(df)
        _apply_markers(created, layout, s.name)
        if sys_obj is not None:
            sys_obj._series_map[s.name] = created
            sys_obj._sync_state[s.name] = len(df)
            sys_obj._sync_last_marker_counts[s.name] = len(sys_obj._markers.get(s.name, []))

        if not s.visible:
            created._apply_options({'visible': False})
