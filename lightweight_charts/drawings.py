import json
import inspect
from typing import Union, Optional, TYPE_CHECKING

from .util import NUM, Pane, as_enum, LINE_STYLE, TIME, js_json, jbool


if TYPE_CHECKING:
    from .abstract import AbstractChart
    from .drawing_series import DrawingSeries


def make_js_point(chart, time, price):
    """构造一个包含 time/logical/price 的 JS 点对象字符串。"""
    formatted_time = chart._single_datetime_format(time)
    return f'''{{
        "time": {formatted_time},
        "logical": {chart.id}.chart.timeScale()
                    .coordinateToLogical(
                        {chart.id}.chart.timeScale()
                        .timeToCoordinate({formatted_time})
                    ),
        "price": {price}
    }}'''


class Drawing(Pane):
    """绘图基类，所有绘制图形（线、框、射线等）的父类。"""
    def __init__(self, drawing_series: 'DrawingSeries', func=None):
        """
        :param drawing_series: 所属的 DrawingSeries 实例
        :param func: 交互回调函数
        """
        super().__init__(drawing_series.win)
        self.drawing_series = drawing_series
        drawing_series._drawings.append(self)

    @property
    def chart(self):
        """兼容旧代码，返回所属的 AbstractChart。"""
        return self.drawing_series.chart

    def _pane_js(self):
        """返回 pane 的 JS 引用字符串：{chartId}.chart.panes()[pane_index]"""
        return f'{self.chart.id}.chart.panes()[{self.drawing_series.pane_index}]'

    def update(self, *points):
        """更新绘图的锚点坐标。
        :param points: 交替传入 time, price 对"""
        formatted_points = []
        for i in range(0, len(points), 2):
            formatted_points.append(make_js_point(self.chart, points[i], points[i + 1]))
        self.run_script(f'{self.id}.updatePoints({", ".join(formatted_points)})')

    def delete(self):
        """删除此 drawing：从 DrawingSeries 中移除 + JS detachPrimitive。"""
        if self in self.drawing_series._drawings:
            self.drawing_series._drawings.remove(self)
        pane_js = self._pane_js()
        self.run_script(f'''
            try {{
                {pane_js}.detachPrimitive({self.id});
            }} catch(e) {{}}
            delete {self.id};
        ''')

    def options(self, color='#1E80F0', style='solid', width=4):
        """设置绘图样式。"""
        self.run_script(f'''
            {self.id}.applyOptions({{
            lineColor: '{color}',
            lineStyle: {as_enum(style, LINE_STYLE)},
            width: {width},}})
        ''')


class HorizontalLine(Drawing):
    """水平线绘图，支持拖拽回调。"""
    def __init__(self, drawing_series: 'DrawingSeries', price, color, width, style, text, axis_label_visible, func):
        super().__init__(drawing_series, func)
        self.price = price
        pane_js = self._pane_js()
        self.run_script(f'''
            {self.id} = new Lib.HorizontalLine(
                {pane_js},
                {{price: {price}}},
                {{
                    lineColor: '{color}',
                    lineStyle: {as_enum(style, LINE_STYLE)},
                    width: {width},
                    text: `{text}`,
                }},
                callbackName={f"'{self.id}'" if func else 'null'}
            )
            {pane_js}.attachPrimitive({self.id})
        ''')
        if not func:
            return

        chart = self.chart
        def wrapper(p):
            self.price = float(p)
            func(chart, self)

        async def wrapper_async(p):
            self.price = float(p)
            await func(chart, self)

        self.win.handlers[self.id] = wrapper_async if inspect.iscoroutinefunction(func) else wrapper

    def update(self, price: float):
        """Moves the horizontal line to the given price."""
        self.run_script(f'{self.id}.updatePoints({{price: {price}}})')
        self.price = price

    def options(self, color='#1E80F0', style='solid', width=4, text=''):
        super().options(color, style, width)
        self.run_script(f'{self.id}.applyOptions({{text: `{text}`}})')


class VerticalLine(Drawing):
    """垂直线绘图。"""
    def __init__(self, drawing_series: 'DrawingSeries', time, color, width, style, text, func=None):
        super().__init__(drawing_series, func)
        self.time = time
        pane_js = self._pane_js()
        self.run_script(f'''
            {self.id} = new Lib.VerticalLine(
                {pane_js},
                {{time: {self.chart._single_datetime_format(time)}}},
                {{
                    lineColor: '{color}',
                    lineStyle: {as_enum(style, LINE_STYLE)},
                    width: {width},
                    text: `{text}`,
                }},
                callbackName={f"'{self.id}'" if func else 'null'}
            )
            {pane_js}.attachPrimitive({self.id})
        ''')

    def update(self, time: TIME):
        """更新垂直线的时间位置。"""
        self.run_script(f'{self.id}.updatePoints({{time: {time}}})')
        self.time = time

    def options(self, color='#1E80F0', style='solid', width=4, text=''):
        """设置垂直线样式。"""
        super().options(color, style, width)
        self.run_script(f'{self.id}.applyOptions({{text: `{text}`}})')


class RayLine(Drawing):
    """射线绘图，从起点延伸至无穷远。"""
    def __init__(self,
        drawing_series: 'DrawingSeries',
        start_time: TIME,
        value: NUM,
        round: bool = False,
        color: str = '#1E80F0',
        width: int = 2,
        style: LINE_STYLE = 'solid',
        text: str = '',
        func = None,
    ):
        super().__init__(drawing_series, func)
        pane_js = self._pane_js()
        self.run_script(f'''
            {self.id} = new Lib.RayLine(
                {pane_js},
                {{time: {self.chart._single_datetime_format(start_time)}, price: {value}}},
                {{
                    lineColor: '{color}',
                    lineStyle: {as_enum(style, LINE_STYLE)},
                    width: {width},
                    text: `{text}`,
                }},
                callbackName={f"'{self.id}'" if func else 'null'}
            )
            {pane_js}.attachPrimitive({self.id})
        ''')


class TwoPointDrawing(Drawing):
    """两点绘图基类，用于趋势线、方框等需要两个锚点的图形。"""
    def __init__(
        self,
        drawing_type,
        drawing_series: 'DrawingSeries',
        start_time: TIME,
        start_value: NUM,
        end_time: TIME,
        end_value: NUM,
        round: bool,
        options: dict,
        func=None
    ):
        super().__init__(drawing_series, func)

        options_string = '\n'.join(f'{key}: {val},' for key, val in options.items())

        pane_js = self._pane_js()
        self.run_script(f'''
            {self.id} = new Lib.{drawing_type}(
                {pane_js},
                {make_js_point(self.chart, start_time, start_value)},
                {make_js_point(self.chart, end_time, end_value)},
                {{
                    {options_string}
                }}
            )
            {pane_js}.attachPrimitive({self.id})
        ''')


class Box(TwoPointDrawing):
    """矩形方框绘图，支持填充色。"""
    def __init__(self,
        drawing_series: 'DrawingSeries',
        start_time: TIME,
        start_value: NUM,
        end_time: TIME,
        end_value: NUM,
        round: bool,
        line_color: str,
        fill_color: str,
        width: int,
        style: LINE_STYLE,
        func=None):

        super().__init__(
            "Box",
            drawing_series,
            start_time,
            start_value,
            end_time,
            end_value,
            round,
            {
                "lineColor": f'"{line_color}"',
                "fillColor": f'"{fill_color}"',
                "width": width,
                "lineStyle": as_enum(style, LINE_STYLE)
            },
            func
        )


class TrendLine(TwoPointDrawing):
    """趋势线绘图（两点连线）。"""
    def __init__(self,
        drawing_series: 'DrawingSeries',
        start_time: TIME,
        start_value: NUM,
        end_time: TIME,
        end_value: NUM,
        round: bool,
        line_color: str,
        width: int,
        style: LINE_STYLE,
        func=None):

        super().__init__(
            "TrendLine",
            drawing_series,
            start_time,
            start_value,
            end_time,
            end_value,
            round,
            {
                "lineColor": f'"{line_color}"',
                "width": width,
                "lineStyle": as_enum(style, LINE_STYLE)
            },
            func
        )


class VerticalSpan(Pane):
    """垂直区间高亮，支持单个时间点标记或起止时间段。"""
    def __init__(self, chart: 'AbstractChart', start_time: Union[TIME, tuple, list], end_time: Optional[TIME] = None,
                 color: str = 'rgba(252, 219, 3, 0.2)'):
        """
        :param chart: 绑定的图表实例
        :param start_time: 起始时间（或时间列表，用于多点标记）
        :param end_time: 结束时间（None 则为单点标记）。仅当 start_time 为单个值时可用。
        :param color: 填充颜色
        :raises ValueError: 当 start_time 为多个值且 end_time 不为 None 时
        """
        self._chart = chart
        super().__init__(self._chart.win)
        fmt = self._chart._single_datetime_format

        # 参数校验：start_time 是否为多值
        is_multi = hasattr(start_time, '__iter__') and not isinstance(start_time, (str, int, float))
        if is_multi and end_time is not None:
            raise ValueError("start_time 为多个值时，end_time 必须为 None。")

        if end_time is None:
            # Single time marker(s) — use thin bars
            if is_multi:
                data = [{'time': fmt(t), 'value': 1} for t in start_time]
            else:
                data = [{'time': fmt(start_time), 'value': 1}]

            self.run_script(f'''
                var _vs = {self._chart.id}.chart.addSeries(LightweightCharts.HistogramSeries, {{
                    color: '{color}',
                    priceFormat: {{type: 'volume'}},
                    priceScaleId: 'vs_{self.id}',
                    lastValueVisible: false,
                    priceLineVisible: false,
                }});
                _vs.priceScale().applyOptions({{scaleMargins: {{top: 0.0, bottom: 0.0}}}});
                _vs.setData({json.dumps(data)});
                {self.id} = _vs;
                0
            ''')
        else:
            # Range between two dates — use continuous fill
            data = [
                {'time': fmt(start_time), 'value': 1},
                {'time': fmt(end_time), 'value': 1},
            ]

            self.run_script(f'''
                var _vs = {self._chart.id}.chart.addSeries(LightweightCharts.AreaSeries, {{
                    topColor: '{color}',
                    bottomColor: '{color}',
                    lineColor: '{color}',
                    lineWidth: 0,
                    lastValueVisible: false,
                    priceLineVisible: false,
                    crosshairMarkerVisible: false,
                    priceScaleId: 'vs_{self.id}',
                    autoscaleInfoProvider: () => ({{priceRange: {{minValue: 0, maxValue: 1}}}}),
                }});
                _vs.priceScale().applyOptions({{scaleMargins: {{top: 0.0, bottom: 0.0}}}});
                _vs.setData({json.dumps(data)});
                {self.id} = _vs;
                0
            ''')
        self._data = data
        self._chart._get_drawing_series(0)._drawings.append(self)

    def delete(self):
        """Irreversibly deletes the vertical span."""
        ds = self._chart._get_drawing_series(0)
        if self in ds._drawings:
            ds._drawings.remove(self)
        self.run_script(f'''
            {self._chart.id}.chart.removeSeries({self.id});
            delete {self.id};
        ''')


class PriceLine(Pane):
    """A price line drawn on the series (created via create_price_line)."""

    def __init__(self, chart: 'AbstractChart', price: float, color: str,
                 style: str, width: int, price_label: bool, title: str):
        super().__init__(chart.win)
        self._chart = chart
        chart._price_lines.append(self)
        self.run_script(f'''
            {self.id} = {self._chart.id}.series.createPriceLine(
                {{
                    price: {price},
                    color: '{color}',
                    lineStyle: {as_enum(style, LINE_STYLE)},
                    lineWidth: {width},
                    axisLabelVisible: {jbool(price_label)},
                    title: '{title}',
                }},
            );0
        ''')

    def delete(self):
        """Removes the price line from the series."""
        self._chart._price_lines.remove(self) if self in self._chart._price_lines else None
        self.run_script(f'''
            {self._chart.id}.series.removePriceLine({self.id});
            delete {self.id};
        ''')

    def update(self, price: Optional[float] = None, color: Optional[str] = None,
               style: Optional[str] = None, width: Optional[int] = None,
               title: Optional[str] = None):
        """Updates the price line options."""
        opts = {}
        if price is not None:
            opts['price'] = price
        if color is not None:
            opts['color'] = color
        if style is not None:
            opts['lineStyle'] = as_enum(style, LINE_STYLE)
        if width is not None:
            opts['lineWidth'] = width
        if title is not None:
            opts['title'] = title
        if not opts:
            return
        self.run_script(f'{self.id}.applyOptions({js_json(opts)})')
