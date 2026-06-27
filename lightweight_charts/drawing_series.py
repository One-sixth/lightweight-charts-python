"""DrawingSeries — 管理单个 pane 的所有 drawing 对象。

Pane Primitive 模式下，DrawingSeries 不再创建 JS LineSeries。
drawing 直接通过 pane.attachPrimitive() 附着到 pane 上。
DrawingSeries 仅作为 Python 侧的 per-pane drawing 管理器。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .util import Pane

if TYPE_CHECKING:
    from .abstract import AbstractChart


class DrawingSeries(Pane):
    """管理单个 pane 的所有 drawing 对象。继承 Pane，自动获得 self.id。

    不创建 JS series，不使用 attachPrimitive。
    仅负责：跟踪 pane_index、维护 _drawings 列表、提供工厂方法。
    """

    def __init__(self, chart: AbstractChart, pane_index: int = 0):
        super().__init__(chart.win)
        self.chart = chart
        self.pane_index = pane_index
        self._drawings: list = []

    # ── 工厂方法 ──

    def horizontal_line(self, price, color='rgb(122, 146, 202)', width=2,
                        style='solid', text='', axis_label_visible=True, func=None):
        """创建水平线。"""
        from .drawings import HorizontalLine
        return HorizontalLine(self, price, color, width, style, text, axis_label_visible, func)

    def trend_line(self, start_time, start_value, end_time, end_value,
                   round=False, line_color='#1E80F0', width=2, style='solid'):
        """创建趋势线。"""
        from .drawings import TrendLine
        return TrendLine(self, start_time, start_value, end_time, end_value, round, line_color, width, style)

    def ray_line(self, start_time, value, round=False, color='#1E80F0', width=2, style='solid', text=''):
        """创建射线。"""
        from .drawings import RayLine
        return RayLine(self, start_time, value, round, color, width, style, text)

    def vertical_line(self, time, color='#1E80F0', width=2, style='solid', text=''):
        """创建垂直线。"""
        from .drawings import VerticalLine
        return VerticalLine(self, time, color, width, style, text)

    def box(self, start_time, start_value, end_time, end_value,
            round=False, color='#1E80F0', fill_color='rgba(255, 255, 255, 0.2)', width=2, style='solid'):
        """创建矩形方框。"""
        from .drawings import Box
        return Box(self, start_time, start_value, end_time, end_value, round, color, fill_color, width, style)

    # ── 管理方法 ──

    def delete(self):
        """删除此 DrawingSeries：逐个删除所有 drawing。"""
        for d in list(self._drawings):
            d.delete()
        self._drawings.clear()

    def clear(self):
        """清空此 pane 的所有 drawing（不删除 DrawingSeries 自身）。"""
        for d in list(self._drawings):
            d.delete()
        self._drawings.clear()
