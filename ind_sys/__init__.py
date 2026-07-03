"""ind_sys — 纯数据指标系统 v0.3

声明式、扁平化、引用式的纯数据模型。与渲染层完全解耦。
"""
from __future__ import annotations

from .models import System, Window, Chart, Series, SystemLayout, SeriesType, SeriesAccessor, parse_interval
from .adapter import Adapter

__all__ = [
    'System', 'Window', 'Chart', 'Series', 'SystemLayout',
    'SeriesType', 'SeriesAccessor', 'Adapter', 'parse_interval',
]
