"""chart_model 核心数据模型 — Window / Chart / Series / Model + SystemLayout"""
from __future__ import annotations

from collections import defaultdict
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
#  DrawingData — drawing 纯数据表示（内部使用）
# ═══════════════════════════════════════════════════════════════

@dataclass
class DrawingData:
    """drawing 的纯数据表示（内部使用，不可变语义）"""
    name: str
    chart: str
    type: str              # horizontal_line / trend_line / ray_line / vertical_line / box
    pane: int = 0

    # ── 几何参数（各 type 按需使用） ──
    price: Optional[float] = None                    # HorizontalLine
    time: Optional[Union[int, str, float]] = None    # VerticalLine
    start_time: Optional[Union[int, str, float]] = None   # TrendLine / RayLine / Box
    end_time: Optional[Union[int, str, float]] = None     # TrendLine / Box
    start_price: Optional[float] = None              # TrendLine / Box
    end_price: Optional[float] = None                # TrendLine / Box
    value: Optional[float] = None                    # RayLine
    round: bool = False                              # TrendLine / RayLine / Box

    # ── 样式 ──
    color: str = "#1E80F0"
    fill_color: str = "rgba(255, 255, 255, 0.2)"    # Box 专用
    width: int = 2
    style: str = "solid"      # solid / dotted / dashed / large_dashed / sparse_dotted
    text: str = ""
    axis_label_visible: bool = True                  # HorizontalLine 专用


# 各 type 的完整参数 schema（必选 + 可选）
_DRAWING_SCHEMA = {
    "horizontal_line": {
        "required": ["price"],
        "optional": ["color", "width", "style", "text", "axis_label_visible"],
    },
    "vertical_line": {
        "required": ["time"],
        "optional": ["color", "width", "style", "text"],
    },
    "trend_line": {
        "required": ["start_time", "start_price", "end_time", "end_price"],
        "optional": ["color", "width", "style", "round"],
    },
    "ray_line": {
        "required": ["start_time", "value"],
        "optional": ["color", "width", "style", "text", "round"],
    },
    "box": {
        "required": ["start_time", "start_price", "end_time", "end_price"],
        "optional": ["color", "fill_color", "width", "style", "round"],
    },
}

# 所有合法参数名（用于校验未知参数）
_DRAWING_ALL_PARAMS = set()
for _schema in _DRAWING_SCHEMA.values():
    _DRAWING_ALL_PARAMS.update(_schema["required"])
    _DRAWING_ALL_PARAMS.update(_schema["optional"])


def _drawing_type_help(type_name: str) -> str:
    """返回某个 drawing type 的参数提示文本"""
    schema = _DRAWING_SCHEMA.get(type_name)
    if schema is None:
        return ""
    req = ", ".join(schema["required"])
    opt = ", ".join(schema["optional"])
    return (f"  {type_name} 支持以下参数:\n"
            f"    必选: {req}\n"
            f"    可选: {opt}")


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
    _main_mapping: dict[str, str] = field(default_factory=dict, repr=False)  # series_name → 'candle'|'volume'|'oi'
    _data: dict = field(default_factory=dict, repr=False)  # series_name → DataFrame
    _markers: dict = field(default_factory=dict, repr=False)  # series_name → [marker dict]
    drawings: list[DrawingData] = field(default_factory=list, repr=False)  # 🆕 drawing 列表
    _system: object = None  # Model 引用（build 时设置，适配器用）

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

    def drawings_of(self, chart_name: str) -> list[DrawingData]:
        """返回某 Chart 下的全部 Drawing"""
        return [d for d in self.drawings if d.chart == chart_name]


# ═══════════════════════════════════════════════════════════════
#  Model — 根容器
# ═══════════════════════════════════════════════════════════════

@dataclass
class Model:
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
    _render_ready: bool = False          # 渲染就绪标志（Adapter.render 设置）
    _series_map: dict = field(default_factory=dict, repr=False)  # series_name → 主库 series 对象
    _series_locks: dict = field(default_factory=lambda: defaultdict(threading.Lock), repr=False)  # series_name → Lock
    _sync_thread: object = None
    _stop_event: object = None

    # ── Drawing（通过 sys_obj.drawing 管理） ──
    _drawings: dict = field(default_factory=dict, repr=False)           # name → DrawingData
    _drawing_version: int = 0                                           # 版本号，增删时 +1
    _render_drawings: dict = field(default_factory=dict, repr=False)    # name → 渲染层 drawing 对象
    _sync_last_drawing_version: int = 0                                 # 上次同步的 drawing 版本
    _chart_map: dict = field(default_factory=dict, repr=False)          # chart_name → 主库 chart 对象

    @property
    def drawing(self) -> 'DrawingManager':
        """返回 DrawingManager 访问器。"""
        return DrawingManager(self)

    def _mark_drawing_change(self) -> None:
        """标记 drawing 发生了变更（add / del 时调用）"""
        self._drawing_version += 1

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
        """追加 bar 数据（replace-or-append 模式：仅替换已有数据最后一条，不影响之前的 bar）"""
        self._assert_series(series_name)
        existing = self._data.get(series_name)
        if existing is None or existing.empty:
            self._data[series_name] = df.copy()
        else:
            if existing['time'].iloc[-1] == df['time'].iloc[0]:
                # 新数据首条时间 == 已有最后一条时间 → 替换最后一条，追加其余
                self._data[series_name] = pd.concat(
                    [existing.iloc[:-1], df], ignore_index=True
                )
            else:
                # 纯追加
                self._data[series_name] = pd.concat(
                    [existing, df], ignore_index=True
                )
        old_v = self._series_versions.get(series_name, 0)
        self._series_versions[series_name] = old_v + 1

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

        # 9. 主序列映射：每 chart 内首个 candle/volume/open_interest → chart.candle/volume/oi
        main_mapping: dict[str, str] = {}
        for chart_name, s_list in chart_series.items():
            seen = set()
            for s in s_list:
                if s.type in ('candle', 'volume', 'open_interest') and s.type not in seen:
                    key = {'candle': 'candle', 'volume': 'volume', 'open_interest': 'oi'}[s.type]
                    main_mapping[s.name] = key
                    seen.add(s.type)

        self._main_mapping = main_mapping

        layout = SystemLayout(
            windows=self.windows,
            charts=self.charts,
            series=self.series,
            pane_info=pane_info,
            window_charts=window_charts,
            chart_series=chart_series,
            primary_charts=primary_charts,
            _data=self._data,
            _markers=self._markers,
            drawings=list(self._drawings.values()),
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
            if self._render_ready:
                try:
                    self._do_sync()
                except Exception as e:
                    import traceback
                    print(f'[sync] EXCEPTION: {e}')
                    traceback.print_exc()
            self._stop_event.wait(0.1)

    def _do_sync(self):
        """比较每个 series 的版本号，有变化的同步数据和 markers"""
        for s in self.series:
            name = s.name
            cur = self._series_versions.get(name, 0)
            last = self._sync_last_versions.get(name, 0)
            if cur == last:
                continue  # 此 series 无变化

            # 获取 series 的互斥锁，保护推送渲染层的原子性
            lock = self._series_locks[name]
            with lock:
                series_obj = self._series_map.get(name)
                if series_obj is None:
                    # 未渲染的 series（如 Window 2），直接标记已同步
                    self._sync_last_versions[name] = cur
                    continue

                # ── 同步数据 ──
                df = self._data.get(name)
                if df is not None and not df.empty:
                    last_rows = self._sync_state.get(name, 0)
                    curr_rows = len(df)
                    if curr_rows > last_rows:
                        series_obj.update_bars(df.iloc[last_rows:])
                    elif curr_rows < last_rows:
                        series_obj.set(df)
                    else:
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

        # ── 同步 drawings（增量 diff） ──
        drawing_ver = self._drawing_version
        if drawing_ver != self._sync_last_drawing_version:
            current = set(self._drawings.keys())
            rendered = set(self._render_drawings.keys())

            # 🆕 新增：数据层有，渲染层还没有
            for name in current - rendered:
                d = self._drawings[name]
                chart_obj = self._chart_map.get(d.chart)
                if chart_obj is None:
                    # chart 未就绪（可能是另一个 Window），跳过
                    continue
                if not hasattr(chart_obj, '_drawing_series'):
                    continue  # 不支持的 chart 类型
                ds = chart_obj._get_drawing_series(d.pane)
                from .adapter import _DRAWING_FACTORY, _drawing_to_kwargs
                method = getattr(ds, _DRAWING_FACTORY[d.type])
                obj = method(**_drawing_to_kwargs(d))
                self._render_drawings[name] = obj

            # 🗑️ 删除：渲染层有，数据层已移除
            for name in rendered - current:
                obj = self._render_drawings.pop(name)
                try:
                    obj.delete()
                except Exception:
                    pass  # 容错：JS 层面可能已清理

            self._sync_last_drawing_version = drawing_ver

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

    def __init__(self, system: Model, series_name: str):
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


# ═══════════════════════════════════════════════════════════════
#  DrawingManager — sys_obj.drawing 访问器
# ═══════════════════════════════════════════════════════════════

class DrawingManager:
    """通过 sys_obj.drawing 访问，提供 drawing 增删操作。

    用法:
        sys_obj.drawing.add('支撑位', chart='price', pane=0,
                             type='horizontal_line', price=5000, color='#FF0000')
        sys_obj.drawing.delete('支撑位')
        del sys_obj.drawing['支撑位']
        'name' in sys_obj.drawing
        len(sys_obj.drawing)
        sys_obj.drawing.names
    """

    def __init__(self, system: 'Model'):
        self._sys = system

    def add(self, name: str, chart: str, type: str,
            pane: int = 0, **params) -> None:
        """添加一个 drawing。

        必要参数由 type 决定：
          horizontal_line → price
          vertical_line   → time
          trend_line      → start_time, start_price, end_time, end_price
          ray_line        → start_time, value
          box             → start_time, start_price, end_time, end_price

        可选样式参数：color, fill_color, width, style, text, axis_label_visible, round
        """
        # 1. 校验 type 是否有效
        schema = _DRAWING_SCHEMA.get(type)
        if schema is None:
            types_list = "\n".join(
                f"  {t}" for t in _DRAWING_SCHEMA)
            raise ValueError(
                f"不支持的 Drawing type: '{type}'。\n"
                f"支持的 type:\n{types_list}\n"
                f"使用 sys_obj.drawing.help('{type}') 查看参数详情")

        # 2. 校验 name 唯一
        if name in self._sys._drawings:
            raise ValueError(f"Drawing name 重复: '{name}'")

        # 3. 校验 chart 存在
        chart_names = {c.name for c in self._sys.charts}
        if chart not in chart_names:
            raise ValueError(f"Chart '{chart}' 不存在，可用: {sorted(chart_names)}")

        # 4. 校验必选参数
        required = schema["required"]
        missing = [f for f in required if f not in params]
        if missing:
            raise ValueError(
                f"Drawing '{name}' type='{type}' 缺少必选参数: {missing}\n"
                f"{_drawing_type_help(type)}")

        # 5. 校验无未知字段
        all_valid = _DRAWING_ALL_PARAMS
        unknown = set(params) - all_valid
        if unknown:
            raise ValueError(
                f"Drawing '{name}' 中有未知参数: {unknown}\n"
                f"{_drawing_type_help(type)}")

        # 6. 构建 DrawingData
        kwargs = {k: params.get(k, getattr(DrawingData, k))
                  for k in all_valid}
        data = DrawingData(
            name=name, chart=chart, type=type, pane=pane, **kwargs)
        self._sys._drawings[name] = data
        self._sys._mark_drawing_change()

    def _del(self, name: str) -> None:
        """内部删除方法"""
        if name not in self._sys._drawings:
            raise KeyError(f"Drawing '{name}' 不存在")
        del self._sys._drawings[name]
        self._sys._mark_drawing_change()

    def delete(self, name: str) -> None:
        """删除指定名称的 drawing。"""
        self._del(name)

    def __delitem__(self, name: str) -> None:
        """del sys_obj.drawing['name']"""
        self._del(name)

    def __contains__(self, name: str) -> bool:
        return name in self._sys._drawings

    def __len__(self) -> int:
        return len(self._sys._drawings)

    @property
    def names(self) -> list[str]:
        return sorted(self._sys._drawings.keys())

    @staticmethod
    def help(type_name: str) -> str:
        """查看某个 drawing type 的参数说明。

        用法:
            print(sys_obj.drawing.help('trend_line'))
            print(DrawingManager.help('horizontal_line'))
        """
        help_text = _drawing_type_help(type_name)
        if not help_text:
            types_list = "\n".join(
                f"  {t}" for t in _DRAWING_SCHEMA)
            return (f"不支持的 type: '{type_name}'。支持的 type:\n"
                    f"{types_list}")
        return help_text
