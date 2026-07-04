"""ind_sys 核心数据模型 — Window / Chart / Series / System + SystemLayout"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union
import re
import threading
import pandas as pd


# ═══════════════════════════════════════════════════════════════
#  interval 字符串解析
# ═══════════════════════════════════════════════════════════════

_INTERVAL_UNITS = {
    's': 1, 'sec': 1, 'secs': 1, 'second': 1, 'seconds': 1,
    'min': 60, 'mins': 60, 'minute': 60, 'minutes': 60,
    'h': 3600, 'hr': 3600, 'hour': 3600, 'hours': 3600,
    'd': 86400, 'day': 86400, 'days': 86400,
    'w': 604800, 'week': 604800, 'weeks': 604800,
}


def parse_interval(interval: Union[int, str]) -> int:
    """将 interval 转换为秒数。支持 int 或 str（如 '1day', '5min', '15sec'）。"""
    if isinstance(interval, (int, float)):
        return int(interval)
    s = str(interval).strip().lower()
    m = re.match(r'^(\d+)\s*([a-z]+)$', s)
    if not m:
        raise ValueError(f"无法解析 interval: '{interval}'，示例: '1day', '5min', '15sec'")
    num = int(m.group(1))
    unit = m.group(2)
    if unit not in _INTERVAL_UNITS:
        raise ValueError(f"未知的 interval 单位: '{unit}'，支持: {sorted(set(_INTERVAL_UNITS))}")
    return num * _INTERVAL_UNITS[unit]


# ═══════════════════════════════════════════════════════════════
#  类型常量
# ═══════════════════════════════════════════════════════════════

class SeriesType:
    CANDLE        = "candle"
    OHLC_BAR      = "ohlc_bar"
    LINE          = "line"
    AREA          = "area"
    BASELINE      = "baseline"
    HISTOGRAM     = "histogram"
    VOLUME        = "volume"
    OPEN_INTEREST = "open_interest"


KLINE_TYPES = {SeriesType.CANDLE, SeriesType.OHLC_BAR}


# ═══════════════════════════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════════════════════════

def _assert_unique(items: list, label: str):
    names = [x.name for x in items]
    seen = set()
    for n in names:
        if n in seen:
            raise ValueError(f"Duplicate {label} name: '{n}'")
        seen.add(n)


def _group_by(items: list, key_fn) -> dict:
    """按 key_fn 分组，返回 {key: [items]}"""
    result: dict = {}
    for item in items:
        k = key_fn(item)
        result.setdefault(k, []).append(item)
    return result


# ═══════════════════════════════════════════════════════════════
#  Window — 窗口（极简）
# ═══════════════════════════════════════════════════════════════

@dataclass
class Window:
    name: str
    display_name: str


# ═══════════════════════════════════════════════════════════════
#  Chart — 图表（精简）
# ═══════════════════════════════════════════════════════════════

@dataclass
class Chart:
    name: str
    display_name: str
    window: str                              # 所属 Window 名称引用
    interval: Union[int, str]                # 必选：时间级别（秒数或 '1day'/'5min'/'15sec'）
    precision: int = 2                       # 价格精度（小数位数）
    position: int = 111                      # 网格位置（如 221 = 2行2列第1格）
    width: float = 1.0                       # 相对于网格单元的宽度
    height: float = 1.0                      # 相对于网格单元的高度
    xy: Optional[tuple[float, float]] = None # 绝对坐标 (x, y)，设定后切换为绝对坐标模式
    sync_id: Optional[str] = None            # 同步组名


# ═══════════════════════════════════════════════════════════════
#  Series — 数据系列（全量支持，8 种类型）
# ═══════════════════════════════════════════════════════════════

@dataclass
class Series:
    name: str
    display_name: str
    chart: str                                      # 所属 Chart 名称引用
    pane: int = 0
    type: str = SeriesType.LINE

    # ── 通用 ──
    visible: bool = True
    color: str = "#2962FF"
    line_width: int = 2
    line_style: str = "solid"
    price_scale_id: Optional[str] = "right"         # left / right / None(独立)
    price_line: bool = False
    price_label: bool = True
    legend: bool = True
    group: Optional[str] = None

    # ── Candle / OHLCBar ──
    up_color: str = "rgba(39,157,130,100)"
    down_color: str = "rgba(200,97,100,100)"
    border_visible: bool = True
    wick_visible: bool = True
    crosshair_marker: bool = True

    # ── OHLCBar ──
    open_visible: bool = True
    thin_bars: bool = True

    # ── Area ──
    top_color: str = "rgba(33,150,243,0.4)"
    bottom_color: str = "rgba(33,150,243,0)"
    relative_gradient: bool = False
    invert_filled_area: bool = False

    # ── Baseline ──
    base_value: float = 0
    top_fill_color1: str = "rgba(38,166,154,0.28)"
    top_fill_color2: str = "rgba(38,166,154,0.05)"
    top_line_color: str = "rgba(38,166,154,1)"
    bottom_fill_color1: str = "rgba(239,83,80,0.05)"
    bottom_fill_color2: str = "rgba(239,83,80,0.28)"
    bottom_line_color: str = "rgba(239,83,80,1)"

    # ── Histogram ──
    scale_margin_top: float = 0.0
    scale_margin_bottom: float = 0.0


# ═══════════════════════════════════════════════════════════════
#  SystemLayout — build() 只读结果
# ═══════════════════════════════════════════════════════════════

@dataclass
class SystemLayout:
    windows: list[Window]
    charts: list[Chart]
    series: list[Series]
    pane_info: dict[str, dict[int, list[Series]]]   # chart_name → {pane → [series]}
    window_charts: dict[str, list[Chart]]            # window_name → [charts]
    chart_series: dict[str, list[Series]]            # chart_name → [series]
    primary_charts: dict[str, str]                   # window_name → 主 chart name
    primary_series: dict[str, str]                   # chart_name → 主 series name
    _data: dict = field(default_factory=dict, repr=False)  # series_name → DataFrame
    _markers: dict = field(default_factory=dict, repr=False)  # series_name → [marker dict]
    _system: object = None  # System 引用（build 时设置，适配器用）

    def series_of(self, chart_name: str) -> list[Series]:
        """返回某 Chart 下的全部 Series"""
        return self.chart_series.get(chart_name, [])

    def charts_of(self, window_name: str) -> list[Chart]:
        """返回某 Window 下的全部 Chart"""
        return self.window_charts.get(window_name, [])

    def panes_of(self, chart_name: str) -> dict[int, list[Series]]:
        """返回某 Chart 的 pane 分组"""
        return self.pane_info.get(chart_name, {})

    def get_data(self, series_name: str) -> Optional[pd.DataFrame]:
        """获取某 Series 的数据"""
        return self._data.get(series_name)

    def get_markers(self, series_name: str) -> list[dict]:
        """获取某 Series 的标记列表"""
        return self._markers.get(series_name, [])


# ═══════════════════════════════════════════════════════════════
#  System — 根容器
# ═══════════════════════════════════════════════════════════════

@dataclass
class System:
    windows: list[Window]
    charts: list[Chart]
    series: list[Series]
    _data: dict = field(default_factory=dict, repr=False)  # series_name → DataFrame
    _markers: dict = field(default_factory=dict, repr=False)  # series_name → [marker dict]
    # ── 动态同步（live 模式） ──
    _series_versions: dict = field(default_factory=dict, repr=False)  # series_name → version
    _sync_state: dict = field(default_factory=dict, repr=False)  # series_name → last synced row count
    _sync_last_versions: dict = field(default_factory=dict, repr=False)  # series_name → last synced version
    _sync_last_marker_counts: dict = field(default_factory=dict, repr=False)  # series_name → last synced marker count
    _render_chart: object = None        # 主库 chart 引用（Adapter.render 设置）
    _series_map: dict = field(default_factory=dict, repr=False)  # series_name → 主库 series 对象
    _sync_thread: object = None
    _stop_event: object = None

    def _assert_series(self, series_name: str):
        names = {s.name for s in self.series}
        if series_name not in names:
            raise ValueError(f"Series '{series_name}' 不存在")

    def __getitem__(self, series_name: str) -> 'SeriesAccessor':
        """通过 sys_obj['series_name'] 获取数据访问器"""
        self._assert_series(series_name)
        return SeriesAccessor(self, series_name)

    def set_data(self, series_name: str, df: pd.DataFrame) -> None:
        """一次性设置全量 bar 数据"""
        self._assert_series(series_name)
        self._data[series_name] = df.copy()
        self._series_versions[series_name] = self._series_versions.get(series_name, 0) + 1

    def append_data(self, series_name: str, df: pd.DataFrame) -> None:
        """追加 bar 数据（按 time 去重，保留最新）"""
        self._assert_series(series_name)
        existing = self._data.get(series_name)
        if existing is None or existing.empty:
            self._data[series_name] = df.copy()
        else:
            combined = pd.concat([existing, df])
            combined = combined.drop_duplicates(subset='time', keep='last')
            combined = combined.sort_values('time').reset_index(drop=True)
            self._data[series_name] = combined
        self._series_versions[series_name] = self._series_versions.get(series_name, 0) + 1

    def pop_data(self, series_name: str, count: int = 1) -> None:
        """从末尾移除指定数量的 bar"""
        self._assert_series(series_name)
        existing = self._data.get(series_name)
        if existing is not None and not existing.empty:
            self._data[series_name] = existing.iloc[:-count].copy()
            self._series_versions[series_name] = self._series_versions.get(series_name, 0) + 1

    def get_data(self, series_name: str) -> Optional[pd.DataFrame]:
        """获取某 Series 的数据"""
        return self._data.get(series_name)

    # ═══ 标记操作 ═══

    def _add_marker(self, series_name: str, marker: dict) -> None:
        self._assert_series(series_name)
        self._markers.setdefault(series_name, []).append(marker)
        self._series_versions[series_name] = self._series_versions.get(series_name, 0) + 1

    def get_markers(self, series_name: str) -> list[dict]:
        return self._markers.get(series_name, [])

    # ═══ 构建关系图 ═══

    def build(self, live: bool = False) -> SystemLayout:
        # 1. 名称唯一性
        _assert_unique(self.windows, "window")
        _assert_unique(self.charts, "chart")
        _assert_unique(self.series, "series")

        # 2. Window → Chart
        window_charts = _group_by(self.charts, lambda c: c.window)

        # 3. Chart → Series
        chart_series = _group_by(self.series, lambda s: s.chart)

        # 4. Chart → Pane
        pane_info: dict[str, dict[int, list[Series]]] = {}
        for chart_name, s_list in chart_series.items():
            pane_info[chart_name] = _group_by(s_list, lambda s: s.pane)

        # 5. Indicator 约束：每 pane 只能一个 K线类型
        for chart_name, panes in pane_info.items():
            for pane_num, s_list in panes.items():
                kline_count = sum(1 for s in s_list if s.type in KLINE_TYPES)
                if kline_count > 1:
                    raise ValueError(
                        f"Chart '{chart_name}' pane {pane_num} 有 {kline_count} 个 "
                        f"K线类型指标，限制为 1 个"
                    )

        # 6. 引用完整性：chart.window 必须存在
        win_names = {w.name for w in self.windows}
        for c in self.charts:
            if c.window not in win_names:
                raise ValueError(f"Chart '{c.name}' 引用了不存在的 Window '{c.window}'")

        # 7. 引用完整性：series.chart 必须存在
        chart_names = {c.name for c in self.charts}
        for s in self.series:
            if s.chart not in chart_names:
                raise ValueError(f"Series '{s.name}' 引用了不存在的 Chart '{s.chart}'")

        # 8. 主图：Window 内首个 Chart
        primary_charts: dict[str, str] = {}
        for w in self.windows:
            charts_in_win = window_charts.get(w.name, [])
            if charts_in_win:
                primary_charts[w.name] = charts_in_win[0].name

        # 9. 主 series：pane 0 首个 candle/ohlc_bar
        primary_series: dict[str, str] = {}
        for chart_name, panes in pane_info.items():
            pane0 = panes.get(0, [])
            for s in pane0:
                if s.type in KLINE_TYPES:
                    primary_series[chart_name] = s.name
                    break

        layout = SystemLayout(
            windows=self.windows,
            charts=self.charts,
            series=self.series,
            pane_info=pane_info,
            window_charts=window_charts,
            chart_series=chart_series,
            primary_charts=primary_charts,
            primary_series=primary_series,
            _data=self._data,
            _markers=self._markers,
            _system=self,
        )

        # ── live 模式：启动同步线程 ──
        if live:
            self._stop_event = threading.Event()
            self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
            self._sync_thread.start()

        return layout

    # ═══ 动态同步（live 模式）═══

    def _sync_loop(self):
        """同步线程主循环：每秒检查 series 版本号，有变化的同步到渲染层"""
        while not self._stop_event.is_set():
            if self._render_chart is not None:
                try:
                    self._do_sync()
                except Exception:
                    pass  # 容错：同步失败不影响数据层
            self._stop_event.wait(1.0)

    def _do_sync(self):
        """比较每个 series 的版本号，有变化的同步数据和 markers"""
        for s in self.series:
            name = s.name
            cur = self._series_versions.get(name, 0)
            last = self._sync_last_versions.get(name, 0)
            if cur == last:
                continue  # 此 series 无变化

            series_obj = self._series_map.get(name)
            if series_obj is None:
                continue

            # ── 同步数据 ──
            df = self._data.get(name)
            if df is not None and not df.empty:
                last_rows = self._sync_state.get(name, 0)  # 上次同步的行数
                curr_rows = len(df)
                if curr_rows > last_rows:
                    # 先更新最后一根旧 bar（数据可能被修改了）
                    if last_rows > 0:
                        series_obj.update_bar(df.iloc[last_rows - 1])
                    # 再追加新增部分
                    series_obj.update_bars(df.iloc[last_rows:])
                elif curr_rows < last_rows:
                    # 数据变少（pop/set）：全量重置
                    series_obj.set(df)
                else:
                    # 行数不变但版本变了：更新最后一个 bar
                    series_obj.update_bar(df.iloc[-1])
                self._sync_state[name] = curr_rows

            # ── 同步 markers ──
            markers = self._markers.get(name, [])
            last_mc = self._sync_last_marker_counts.get(name, 0)
            if len(markers) > last_mc:
                for m in markers[last_mc:]:
                    m_clean = {k: v for k, v in m.items() if v is not None}
                    series_obj.add_marker(**m_clean)
                self._sync_last_marker_counts[name] = len(markers)

            self._sync_last_versions[name] = cur

    def stop_sync(self):
        """停止同步线程"""
        if self._stop_event is not None:
            self._stop_event.set()
            if self._sync_thread is not None:
                self._sync_thread.join(timeout=2)
            self._stop_event = None
            self._sync_thread = None


# ═══════════════════════════════════════════════════════════════
#  SeriesAccessor — sys_obj['series_name'] 返回的数据访问器
# ═══════════════════════════════════════════════════════════════

class SeriesAccessor:
    """通过 sys_obj['series_name'] 获取，提供链式数据操作方法。

    用法：
        sys_obj['sma10'].set(df)
        sys_obj['sma10'].append(df_new)
        sys_obj['sma10'].pop(2)
        sys_obj['sma10'].add_marker(time=123, position='below', text='买入')
        sys_obj['sma10'].add_markers([{...}, {...}])
    """

    __slots__ = ('_sys', '_name')

    def __init__(self, system: System, series_name: str):
        self._sys = system
        self._name = series_name

    @property
    def name(self) -> str:
        return self._name

    # ── bar 数据操作 ──

    def set(self, df: pd.DataFrame) -> None:
        """一次性设置全量 bar 数据"""
        self._sys.set_data(self._name, df)

    def append(self, df: pd.DataFrame) -> None:
        """追加 bar 数据（按 time 去重，保留最新）"""
        self._sys.append_data(self._name, df)

    def pop(self, count: int = 1) -> None:
        """从末尾移除指定数量的 bar"""
        self._sys.pop_data(self._name, count)

    @property
    def data(self) -> Optional[pd.DataFrame]:
        """获取当前数据"""
        return self._sys.get_data(self._name)

    # ── 标记操作 ──

    def add_marker(self, time, position: str = 'below',
                   shape: str = 'arrow_up', color: str = '#2196F3',
                   text: Optional[str] = None) -> None:
        """添加单个标记"""
        self._sys._add_marker(self._name, {
            'time': time, 'position': position, 'shape': shape,
            'color': color, 'text': text,
        })

    def add_markers(self, markers: list[dict]) -> None:
        """批量添加标记，每个 marker 是 dict（含 time/position/shape/color/text）"""
        for m in markers:
            self._sys._add_marker(self._name, m)

    @property
    def markers(self) -> list[dict]:
        """获取当前标记列表"""
        return self._sys.get_markers(self._name)
