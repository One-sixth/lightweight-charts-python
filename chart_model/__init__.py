"""chart_model — 图表数据模型 v0.3+

声明式、扁平化、引用式的纯数据模型。与渲染层完全解耦。
支持 Drawing（5 种画线类型）动态增删 + 实时同步。
"""
from __future__ import annotations

from .models import Model, Window, Chart, Series, SystemLayout, SeriesType, SeriesAccessor, DrawingManager, parse_interval
from .adapter import Adapter

__all__ = [
    'Model', 'Window', 'Chart', 'Series', 'SystemLayout',
    'SeriesType', 'SeriesAccessor', 'DrawingManager', 'Adapter', 'parse_interval',
]
