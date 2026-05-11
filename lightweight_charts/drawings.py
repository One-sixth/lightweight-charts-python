import asyncio
import json
import pandas as pd
import inspect

from typing import Union, Optional

from .util import NUM, Pane, as_enum, LINE_STYLE, TIME, snake_to_camel, js_json

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
    def __init__(self, chart, func=None):
        """
        :param chart: 绑定的图表实例
        :param func: 交互回调函数
        """
        super().__init__(chart.win)
        self.chart = chart
        chart._drawings.append(self)

    def update(self, *points):
        """更新绘图的锚点坐标。
        :param points: 交替传入 time, price 对"""
        formatted_points = []
        for i in range(0, len(points), 2):
            formatted_points.append(make_js_point(self.chart, points[i], points[i + 1]))
        self.run_script(f'{self.id}.updatePoints({", ".join(formatted_points)})')
        print(f'{self.id}.updatePoints({", ".join(formatted_points)})')

    def delete(self):
        """
        Irreversibly deletes the drawing.
        """
        if self in self.chart._drawings:
            self.chart._drawings.remove(self)
        self.run_script(f'''
            {self.id}.detach()
            delete {self.id}
        ''')

    def options(self, color='#1E80F0', style='solid', width=4):
        """设置绘图样式。
        :param color: 线条颜色
        :param style: 线条样式（solid/dotted/dashed 等）
        :param width: 线宽"""
        self.run_script(f'''{self.id}.applyOptions({{
            lineColor: '{color}',
            lineStyle: {as_enum(style, LINE_STYLE)},
            width: {width},
        }})''')

class TwoPointDrawing(Drawing):
    """两点绘图基类，用于趋势线、方框等需要两个锚点的图形。"""
    def __init__(
        self,
        drawing_type,
        chart,
        start_time: TIME,
        start_value: NUM,
        end_time: TIME,
        end_value: NUM,
        round: bool,
        options: dict,
        func=None
    ):
        super().__init__(chart, func)

        options_string = '\n'.join(f'{key}: {val},' for key, val in options.items())

        self.run_script(f'''
        {self.id} = new Lib.{drawing_type}(
            {make_js_point(self.chart, start_time, start_value)},
            {make_js_point(self.chart, end_time, end_value)},
            {{
                {options_string}
            }}
        )
        {chart.id}.series.attachPrimitive({self.id})
        ''')


class HorizontalLine(Drawing):
    """水平线绘图，支持拖拽回调。"""
    def __init__(self, chart, price, color, width, style, text, axis_label_visible, func):
        super().__init__(chart, func)
        self.price = price
        self.run_script(f'''

        {self.id} = new Lib.HorizontalLine(
            {{price: {price}}},
            {{
                lineColor: '{color}',
                lineStyle: {as_enum(style, LINE_STYLE)},
                width: {width},
                text: `{text}`,
            }},
            callbackName={f"'{self.id}'" if func else 'null'}
        )
        {chart.id}.series.attachPrimitive({self.id})
        ''')
        if not func:
            return

        def wrapper(p):
            self.price = float(p)
            func(chart, self)

        async def wrapper_async(p):
            self.price = float(p)
            await func(chart, self)

        self.win.handlers[self.id] = wrapper_async if inspect.iscoroutinefunction(func) else wrapper
        self.run_script(f'{chart.id}.toolBox?.addNewDrawing({self.id})')

    def update(self, price: float):
        """
        Moves the horizontal line to the given price.
        """
        self.run_script(f'{self.id}.updatePoints({{price: {price}}})')
        # self.run_script(f'{self.id}.updatePrice({price})')
        self.price = price

    def options(self, color='#1E80F0', style='solid', width=4, text=''):
        super().options(color, style, width)
        self.run_script(f'{self.id}.applyOptions({{text: `{text}`}})')


class VerticalLine(Drawing):
    """垂直线绘图。"""
    def __init__(self, chart, time, color, width, style, text, func=None):
        super().__init__(chart, func)
        self.time = time
        self.run_script(f'''

        {self.id} = new Lib.VerticalLine(
            {{time: {self.chart._single_datetime_format(time)}}},
            {{
                lineColor: '{color}',
                lineStyle: {as_enum(style, LINE_STYLE)},
                width: {width},
                text: `{text}`,
            }},
            callbackName={f"'{self.id}'" if func else 'null'}
        )
        {chart.id}.series.attachPrimitive({self.id})
        ''')

    def update(self, time: TIME):
        """更新垂直线的时间位置。"""
        self.run_script(f'{self.id}.updatePoints({{time: {time}}})')
        # self.run_script(f'{self.id}.updatePrice({price})')
        self.time = time

    def options(self, color='#1E80F0', style='solid', width=4, text=''):
        """设置垂直线样式。"""
        super().options(color, style, width)
        self.run_script(f'{self.id}.applyOptions({{text: `{text}`}})')


class RayLine(Drawing):
    """射线绘图，从起点延伸至无穷远。"""
    def __init__(self,
        chart,
        start_time: TIME,
        value: NUM,
        round: bool = False,
        color: str = '#1E80F0',
        width: int = 2,
        style: LINE_STYLE = 'solid',
        text: str = '',
        func = None,
    ):
        super().__init__(chart, func)
        self.run_script(f'''
        {self.id} = new Lib.RayLine(
            {{time: {self.chart._single_datetime_format(start_time)}, price: {value}}},
            {{
                lineColor: '{color}',
                lineStyle: {as_enum(style, LINE_STYLE)},
                width: {width},
                text: `{text}`,
            }},
            callbackName={f"'{self.id}'" if func else 'null'}
        )
        {chart.id}.series.attachPrimitive({self.id})
        ''')


class Box(TwoPointDrawing):
    """矩形方框绘图，支持填充色。"""
    def __init__(self,
        chart,
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
            chart,
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
        chart,
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
            chart,
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
    def __init__(self, series: 'SeriesCommon', start_time: Union[TIME, tuple, list], end_time: Optional[TIME] = None,
                 color: str = 'rgba(252, 219, 3, 0.2)'):
        """
        :param series: 绑定的数据系列
        :param start_time: 起始时间（或时间列表，用于多点标记）
        :param end_time: 结束时间（None 则为单点标记）
        :param color: 填充颜色
        """
        self._chart = series._chart
        super().__init__(self._chart.win)
        start_time = pd.to_datetime(start_time).tz_localize(None)
        end_time = pd.to_datetime(end_time).tz_localize(None) if end_time else None

        if end_time is None:
            # Single time marker(s) — use thin bars
            if hasattr(start_time, '__iter__') and not isinstance(start_time, pd.Timestamp):
                data = [{'time': t.timestamp(), 'value': 1} for t in start_time]
            else:
                data = [{'time': start_time.timestamp(), 'value': 1}]
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
                {'time': start_time.timestamp(), 'value': 1},
                {'time': end_time.timestamp(), 'value': 1},
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
        self._chart._drawings.append(self)

    def delete(self):
        """
        Irreversibly deletes the vertical span.
        """
        if self in self._chart._drawings:
            self._chart._drawings.remove(self)
        self.run_script(f'''
            {self._chart.id}.chart.removeSeries({self.id})
            delete {self.id}
        ''')
