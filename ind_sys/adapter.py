"""ind_sys 适配器 — 将 SystemLayout 翻译为 lightweight-charts 渲染实例"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import SystemLayout, Series, Chart
    from .models import parse_interval, Chart


# ═══════════════════════════════════════════════════════════════
#  Series → 工厂方法参数
# ═══════════════════════════════════════════════════════════════

# 支持 price_scale_id 参数的工厂方法（histogram 不支持）
_SUPPORTS_PRICE_SCALE_ID = {"line", "candle", "area", "ohlc_bar", "baseline"}


def _series_kwargs(s: 'Series') -> dict:
    """根据 Series.type 生成对应 create_*() 工厂方法的参数"""
    common = dict(
        name=s.display_name,
        price_line=s.price_line,
        price_label=s.price_label,
        pane_index=s.pane,
    )
    # price_scale_id 只在支持它的工厂方法中传递
    if s.type in _SUPPORTS_PRICE_SCALE_ID and s.price_scale_id is not None:
        common['price_scale_id'] = s.price_scale_id
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

        - 如果 System 中只有一个 Window → 返回单个 Chart
        - 如果有多个 Window → 返回 tuple[Chart, ...]
        """
        from lightweight_charts import Chart as RenderChart
        from .models import parse_interval

        if not layout.windows:
            raise ValueError("System 中没有 Window")

        sys_obj = layout._system
        result = []

        for wi, window in enumerate(layout.windows):
            charts = layout.charts_of(window.name)
            if not charts:
                continue

            primary_chart_name = layout.primary_charts.get(window.name, charts[0].name)
            primary_chart = next(c for c in charts if c.name == primary_chart_name)

            # 窗口偏移，避免多个窗口完全重叠
            wx, wy = 20 * wi, 20 * wi

            # ── 创建主图（每个 Window 独立窗口）──
            chart = RenderChart(
                width=width, height=height,
                x=wx, y=wy,
                title=window.display_name,
                position=primary_chart.position,
                sync_id=primary_chart.sync_id,
            )
            chart.legend(visible=True)
            chart.set_period(parse_interval(primary_chart.interval))
            chart.price_scale(price_format={'type': 'price',
                                            'precision': primary_chart.precision})
            if primary_chart.xy is not None:
                x, y = primary_chart.xy
                chart.set_position(x, y, primary_chart.width, primary_chart.height)

            # ── 主图的 Series ──
            _render_series(chart, layout, primary_chart_name, sys_obj)

            # ── 子图 ──
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
                sub.price_scale(price_format={'type': 'price',
                                              'precision': c.precision})
                if c.xy is not None:
                    x, y = c.xy
                    sub.set_position(x, y, c.width, c.height)
                _render_series(sub, layout, c.name, sys_obj)

            result.append(chart)

        # 激活同步（live 模式下，同步线程检测到就绪后开始工作）
        if sys_obj is not None:
            sys_obj._render_ready = True

        if len(result) == 1:
            return result[0]
        return tuple(result)


def _apply_markers(series_obj, layout: 'SystemLayout', series_name: str):
    """将 ind_sys markers 应用到主库 series 上"""
    markers = layout.get_markers(series_name)
    for m in markers:
        m_clean = {k: v for k, v in m.items() if v is not None}
        series_obj.add_marker(**m_clean)


def _create_series_on_chart(chart, s, layout):
    """在 chart 上创建一个额外 series（非主序列）并设置数据。"""
    factory = _FACTORY[s.type]
    kwargs = _series_kwargs(s)
    method = getattr(chart, factory)
    series_obj = method(**kwargs)
    series_obj.set(layout.get_data(s.name))
    return series_obj


def _render_series(chart, layout: 'SystemLayout', chart_name: str, sys_obj=None):
    """在主库 chart 上渲染 ind_sys Series。

    使用 ``_main_mapping`` 决定主序列映射：
      - 映射为 'candle' → chart.candle.set()
      - 映射为 'volume' → chart.volume.set()
      - 映射为 'oi'     → chart.oi.set()
      - 未映射的        → create_*() 工厂方法
    """
    series_list = layout.series_of(chart_name)
    main_map = getattr(layout._system, '_main_mapping', {})

    for s in series_list:
        data = layout.get_data(s.name)
        if data is None:
            continue

        main_key = main_map.get(s.name)
        if main_key == 'candle':
            chart.candle.set(data)
            series_obj = chart.candle
        elif main_key == 'volume':
            chart.volume.set(data)
            series_obj = chart.volume
        elif main_key == 'oi':
            chart.oi.set(data)
            series_obj = chart.oi
        else:
            series_obj = _create_series_on_chart(chart, s, layout)

        if sys_obj is not None:
            sys_obj._series_map[s.name] = series_obj

    # 应用 markers
    for s in series_list:
        markers = layout.get_markers(s.name)
        if markers:
            series_obj = sys_obj._series_map.get(s.name) if sys_obj else None
            if series_obj is not None:
                _apply_markers(series_obj, layout, s.name)