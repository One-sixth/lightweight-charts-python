import json
import os
from base64 import b64decode
from typing import Callable, Union, Literal, Optional
import pandas as pd
import time as _time
import tomllib
import numpy as np

from .table import Table
from .toolbox import ToolBox
from .drawings import Box, HorizontalLine, RayLine, TrendLine, VerticalLine, VerticalSpan, PriceLine
from .series import SeriesCommon, LineSeries, HistogramSeries, VolumeSeries, OpenInterestSeries, CandleSeries, AreaSeries, OHLCBarSeries, BaselineSeries
from .drawing_series import DrawingSeries
from .topbar import TopBar
from .util import (
    BulkRunScript, Pane, Events, IDGen, as_enum, jbool, js_json, TIME, NUM, FLOAT,
    LINE_STYLE, MARKER_POSITION, MARKER_SHAPE, CROSSHAIR_MODE,
    PRICE_SCALE_MODE, marker_position, marker_shape, js_data,
    Position, GridPosition, parse_position,
    normal_df, merge_value_by_time, get_df_interval_offset, time_to_bar_time
)

current_dir = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(current_dir, 'js', 'index.html')
INDEX_TAB = os.path.join(current_dir, 'js', 'index_tab.html')


class Window:
    """JS 窗口桥接层，管理脚本执行队列、事件处理器和加载状态。"""
    _id_gen = IDGen()

    def __init__(
        self,
        script_func: Optional[Callable] = None,
        js_api_code: Optional[str] = None,
        run_script: Optional[Callable] = None
    ):
        """
        :param script_func: 执行 JS 字符串的函数
        :param js_api_code: 可选，设置 JS 侧回调函数名（如 'window.callbackFunction = ...'）
        :param run_script: 可选，覆盖默认的 run_script 实现
        """
        self.handlers = {}
        self.loaded = False
        self.destroyed = False
        self.script_func = script_func
        self.scripts = []
        self.final_scripts = []
        self.bulk_run = BulkRunScript(script_func)

        # 网格布局跟踪
        self._grid_spec: Optional[tuple[int, int]] = None  # (nrows, ncols)

        if run_script:
            self.run_script = run_script

        if js_api_code:
            self.run_script(f'window.callbackFunction = {js_api_code}')

    def on_js_load(self):
        """JS 页面加载完成后的回调，执行所有排队脚本。"""
        if self.loaded:
            return
        self.loaded = True

        if hasattr(self, '_return_q'):
            try:
                self.run_script_and_get('document.readyState == "complete"')
            except TimeoutError:
                raise RuntimeError(
                    "on_js_load: 远端超时，JS 页面未就绪。可能原因：\n"
                    "  1. WebView 未正常启动（检查浏览器路径/系统权限）\n"
                    "  2. 页面加载被阻塞（检查 index.html 资源加载）\n"
                    "  3. JS 桥未建立（检查 _return_q 是否正确设置）"
                )
            except RuntimeError as e:
                raise RuntimeError(
                    f"on_js_load: JS 执行出错 → {e}\n"
                    "  页面加载阶段发生 JS 错误，请检查 index.html 和 bundle.js"
                ) from e

        initial_script = ''
        self.scripts.extend(self.final_scripts)
        for script in self.scripts:
            initial_script += f'\n{script}'
        self.script_func(f'(async ()=> {{ {initial_script} }})();')

    def run_script(self, script: str, run_last: bool = False):
        """
        For advanced users; evaluates JavaScript within the Webview.
        """
        if self.destroyed:
            raise RuntimeError("Chart window has been destroyed. Cannot execute script.")
        if self.script_func is None:
            raise AttributeError("script_func has not been set")
        if self.loaded:
            if self.bulk_run.enabled:
                self.bulk_run.add_script(script)
            else:
                self.script_func(script)
        elif run_last:
            self.final_scripts.append(script)
        else:
            self.scripts.append(script)

    def run_script_and_get(self, script: str, timeout: float = 10.0):
        """同步执行 JS 脚本并获取返回值。
        :param script: JS 表达式
        :param timeout: 超时秒数
        :return: JS 返回值
        :raises TimeoutError: 超时未返回"""
        self.run_script(f'_~_~RETURN~_~_{script}')
        deadline = _time.time() + timeout
        while _time.time() < deadline:
            try:
                result = self._return_q.get_nowait()
            except Exception:
                _time.sleep(0.02)
                continue
            if result is None:
                raise RuntimeError(
                    f"JS evaluation error for: {script[:120]}"
                )
            return result
        raise TimeoutError(
            f"run_script_and_get timed out after {timeout}s for: {script[:120]}"
        )

    def remove_handler(self, handler_id: str):
        """
        Removes a single event/message handler by its ID.
        """
        self.handlers.pop(handler_id, None)

    def create_table(
        self,
        width: NUM,
        height: NUM,
        headings: tuple,
        widths: Optional[tuple] = None,
        alignments: Optional[tuple] = None,
        position: FLOAT = 'left',
        draggable: bool = False,
        background_color: str = '#121417',
        border_color: str = 'rgb(70, 70, 70)',
        border_width: int = 1,
        heading_text_colors: Optional[tuple] = None,
        heading_background_colors: Optional[tuple] = None,
        return_clicked_cells: bool = False,
        func: Optional[Callable] = None
    ) -> 'Table':
        """
        在图表上创建一个可交互的表格组件。

        :param width: 表格宽度。支持三种格式：
            - 整数（如 200）：固定像素宽度
            - 小数（如 0.2）：相对窗口宽度的百分比（0-1）
            - None：自动适应内容宽度
        :param height: 表格高度。支持三种格式：
            - 整数（如 150）：固定像素高度
            - 小数（如 0.3）：相对窗口高度的百分比（0-1）
            - None：自动适应内容高度
        :param headings: 表头列名元组，如 ('Symbol', 'Price', 'Volume')
        :param widths: 各列宽度比例元组，总和应为 1，如 (0.3, 0.35, 0.35)
        :param alignments: 各列对齐方式元组，可选值：'left', 'right', 'center'
        :param position: 表格位置，支持：
            - 'left'：左侧浮动
            - 'right'：右侧浮动
            - 元组 (x, y)：绝对位置，使用百分比坐标（0-1范围），如 (0.7, 0.1)
        :param draggable: 是否可拖动，默认为 False
        :param background_color: 表格背景颜色，默认为 '#121417'
        :param border_color: 边框颜色，默认为 'rgb(70, 70, 70)'
        :param border_width: 边框宽度（像素），默认为 1
        :param heading_text_colors: 表头文字颜色元组，如 ('#FFFFFF', '#FFFFFF', '#FFFFFF')
        :param heading_background_colors: 表头背景颜色元组，如 ('rgba(70, 130, 180, 0.8)',) * 3
        :param return_clicked_cells: 是否返回点击的单元格信息，默认为 False。
            为 True 时，回调函数会接收 (row, column) 参数；否则只接收 row 参数
        :param func: 行点击回调函数，签名为 func(row) 或 func(row, column)（当 return_clicked_cells=True 时）
        :return: Table 实例，可用于添加行、更新单元格数据等操作
        """
        return Table(*locals().values())

    def create_subchart(
        self,
        position: Position = 111,
        width: float = 1.0,
        height: float = 1.0,
        sync_id: Optional[str] = None,
        scale_candles_only: bool = False,
        sync_crosshairs_only: bool = False,
        toolbox: bool = False,
        autosize: bool = True,
        pane_index: int = 0,
        marker_auto_scale: bool = True
    ) -> 'AbstractChart':
        """创建子图表，支持独立缩放或同步十字光标。

        :param position: 子图位置（网格格式或字符串格式，如 111, (2,2,1), 'left'）
        :param width: 宽度比例（相对于网格单元，1.0=占满，<1.0=内缩对齐左上角，>1.0=侵占）
        :param height: 高度比例（相对于网格单元）
        :param sync_id: 同步组名。所有使用相同 sync_id 的子图会自动同步十字光标和时间轴。
            例如 sync_id="main" 会将子图加入 "main" 同步组。组内不同子图可独立设置 sync_crosshairs_only。
        :param scale_candles_only: 是否仅以 K 线范围缩放
        :param sync_crosshairs_only: 是否仅同步十字光标（不同步时间轴），默认为 False
        :param toolbox: 是否启用绘图工具箱
        :param autosize: 是否自动调整大小
        :param pane_index: 面板索引
        :param marker_auto_scale: 标记是否自动缩放
        :return: AbstractChart 子图实例

        :raises ValueError: 如果网格规格冲突（如先创建 311 再创建 221）
        """
        # 解析 position 获取网格规格
        position_info = parse_position(position)
        new_grid_spec = (position_info['nrows'], position_info['ncols'])

        # 检查网格规格冲突
        if self._grid_spec is not None and self._grid_spec != new_grid_spec:
            raise ValueError(
                f"网格规格冲突：当前窗口使用 {self._grid_spec[0]}x{self._grid_spec[1]} 网格，"
                f"但尝试创建 {new_grid_spec[0]}x{new_grid_spec[1]} 网格的图表。"
                f"所有图表必须使用相同的网格规格。"
            )

        # 更新网格规格（首次设置或相同规格）
        if self._grid_spec is None:
            self._grid_spec = new_grid_spec

        subchart = AbstractChart(
            self, width, height, scale_candles_only, toolbox,
            autosize=autosize, position=position, pane_index=pane_index,
            marker_auto_scale=marker_auto_scale
        )
        subchart._is_subchart = True
        # 如果指定了 sync_id，加入同步组
        if sync_id:
            self.run_script(f'''
                Lib.Handler.joinSyncGroup(
                    {subchart.id},
                    "{sync_id}",
                    {'true' if sync_crosshairs_only else 'false'}
                )
            ''')
        return subchart

    def style(
        self,
        background_color: str = '#0c0d0f',
        hover_background_color: str = '#3c434c',
        click_background_color: str = '#50565E',
        active_background_color: str = 'rgba(0, 122, 255, 0.7)',
        muted_background_color: str = 'rgba(0, 122, 255, 0.3)',
        border_color: str = '#3C434C',
        color: str = '#d8d9db',
        active_color: str = '#ececed'
    ):
        """自定义 UI 组件（顶栏、表格等）的全局样式。"""
        self.run_script(f'Lib.Handler.setRootStyles({js_json(locals())});')


class AbstractChart(Pane):
    """图表容器——管理所有序列和工具组件，自身不是任何 Series。

    采用组合模式：self.candle (CandleSeries) 管理 K 线数据，
    self.volume (VolumeSeries) / self.oi (OpenInterestSeries) 始终存在（reset 后自动重建）。
    所有 CandleSeries 方法通过委托保持向后兼容。
    """

    def __init__(self, window: Window, width: float = 1.0, height: float = 1.0,
                 scale_candles_only: bool = False, toolbox: bool = False,
                 autosize: bool = True, position: Position = 111, pane_index:int = 0, marker_auto_scale: bool = True
                 ):
        Pane.__init__(self, window)

        self._lines = []
        self.subcharts = []
        self._drawing_series: dict[int, DrawingSeries] = {}  # {pane_index: DrawingSeries}
        self._tables = []
        self._price_lines: list['PriceLine'] = []
        self._scale_candles_only = scale_candles_only
        self._width = width
        self._height = height
        self._is_subchart = False  # 由 create_subchart() 设为 True
        self._marker_auto_scale = marker_auto_scale  # 标记是否参与价格轴自动缩放
        # 时间级别（图表级，所有 series 共享）
        self._interval = None       # None = 未初始化，需先调 set() 或 set_period()
        self._offset = 0
        self._period_locked = False
        self.events: Events = Events(self)

        # 初始化PolygonAPI支持
        from .polygon import PolygonAPI
        self.polygon: PolygonAPI = PolygonAPI(self)

        # 获取当前图表数量（用于字符串格式转换）
        chart_count = len(self.win.handlers) + 1

        # 解析并存储 position 信息
        self._position_info = parse_position(position)
        grid_spec = (self._position_info['nrows'], self._position_info['ncols'])

        # 检查网格规格冲突（仅在已有图表时）
        if chart_count > 1 and self.win._grid_spec is not None and self.win._grid_spec != grid_spec:
            raise ValueError(
                f"网格规格冲突：当前窗口使用 {self.win._grid_spec[0]}x{self.win._grid_spec[1]} 网格，"
                f"但尝试创建 {grid_spec[0]}x{grid_spec[1]} 网格的图表。"
                f"所有图表必须使用相同的网格规格。"
            )

        # 设置窗口网格规格（首次设置）
        if self.win._grid_spec is None:
            self.win._grid_spec = grid_spec
        self._position = position

        # 生成 JS 初始化脚本（统一使用网格格式）
        self._html_chart_init = f'''
                {self.id} = new Lib.Handler(
                "{self.id}", {width}, {height},
                {self._position_info["nrows"]}, {self._position_info["ncols"]}, {self._position_info["index"]},
                {jbool(autosize)}
            );
            0
        '''
        self.run_script(self._html_chart_init)

        # ── 组合模式：主 series 使用固定 ID 创建 ──
        base = self.id.replace('window.', '')  # 如 'Chart_1'
        self.candle = CandleSeries(self, _fixed_id=f'window.{base}_candle', _dont_add_list=True, legend=False)
        self.volume: 'VolumeSeries' = VolumeSeries(self, _fixed_id=f'window.{base}_volume', _dont_add_list=True, legend=False)
        self.oi: 'OpenInterestSeries' = OpenInterestSeries(self, _fixed_id=f'window.{base}_oi', _dont_add_list=True, legend=False)

        # 设置 Handler 的 series 引用（audit 和 _toggle_data 需要）
        # seriesMarkers 由 _update_markers() 按需在 series 级别创建，无需复制到 Handler
        self.run_script(f'''
            {self.id}.series = {self.candle.id}.series;
            {self.id}.volumeSeries = {self.volume.id}.series;
            {self.id}.openInterestSeries = {self.oi.id}.series;
            0;
        ''')

        self.subcharts.append(self.id)

        self.topbar: TopBar = TopBar(self)
        self.toolbox: ToolBox = ToolBox(self) if toolbox else None

    # ── DrawingSeries 管理 ──

    def _get_drawing_series(self, pane_index=0):
        """内部方法：获取或创建指定 pane 的 DrawingSeries。"""
        if pane_index not in self._drawing_series:
            self._drawing_series[pane_index] = DrawingSeries(self, pane_index)
        return self._drawing_series[pane_index]

    @property
    def drawings(self):
        """返回所有 pane 的 drawing 列表（兼容旧代码）。"""
        result = []
        for ds in self._drawing_series.values():
            result.extend(ds._drawings)
        return result

    # ═══════════════════════════════════════════════════════
    #  委托方法 — 向后兼容 chart.set() / chart.update() 等 API
    # ═══════════════════════════════════════════════════════

    # ── CandleSeries 属性代理 ──

    @property
    def candle_data(self):
        """K 线数据 DataFrame（time, open, high, low, close）。"""
        return self.candle.data

    @property
    def vol_data(self):
        """成交量数据 DataFrame（time, value）。"""
        df = self.volume.data
        if df is None or df.empty:
            return df
        return df[['time', 'value']]

    @property
    def oi_data(self):
        """持仓量数据 DataFrame（time, value）。"""
        return self.oi.data

    @property
    def data(self):
        """合并后的 K 线 + 成交量 + 持仓量 DataFrame，按时间对齐，缺失条目填 NaN。

        始终返回 7 列: time, open, high, low, close, volume, open_interest。
        """
        _COLS = ['time', 'open', 'high', 'low', 'close', 'volume', 'open_interest']

        parts = []

        candle_df = self.candle.data
        if candle_df is not None and not candle_df.empty:
            parts.append(candle_df[['time', 'open', 'high', 'low', 'close']])

        vol_df = self.volume.data
        if vol_df is not None and not vol_df.empty:
            parts.append(vol_df[['time', 'value']].rename(columns={'value': 'volume'}))

        oi_df = self.oi.data
        if oi_df is not None and not oi_df.empty:
            parts.append(oi_df[['time', 'value']].rename(columns={'value': 'open_interest'}))

        if not parts:
            return pd.DataFrame(columns=_COLS)

        result = pd.concat(parts, ignore_index=True).groupby('time', as_index=False).first()
        result = result.reindex(columns=_COLS)
        result.sort_values('time', inplace=True)
        result.reset_index(drop=True, inplace=True)
        return result

    @property
    def markers(self):
        """标记字典。"""
        return self.candle.markers

    # ── 时间级别方法（图表级，不再委托到 candle）──

    def _set_interval(self, df: pd.DataFrame):
        """根据数据时间点，智能地设置时间间隔。"""
        if self._period_locked:
            return
        self._interval, self._offset = get_df_interval_offset(df)

    def _time_to_bar_time(self, data):
        """将时间戳对齐到 bar 时间边界。"""
        if self._interval is None:
            raise RuntimeError("时间级别未初始化，请先调用 chart.set() 或 chart.set_period()。")
        return time_to_bar_time(data, self._offset, self._interval)

    def _single_datetime_format(self, arg) -> int:
        """格式化单个时间值为秒级时间戳。"""
        if self._interval is None:
            raise RuntimeError("时间级别未初始化，请先调用 chart.set() 或 chart.set_period()。")
        if not isinstance(arg, (int, np.int64, float, np.float64)):
            arg = (pd.to_datetime(arg, unit='s').tz_localize(None) - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')
        return int(self._time_to_bar_time(arg))

    def _clean_df(self, df, _df_cleaned=False):
        """清洗 DataFrame（normal_df + _time_to_bar_time + merge_value_by_time）。

        :param df: 输入 DataFrame
        :param _df_cleaned: True 表示数据已清洗过，跳过全部三步。
            False（默认）执行完整清洗流程。
        """
        if _df_cleaned:
            return df
        df = normal_df(df)
        df = self._time_to_bar_time(df)
        df = merge_value_by_time(df)
        return df

    def set_period(self, seconds: Optional[int] = None):
        """
        锁定/解锁图表的时间间隔。
        锁定后 set() 将跳过自动检测，使用指定的时间间隔。

        :param seconds: 时间间隔（秒），None 则解锁

        Example::

            chart.set_period(60)       # 锁定为 1 分钟
            chart.set_period(300)      # 锁定为 5 分钟
            chart.set_period(None)     # 解锁，恢复自动检测
            chart.set(df)              # 下一次 set 时生效
        """
        if seconds is not None:
            self._interval = seconds
            self._period_locked = True
        else:
            self._period_locked = False

    # ── 高频数据方法（显式委托，IDE 友好）──

    def set(self, df: Optional[pd.DataFrame] = None):
        """设置 K 线数据。自动检测 volume/OI 列并转发数据给独立 series。

        .. deprecated::
            不再联动设置 _lines。Line/Histogram 需要各自调用 ``line.set(df)`` 独立设置数据。
        """
        if self.toolbox is not None:
            self.toolbox.clear_drawings()
        self.candle.set(None)
        self.volume.set(None)
        self.oi.set(None)

        if df is not None and not df.empty:
            # 需要先 normal ，才能设定 interval
            df = normal_df(df)
            self._set_interval(df)
            self.update_bars(df)

    def update_bar(self, series):
        """更新最新一根 bar 或追加新 bar。"""
        self.update_bars(series.to_frame().T)

    def update_bars(self, df):
        """批量更新多根 K 线（OHLC + volume + OI）。

        更新顺序：candle → volume → oi。
        每个 series 独立维护 _last_bar，顺序不影响正确性。

        .. deprecated::
            不再联动更新 _lines。Line/Histogram 需要各自调用 ``line.update_bars(df)`` 独立更新。
        """
        df = self._clean_df(df)
        if 'open' in df.columns:
            self.candle.update_bars(df, _df_cleaned=True)
        if 'volume' in df.columns:
            self.volume.update_bars(df[['time', 'volume', 'open', 'close']].rename(columns={'volume': 'value'}), _df_cleaned=True)
        if 'open_interest' in df.columns:
            self.oi.update_bars(df[['time', 'open_interest']].rename(columns={'open_interest': 'value'}), _df_cleaned=True)

    def update_tick(self, series):
        """使用单个 tick 更新图表。委托给 update_ticks 统一处理。"""
        return self.update_ticks(series.to_frame().T)

    def update_ticks(self, df):
        """批量使用 tick 更新图表（OHLC + volume + OI）。

        接受 4 列 tick 数据：time, price, volume, open_interest。
        只做 normal_df + time_to_bar_time（不做 merge_value_by_time），
        然后交给 CandleSeries/VolumeSeries/OISeries 各自做 tick→bar 聚合。

        .. deprecated::
            不再联动更新 _lines。Line/Histogram 需要各自独立更新。
        """
        if df.empty:
            return

        if self._interval is None:
            raise ValueError("set_period() 未设置时间间隔，无法更新 tick 数据")

        # 简单处理，只做 normal_df + time_to_bar_time（不做 merge_value_by_time）
        df = normal_df(df)
        df = self._time_to_bar_time(df)

        # ── candle：price → value ──
        if 'price' in df.columns:
            candle_df = df[['time', 'price']].rename(columns={'price': 'value'})
            self.candle.update_ticks(candle_df, _df_cleaned=True)

        # ── volume：price + volume → value ──
        if 'volume' in df.columns:
            self.volume.update_ticks(
                df[["time", "volume", "price"]].rename(columns={"volume": "value"}),
                _df_cleaned=True
            )

        # ── OI：open_interest → value ──
        if 'open_interest' in df.columns:
            self.oi.update_ticks(
                df[['time', 'open_interest']].rename(columns={'open_interest': 'value'}),
                _df_cleaned=True
            )

    def clear_data(self):
        """清空所有 K 线数据（K线 + 成交量 + 持仓量）。"""
        self.candle.clear_data()
        self.volume.clear_data()
        self.oi.clear_data()

    # ── 标记方法（显式委托）──

    def add_marker(self, time=None, position='below', shape='arrow_up', color='#2196F3', text='', size=1):
        """创建标记。"""
        return self.candle.add_marker(time=time, position=position, shape=shape, color=color, text=text, size=size)

    def remove_marker(self, marker_id):
        """移除标记。"""
        return self.candle.remove_marker(marker_id)

    def add_markers(self, marker_list):
        """批量创建标记。"""
        return self.candle.add_markers(marker_list)

    def clear_markers(self, _dont_update: bool = False):
        """清空所有标记。"""
        return self.candle.clear_markers(_dont_update)

    # ── 样式配置（显式委托）──

    def candle_style(self, **kwargs):
        """配置 K 线样式。"""
        return self.candle.candle_style(**kwargs)

    def volume_config(self, scale_margin_top: float = 0.8, scale_margin_bottom: float = 0.0,
                      up_color=None, down_color=None):
        """配置成交量样式。"""
        self.volume.config(
            scale_margin_top=scale_margin_top, scale_margin_bottom=scale_margin_bottom,
            up_color=up_color, down_color=down_color
        )

    def open_interest_config(self, scale_margin_top: float = 0.8, scale_margin_bottom: float = 0.0,
                             color=None):
        """配置持仓量样式。"""
        self.oi.config(
            scale_margin_top=scale_margin_top, scale_margin_bottom=scale_margin_bottom, color=color
        )

    def price_scale(self, **kwargs):
        """配置价格坐标轴。"""
        return self.candle.price_scale(**kwargs)

    # ── 绘图方法（委托到内部 DrawingSeries）──

    def horizontal_line(self, price, color='rgb(122, 146, 202)', width=2,
                        style='solid', text='', axis_label_visible=True, func=None, pane_index=0):
        """创建水平线。"""
        return self._get_drawing_series(pane_index).horizontal_line(
            price, color, width, style, text, axis_label_visible, func)

    def trend_line(self, start_time, start_value, end_time, end_value,
                   round=False, line_color='#1E80F0', width=2, style='solid', pane_index=0):
        """创建趋势线。"""
        return self._get_drawing_series(pane_index).trend_line(
            start_time, start_value, end_time, end_value, round, line_color, width, style)

    def ray_line(self, start_time, value, round=False, color='#1E80F0', width=2, style='solid', text='', pane_index=0):
        """创建射线。"""
        return self._get_drawing_series(pane_index).ray_line(
            start_time, value, round, color, width, style, text)

    def vertical_line(self, time, color='#1E80F0', width=2, style='solid', text='', pane_index=0):
        """创建垂直线。"""
        return self._get_drawing_series(pane_index).vertical_line(time, color, width, style, text)

    def vertical_span(self, start_time, end_time=None, color='rgba(252, 219, 3, 0.2)', round=False):
        """创建垂直区间。"""
        if round:
            start_time = self._single_datetime_format(start_time)
            end_time = self._single_datetime_format(end_time) if end_time else None
        return VerticalSpan(self, start_time, end_time, color)

    def box(self, start_time, start_value, end_time, end_value,
            round=False, color='#1E80F0', fill_color='rgba(255, 255, 255, 0.2)', width=2, style='solid', pane_index=0):
        """创建矩形。"""
        return self._get_drawing_series(pane_index).box(
            start_time, start_value, end_time, end_value, round, color, fill_color, width, style)

    # ── 其他委托 ──
    def precision(self, precision=2):
        """设置精度。"""
        return self.candle.precision(precision)

    def pop(self, count=1):
        """从末尾移除数据点。"""
        self.candle.pop(count)
        self.volume.pop(count)
        self.oi.pop(count)

    def hide_data(self):
        """隐藏所有数据（candle + volume + oi）。"""
        self.candle.hide_data()
        self.volume.hide_data()
        self.oi.hide_data()

    def show_data(self):
        """显示所有数据（candle + volume + oi）。"""
        self.candle.show_data()
        self.volume.show_data()
        self.oi.show_data()

    # ═══════════════════════════════════════════════════════

    def fit(self):
        """
        Fits the maximum amount of the chart data within the viewport.
        """
        self.run_script(f'{self.id}.chart.timeScale().fitContent()')

    @staticmethod
    def _normalize_sync_id(sync_id):
        """规范化 sync_id 参数。

        :param sync_id: str | None | bool
        :return: str | None（组名字符串或 None）
        :raises TypeError: 如果输入类型不合法
        """
        if sync_id is None or sync_id is False:
            return None
        if sync_id is True:
            return 'True'
        if isinstance(sync_id, str):
            return sync_id
        raise TypeError(
            f"sync_id 只能是 str、None、True 或 False，收到 {type(sync_id).__name__}"
        )

    def join_sync_group(self, group_name, sync_crosshairs_only: bool = False):
        """
        将当前图表加入指定同步组。同组内所有图表自动同步十字光标和/或时间范围。
        可在任意时刻调用，包括主图表和已创建的子图。

        :param group_name: 同步组名（字符串、True 或 None），同名图表自动同步
        :param sync_crosshairs_only: True 则仅同步十字光标，不同步时间范围
        """
        group_name = self._normalize_sync_id(group_name)
        if group_name is None:
            return
        self.win.run_script(f'''
            Lib.Handler.joinSyncGroup(
                {self.id},
                "{group_name}",
                {'true' if sync_crosshairs_only else 'false'}
            )
        ''')

    def _clear_handlers(self):
        """
        清空 Window 上所有图表的全部 handler 回调。

        ⚠️ 内部方法，仅供 reset() 调用。不应手动调用！

        原因：
        - 会清掉 ToolBox 的 save_drawings 回调、TopBar 控件回调、
          JSEmitter 事件回调、hotkey 回调等所有已注册的 handler
        - reset() 调用后会立即恢复主图的 ToolBox handler，
          但其他 handler（如 events.search/click/crosshair 等）不会恢复
        - 如果确实需要清理特定图表的 handler，应使用 _remove_my_handlers()
        """
        if self._is_subchart:
            raise RuntimeError("_clear_handlers() 只能在主图表上调用，不能在子图上调用。")
        self.win.handlers.clear()

    def reset(self):
        """
        Resets the chart to a clean initial state without destroying the WebView.
        Only available on the main chart (not subcharts).

        Deletes candle/volume/oi JS objects and resets Python state.
        After reset(), call set() to recreate and repopulate.
        TopBar widgets and styling options are preserved.
        """
        if self._is_subchart:
            raise RuntimeError("reset() 只能在主图表上调用，并且会删除所有子图表。子图请使用 reset_sub()。")

        # 清理子图表
        for sub_id in list(self.subcharts):
            if sub_id != self.id:
                self.remove_subchart(sub_id)
        self.subcharts = [self.id]

        # 删除 PriceLines
        for series in list(self._price_lines):
            series.delete()

        # 删除所有附属 Line/Histogram 系列
        for line in list(self._lines):
            line.delete()

        # 销毁 ToolBox（JS toolBox + drawings + 回调 + handler）
        if self.toolbox is not None:
            self.toolbox._delete()

        self.topbar.delete()

        # 删除 candle/volume/oi 的 JS 对象和 Python 数据
        self.candle.delete()
        self.volume.delete()
        self.oi.delete()

        self.run_script(f'''
            {self.id}.series = null;
            {self.id}.volumeSeries = null;
            {self.id}.openInterestSeries = null;
            0;
        ''')

        # 重置图表状态
        self._interval = None
        self._offset = 0
        self._period_locked = False

        # 清理事件处理器（包括子图的 ToolBox/topbar/events 等回调）
        self._clear_handlers()

        # 重建 candle/volume/oi（始终存在，省去后续所有 None 检查）
        self.candle._build()
        self.volume._build()
        self.oi._build()
        self.run_script(f'''
            {self.id}.series = {self.candle.id}.series;
            {self.id}.volumeSeries = {self.volume.id}.series;
            {self.id}.openInterestSeries = {self.oi.id}.series;
            0;
        ''')

        # 重建 ToolBox（创建 JS toolBox + 注册 handler）
        if self.toolbox is not None:
            self.toolbox._build()

    def remove_subchart(self, subchart_id: str):
        """
        Removes and destroys a subchart created via create_subchart().

        :param subchart_id: the .id attribute of the subchart AbstractChart.
        """
        if subchart_id not in self.subcharts:
            raise ValueError(f"Subchart {subchart_id} not found in this chart.")
        self.subcharts.remove(subchart_id)
        self.run_script(f'''
            (() => {{
                const h = {subchart_id};
                // 清理引用此 handler series 的 window 全局变量（VolumeSeries/OI 等）
                const seriesSet = new Set([h.series, h.volumeSeries, h.openInterestSeries].filter(Boolean));
                Object.keys(window).forEach(k => {{
                    const v = window[k];
                    if (v && typeof v === 'object' && v.series && seriesSet.has(v.series)) {{
                        delete window[k];
                    }}
                }});
                h.chart.remove();
                h.wrapper.remove();
                var _hid = Lib.Handler._all.findIndex(function(h2) {{ return h2.id === "{subchart_id}" }});
                if (_hid >= 0) Lib.Handler._all.splice(_hid, 1);
                delete {subchart_id};
            }})()
        ''')

    def reset_sub(self):
        """
        清除子图全部内容，保留布局，不影响其他子图。

        清除范围：
        1. K线/成交量/持仓量数据
        2. 所有 Line/Histogram 系列
        3. 所有 PriceLine
        4. 所有标记
        5. 所有绘图（Drawings）
        6. 所有表格（Tables）
        7. ToolBox（DrawingTool 事件、ContextMenu、commandFunction、DOM）
        8. TopBar（Widget 回调、DOM）
        9. Legend（crosshair 订阅、DOM）
        10. Events（JSEmitter 事件订阅）
        11. syncCharts 双向解关联 + 重建
        12. handlers 清理
        13. Legend 重建（最后执行，恢复到初始隐藏状态）
        """

        # 删除所有表格
        for t in list(self._tables):
            t.delete()

        # 销毁 ToolBox （JS toolBox + drawings + 回调 + handler）
        if self.toolbox is not None:
            self.toolbox._delete()

        # 销毁 TopBar（JS DOM + handler 引用 + widget 回调）
        self.topbar.delete()

        # 销毁 Line/Histogram 系列
        for line in list(self._lines):
            line.delete()

        # 销毁 PriceLine
        for pl in list(self._price_lines):
            pl.delete()

        # 删除所有绘图
        for ds in list(self._drawing_series.values()):
            ds.delete()
        self._drawing_series.clear()

        # 删除 K线/成交量/持仓量数据
        self.candle.delete()
        self.volume.delete()
        self.oi.delete()
        self.run_script(f'''
            {self.id}.series = null;
            {self.id}.volumeSeries = null;
            {self.id}.openInterestSeries = null;
            0;
        ''')

        # Legend 清理
        self.run_script(f'{self.id}.legend.cleanup()')

        # Events 清理（JSEmitter）
        self._cleanup_events()

        # syncCharts 双向解关联 + 重建
        self._unsync_all()

        # handlers 清理（salt 匹配）
        self._remove_my_handlers()

        # candle, volume, oi 重建
        self.candle._build()
        self.volume._build()
        self.oi._build()
        self.run_script(f'''
            {self.id}.series = {self.candle.id}.series;
            {self.id}.volumeSeries = {self.volume.id}.series;
            {self.id}.openInterestSeries = {self.oi.id}.series;
            0;
        ''')

        # Legend 重建（最后执行）
        # cleanup() 的 div.remove() 将 legend DOM 从文档树移除，
        # 但后续 legend()/makeSeriesRow() 仍需要一个在 DOM 中的 div。
        # 放在所有清理之后重建，确保 crosshair 订阅不被后续清理干扰。
        # 重建后 div 恢复到"已创建但隐藏"(display:none) 的初始状态，
        # 等待 Python 端 legend(visible=True) 激活。
        self.run_script(f'{self.id}.legend.recreate()')

        # ToolBox 重建（在所有清理之后）
        if self.toolbox is not None:
            self.toolbox._build()

    def _cleanup_events(self):
        """清理 JSEmitter 事件订阅。"""
        salt = '_' + self.id[self.id.index('.') + 1:]
        event_keys = [
            f'range_change{salt}',
            f'subscribe_click{salt}',
            f'crosshair_move{salt}',
        ]
        for key in event_keys:
            self.win.handlers.pop(key, None)

    def _unsync_all(self):
        """双向解除所有同步关联，并按 _syncGroup 重建。

        设计思路：
          采用"先全部清空，再按组重建"策略，避免逐一拆解 pair sync 的复杂性。

        自动恢复机制：
          reset_sub 后调用 set() 重新填充数据，同步关系会自动恢复。
          因为本图的 _syncGroup 保留了组名，重建时会被纳入同组的 syncGroup 调用。

        执行流程：
          Step 1: 清理所有 handler 的旧 sync 回调
          Step 2: 按 _syncGroup 分组，每组调用 syncGroup 重建
        """
        my_id = self.id
        self.run_script(f'''
            (() => {{
                const myId = "{my_id}";

                // ── Step 1: 清理所有 handler 的旧 sync 回调 ──
                // 逐一拆解 pair sync 容易遗漏（如链式同步中非直接关联的 handler），
                // 因此直接清理全部，然后按组统一重建。
                Lib.Handler._all.forEach(h => {{
                    for (const [, cb] of Object.entries(h._syncCallbacks)) {{
                        if (cb.crosshair && cb.crosshairSource) {{
                            cb.crosshairSource.chart.unsubscribeCrosshairMove(cb.crosshair);
                        }}
                        if (cb.range && cb.rangeSource) {{
                            cb.rangeSource.chart.timeScale().unsubscribeVisibleLogicalRangeChange(cb.range);
                        }}
                    }}
                    h._syncCallbacks = {{}};
                    h._syncedHandlers = [];
                }});

                // ── Step 2: 按 _syncGroup 分组重建 ──
                // 所有 _syncGroup 非空的 handler，按组名分组后调用 syncGroup 重建。
                // 本图的 _syncGroup 保留了组名（Step 1 只清 _syncCallbacks，不清 _syncGroup），
                // 因此会被纳入重建，实现 reset 后同步自动恢复。
                const groups = {{}};
                Lib.Handler._all.forEach(h => {{
                    if (h._syncGroup) {{
                        if (!groups[h._syncGroup]) groups[h._syncGroup] = [];
                        groups[h._syncGroup].push(h);
                    }}
                }});
                for (const [, groupHandlers] of Object.entries(groups)) {{
                    if (groupHandlers.length > 1) {{
                        Lib.Handler.syncGroup(groupHandlers);
                    }}
                }}
            }})()
        ''')

    def _remove_my_handlers(self):
        """从共享 handlers 字典中移除属于本子图的条目。

        使用 salt 匹配（子字符串匹配），只移除 handler key 中包含本图 ID 后缀的条目。
        例如本图 ID 为 window.AbstractChart_3，则 salt = '_AbstractChart_3'，
        只会移除 key 中包含 '_AbstractChart_3' 的 handler，不会影响其他图表。
        """
        salt = '_' + self.id[self.id.index('.') + 1:]
        to_remove = [k for k in self.win.handlers if salt in str(k)]
        for k in to_remove:
            del self.win.handlers[k]

    def audit(self, use_js: bool = False):
        """
        审计当前 chart 的资源状态。

        :param use_js: True 时从 JS 端获取完整审计信息（TOML 格式），
                       False 时纯 Python 侧收集，返回 dict。
        """
        if use_js:
            data = self.win.run_script_and_get('Lib.Handler.audit()', timeout=5)
            return tomllib.loads(data)
        else:
            return self._audit_full()

    def _audit_full(self) -> dict:
        """
        从 Python 侧收集所有资源的 ID、类型、参数，不依赖 JS 桥接。
        """
        info = {
            'chart': {
                'id': self.id,
                'type': 'AbstractChart',
                'has_data': not self.candle.data.empty,
                'subchart_ids': [s for s in self.subcharts if s != self.id],
                'interval': self._interval,
                'offset': self._offset,
                'period_locked': self._period_locked,
            },
            'lines': [],
            'price_lines': [],
            'markers': [],
            'subcharts': [],
            'tables': [],
            'drawings': [],
            'drawing_series': [],
            'toolbox': {},
            'volume_oi': {},
        }

        # --- volume/oi 数据状态 ---
        if self.volume is not None:
            info['volume_oi']['volume'] = {
                'has_data': not self.volume.data.empty,
                'data_points': len(self.volume.data) if not self.volume.data.empty else 0,
            }
        if self.oi is not None:
            info['volume_oi']['open_interest'] = {
                'has_data': not self.oi.data.empty,
                'data_points': len(self.oi.data) if not self.oi.data.empty else 0,
            }

        # --- toolbox ---
        if self.toolbox is not None:
            info['toolbox'] = {
                'has_toolbox': True,
                'on_change_callbacks': len(self.toolbox.on_change),
                'tracked_drawings': len(self.toolbox.drawings_list),
            }

        # --- drawing_series（per-pane 管理器）---
        for pane_idx, ds in self._drawing_series.items():
            info['drawing_series'].append({
                'pane_index': pane_idx,
                'id': ds.id,
                'drawings_count': len(ds._drawings),
            })

        # --- lines (including histograms) ---
        for line in self._lines:
            entry = {
                'id': line.id,
                'type': type(line).__name__,
                'name': getattr(line, 'name', ''),
                'color': getattr(line, 'color', ''),
            }
            if hasattr(line, 'data') and not line.data.empty:
                entry['data_points'] = len(line.data)
            info['lines'].append(entry)

        # --- price lines ---
        for pl in self._price_lines:
            info['price_lines'].append({
                'id': pl.id,
                'type': 'PriceLine',
            })

        # --- markers ---
        for mid, m in self.candle.markers.items():
            info['markers'].append({
                'id': mid,
                'type': 'Marker',
                'time': m.get('time'),
                'text': m.get('text', ''),
                'shape': m.get('shape'),
                'position': m.get('position'),
            })

        # --- subcharts ---
        for sub_id in self.subcharts:
            if sub_id != self.id:
                info['subcharts'].append({
                    'id': sub_id,
                    'type': 'AbstractChart',
                })

        # --- drawings ---
        for d in self.drawings:
            entry = {
                'id': d.id,
                'type': type(d).__name__,
            }
            if hasattr(d, 'price'):
                entry['price'] = d.price
            info['drawings'].append(entry)

        # --- tables ---
        for t in self._tables:
            info['tables'].append({
                'id': t.id,
                'type': 'Table',
                'headings': list(t.headings) if hasattr(t, 'headings') else [],
            })

        # --- window handlers ---
        info['handlers_count'] = len(self.win.handlers)

        return info

    def create_line(
            self, name: str = '', color: str = 'rgba(214, 237, 255, 0.6)',
            style: LINE_STYLE = 'solid', width: int = 2,
            price_line: bool = True, price_label: bool = True, price_scale_id: Optional[str] = None,
            pane_index: int = 0, legend: bool = True, group: str = None
    ) -> LineSeries:
        """
        创建并返回一个折线图对象。

        :param name: 线图名称，用于图例显示
        :param color: 线条颜色
        :param style: 线条样式
        :param width: 线条宽度
        :param price_line: 是否显示价格线
        :param price_label: 是否显示价格标签
        :param price_scale_id: 价格刻度ID
        :param pane_index: 面板索引
        :param legend: 是否在图例中显示此系列
        :param group: 图例分组名。同组的 series 在 legend 中显示在同一行，前面有 ♦ 组开关。
        :return: LineSeries 实例
        """
        line = LineSeries(self, name, color, style, width, price_line, price_label, price_scale_id, pane_index=pane_index, legend=legend, group=group)
        self._lines.append(line)
        return line

    def create_histogram(
            self, name: str = '', color: str = 'rgba(214, 237, 255, 0.6)',
            price_line: bool = True, price_label: bool = True,
            scale_margin_top: float = 0.0, scale_margin_bottom: float = 0.0,
            pane_index: int = 0, legend: bool = True, group: str = None,
    ) -> HistogramSeries:
        """
        创建并返回一个柱状图（直方图）对象，通常用于显示成交量。

        :param name: 柱状图名称，用于图例显示
        :param color: 柱状图颜色
        :param price_line: 是否显示价格线
        :param price_label: 是否显示价格标签
        :param scale_margin_top: 顶部刻度边距（0-1）
        :param scale_margin_bottom: 底部刻度边距（0-1）
        :param pane_index: 面板索引
        :param legend: 是否在图例中显示此系列
        :param group: 图例分组名。同组的 series 在 legend 中显示在同一行，前面有 ♦ 组开关。
        :return: HistogramSeries 实例
        """
        hist = HistogramSeries(self, name, color, price_line, price_label, scale_margin_top, scale_margin_bottom, pane_index, legend=legend, group=group)
        self._lines.append(hist)
        return hist

    def create_price_line(self, price=0.0, color='rgba(214, 237, 255, 0.6)',
                          style='large_dashed', width=1, price_label=False, title=''):
        """创建价格线。"""
        return PriceLine(self, price, color, style, width, price_label, title)

    def create_candle_series(
            self, name: str = '', pane_index: int = 0,
            up_color: str = 'rgba(39, 157, 130, 100)',
            down_color: str = 'rgba(200, 97, 100, 100)',
            border_visible: bool = True, wick_visible: bool = True,
            price_line: bool = False, price_label: bool = True,
            price_scale_id: Optional[str] = None,
            crosshair_marker: bool = True, legend: bool = True, group: str = None
    ) -> CandleSeries:
        """
        创建并返回一个独立 K 线系列对象（无 volume/open interest）。

        :param name: K 线名称，用于图例显示
        :param pane_index: 面板索引，用于在多个面板中放置
        :param up_color: 上涨K线颜色
        :param down_color: 下跌K线颜色
        :param border_visible: 是否显示K线边框
        :param wick_visible: 是否显示影线
        :param price_line: 是否显示价格线（在图表右侧显示当前价格）
        :param price_label: 是否显示价格标签
        :param price_scale_id: 价格刻度ID，用于共享刻度
        :param crosshair_marker: 十字光标是否显示标记
        :param group: 图例分组名。同组的 series 在 legend 中显示在同一行，前面有 ♦ 组开关。
        :return: CandleSeries 实例
        """
        candle = CandleSeries(
            self, name, pane_index,
            up_color=up_color, down_color=down_color,
            border_visible=border_visible, wick_visible=wick_visible,
            price_line=price_line, price_label=price_label,
            price_scale_id=price_scale_id, crosshair_marker=crosshair_marker,
            legend=legend, group=group,
        )
        self._lines.append(candle)
        return candle

    def create_area_series(
            self, name: str = '', color: str = '#2196F3',
            style: LINE_STYLE = 'solid', width: int = 2,
            top_color: str = 'rgba(33, 150, 243, 0.4)',
            bottom_color: str = 'rgba(33, 150, 243, 0)',
            relative_gradient: bool = False,
            invert_filled_area: bool = False,
            price_line: bool = True, price_label: bool = True,
            price_scale_id: Optional[str] = None,
            pane_index: int = 0, legend: bool = True, group: str = None
    ) -> AreaSeries:
        """
        创建并返回一个面积图对象（折线+渐变填充）。

        :param name: 面积图名称，用于图例显示
        :param color: 线条颜色
        :param style: 线条样式
        :param width: 线条宽度
        :param top_color: 面积顶部渐变颜色（RGBA）
        :param bottom_color: 面积底部渐变颜色（RGBA）
        :param relative_gradient: 渐变是否相对于基准值
        :param invert_filled_area: 是否反转填充区域
        :param price_line: 是否显示价格线
        :param price_label: 是否显示价格标签
        :param price_scale_id: 价格刻度ID
        :param pane_index: 面板索引
        :return: AreaSeries 实例
        """
        area = AreaSeries(self, name, color, style, width,
                          top_color, bottom_color, relative_gradient, invert_filled_area,
                          price_line, price_label, price_scale_id, pane_index=pane_index, legend=legend, group=group)
        self._lines.append(area)
        return area

    def create_ohlc_bar_series(
            self, name: str = '',
            up_color: str = '#26a69a', down_color: str = '#ef5350',
            open_visible: bool = True, thin_bars: bool = True,
            price_line: bool = False, price_label: bool = True,
            price_scale_id: Optional[str] = None,
            pane_index: int = 0, legend: bool = True, group: str = None
    ) -> OHLCBarSeries:
        """
        创建并返回一个美国线（OHLC 横向柱状图）对象。

        与 K 线使用同一套 OHLC 数据，但用横向短横表示 open/close。

        :param name: 系列名称，用于图例显示
        :param up_color: 上涨颜色
        :param down_color: 下跌颜色
        :param open_visible: 是否显示 open 横线
        :param thin_bars: 是否用细棒显示
        :param price_line: 是否显示价格线
        :param price_label: 是否显示价格标签
        :param price_scale_id: 价格刻度ID
        :param pane_index: 面板索引
        :return: OHLCBarSeries 实例
        """
        bar = OHLCBarSeries(self, name, up_color, down_color, open_visible, thin_bars,
                            price_line, price_label, price_scale_id, pane_index=pane_index, legend=legend, group=group)
        self._lines.append(bar)
        return bar

    def create_baseline_series(
            self, name: str = '',
            base_value: float = 0,
            top_fill_color1: str = 'rgba(38, 166, 154, 0.28)',
            top_fill_color2: str = 'rgba(38, 166, 154, 0.05)',
            top_line_color: str = 'rgba(38, 166, 154, 1)',
            bottom_fill_color1: str = 'rgba(239, 83, 80, 0.05)',
            bottom_fill_color2: str = 'rgba(239, 83, 80, 0.28)',
            bottom_line_color: str = 'rgba(239, 83, 80, 1)',
            line_width: int = 2, line_style: LINE_STYLE = 'solid',
            relative_gradient: bool = False,
            price_line: bool = True, price_label: bool = True,
            price_scale_id: Optional[str] = None,
            pane_index: int = 0, legend: bool = True, group: str = None
    ) -> BaselineSeries:
        """
        创建并返回一个基准线对象，以某个基准值为界上下分色。

        :param name: 系列名称
        :param base_value: 基准值
        :param top_fill_color1: 上方区域渐变起始色
        :param top_fill_color2: 上方区域渐变结束色
        :param top_line_color: 上方区域线条颜色
        :param bottom_fill_color1: 下方区域渐变起始色
        :param bottom_fill_color2: 下方区域渐变结束色
        :param bottom_line_color: 下方区域线条颜色
        :param line_width: 线条宽度
        :param line_style: 线条样式
        :param relative_gradient: 渐变是否相对于基准值
        :param price_line: 是否显示价格线
        :param price_label: 是否显示价格标签
        :param price_scale_id: 价格刻度ID
        :param pane_index: 面板索引
        :param group: 图例分组名。同组的 series 在 legend 中显示在同一行，前面有 ♦ 组开关。
        :return: BaselineSeries 实例
        """
        baseline = BaselineSeries(self, name, base_value,
                                  top_fill_color1, top_fill_color2, top_line_color,
                                  bottom_fill_color1, bottom_fill_color2, bottom_line_color,
                                  line_width, line_style, relative_gradient,
                                  price_line, price_label, price_scale_id, pane_index=pane_index, legend=legend, group=group)
        self._lines.append(baseline)
        return baseline

    def lines(self) -> list[SeriesCommon]:
        """
        Returns all lines for the chart.
        """
        return self._lines.copy()

    def set_visible_range(self, start_time: TIME, end_time: TIME):
        """设置时间轴的可见范围。
        :param start_time: 可见范围起始时间
        :param end_time: 可见范围结束时间"""
        self.run_script(f'''
        {self.id}.chart.timeScale().setVisibleRange({{
            from: {pd.to_datetime(start_time).tz_localize(None).timestamp()},
            to: {pd.to_datetime(end_time).tz_localize(None).timestamp()}
        }})
        ''')

    def resize(self, width: Optional[float] = None, height: Optional[float] = None):
        """
        Resizes the chart within the window.
        Dimensions should be given as a float between 0 and 1.
        """
        self._width = width if width is not None else self._width
        self._height = height if height is not None else self._height
        self.run_script(f'''
        {self.id}.scale.width = {self._width}
        {self.id}.scale.height = {self._height}
        {self.id}.reSize()
        ''')

    def get_position(self) -> tuple:
        """
        获取当前图表的渲染位置
        :return: (x, y, width, height) 百分比值 (0-1)
        """
        if not self.win.loaded:
            info = self._position_info
            nrows = info['nrows']
            ncols = info['ncols']
            index = info['index']
            row = (index - 1) // ncols
            col = (index - 1) % ncols
            x = col / ncols
            y = row / nrows
            w = self._width / ncols
            h = self._height / nrows
            return (x, y, w, h)
        result = self.win.run_script_and_get(
            f'JSON.stringify({self.id}.getPosition())'
        )
        pos = json.loads(result)
        return (pos['x'], pos['y'], pos['width'], pos['height'])

    def set_position(self, x: Optional[float] = None, y: Optional[float] = None,
                     width: Optional[float] = None, height: Optional[float] = None):
        """
        设置图表的渲染位置
        :param x: 左上角 x 坐标百分比 (0-1)，传入 None 使用默认网格位置
        :param y: 左上角 y 坐标百分比 (0-1)，传入 None 使用默认网格位置
        :param width: 宽度百分比 (0-1)，传入 None 使用默认网格位置 (1.0)
        :param height: 高度百分比 (0-1)，传入 None 使用默认网格位置 (1.0)

        示例:
            chart.set_position(0.0, 0.0, 0.5, 0.5)  # 左上角 50% 区域
            chart.set_position(None, 0.5, 0.5, 0.5)  # x 使用默认，其他自定义
            chart.set_position(None, None, None, None)  # 恢复默认网格位置
        """
        # 验证非 None 参数
        for val, name in [(x, 'x'), (y, 'y'), (width, 'width'), (height, 'height')]:
            if val is not None and not 0 <= val <= 1:
                raise ValueError(f"{name} 必须在 0-1 之间，当前值: {val}")

        # 构建 JS 参数字符串
        def to_js(val):
            return 'null' if val is None else str(val)

        self.run_script(f'{self.id}.setPosition({to_js(x)}, {to_js(y)}, {to_js(width)}, {to_js(height)})')

    def time_scale(self, right_offset: int = 0, min_bar_spacing: float = 0.5,
                   visible: bool = True, time_visible: bool = True, seconds_visible: bool = False,
                   border_visible: bool = True, border_color: Optional[str] = None,
                   right_offset_pixels: int = None,
                   enable_conflation: bool = None,
                   conflation_threshold_factor: float = None,
                   precompute_conflation_on_init: bool = None,
                   precompute_conflation_priority: str = None):
        """
        设置时间轴的显示选项。

        :param right_offset: 右侧偏移的K线数量，默认为 0
        :param min_bar_spacing: 最小K线间距（像素），默认为 0.5
        :param visible: 时间轴是否可见，默认为 True
        :param time_visible: 时间标签是否可见，默认为 True
        :param seconds_visible: 秒数是否显示在时间标签中，默认为 False
        :param border_visible: 时间轴边框是否可见，默认为 True
        :param border_color: 时间轴边框颜色
        :param right_offset_pixels: 右侧像素边距 (v5.0.9+)
        :param enable_conflation: 启用大数据集的数据合并 (v5.1.0+)
        :param conflation_threshold_factor: 调整合并的缩放级别阈值 (v5.1.0+)
        :param precompute_conflation_on_init: 初始化时预计算合并数据 (v5.1.0+)
        :param precompute_conflation_priority: 后台计算优先级 (v5.1.0+)
        """
        self.run_script(f'''{self.id}.chart.applyOptions({{timeScale: {js_json(locals())}}})''')

    def layout(self, background_color: str = '#000000', text_color: Optional[str] = None,
               font_size: Optional[int] = None, font_family: Optional[str] = None):
        """
        设置图表的全局布局选项。

        :param background_color: 图表背景颜色，默认为 '#000000'（黑色）
        :param text_color: 文本颜色，如 '#FFFFFF'（白色）
        :param font_size: 字体大小（像素）
        :param font_family: 字体族，如 'Arial', 'Microsoft YaHei'
        """
        self.run_script(f"""
            document.getElementById('container').style.backgroundColor = '{background_color}'
            {self.id}.chart.applyOptions({{
            layout: {{
                background: {{color: "{background_color}"}},
                {f'textColor: "{text_color}",' if text_color else ''}
                {f'fontSize: {font_size},' if font_size else ''}
                {f'fontFamily: "{font_family}",' if font_family else ''}
            }}}})""")

    def grid(self, vert_enabled: bool = True, horz_enabled: bool = True,
             color: str = 'rgba(29, 30, 38, 5)', style: LINE_STYLE = 'solid'):
        """
        Grid styling for the chart.
        """
        self.run_script(f"""
           {self.id}.chart.applyOptions({{
           grid: {{
               vertLines: {{
                   visible: {jbool(vert_enabled)},
                   color: "{color}",
                   style: {as_enum(style, LINE_STYLE)},
               }},
               horzLines: {{
                   visible: {jbool(horz_enabled)},
                   color: "{color}",
                   style: {as_enum(style, LINE_STYLE)},
               }},
           }}
           }})""")

    def crosshair(
        self,
        mode: CROSSHAIR_MODE = 'normal',
        vert_visible: bool = True,
        vert_width: int = 1,
        vert_color: Optional[str] = None,
        vert_style: LINE_STYLE = 'large_dashed',
        vert_label_background_color: str = 'rgb(46, 46, 46)',
        horz_visible: bool = True,
        horz_width: int = 1,
        horz_color: Optional[str] = None,
        horz_style: LINE_STYLE = 'large_dashed',
        horz_label_background_color: str = 'rgb(55, 55, 55)'
    ):
        """
        Crosshair formatting for its vertical and horizontal axes.
        """
        self.run_script(f'''
        {self.id}.chart.applyOptions({{
            crosshair: {{
                mode: {as_enum(mode, CROSSHAIR_MODE)},
                vertLine: {{
                    visible: {jbool(vert_visible)},
                    width: {vert_width},
                    {f'color: "{vert_color}",' if vert_color else ''}
                    style: {as_enum(vert_style, LINE_STYLE)},
                    labelBackgroundColor: "{vert_label_background_color}"
                }},
                horzLine: {{
                    visible: {jbool(horz_visible)},
                    width: {horz_width},
                    {f'color: "{horz_color}",' if horz_color else ''}
                    style: {as_enum(horz_style, LINE_STYLE)},
                    labelBackgroundColor: "{horz_label_background_color}"
                }}
            }}
        }})''')

    def chart_options(self,
                      hovered_series_on_top: bool = None,
                      default_visible_price_scale_id: Literal['left', 'right'] = None,
                      do_not_snap_to_hidden_series_indices: bool = None):
        """
        Set advanced chart-level options (v5.2.0+).

        :param hovered_series_on_top: Render the currently hovered series
                                      above other series in the same pane.
        :param default_visible_price_scale_id: Which price scale to show
                                               by default ('left'/'right').
        :param do_not_snap_to_hidden_series_indices: When True, the crosshair
                                                     ignores hidden series.
        """
        options = {}
        if hovered_series_on_top is not None:
            options['hoveredSeriesOnTop'] = hovered_series_on_top
        if default_visible_price_scale_id is not None:
            options['defaultVisiblePriceScaleId'] = default_visible_price_scale_id
        if do_not_snap_to_hidden_series_indices is not None:
            options['crosshair'] = {
                'doNotSnapToHiddenSeriesIndices': do_not_snap_to_hidden_series_indices
            }
        if options:
            self.run_script(f'''
                {self.id}.chart.applyOptions({js_json(options)})
            ''')

    def _apply_options(self, options: dict):
        """向 JS 端的 chart.applyOptions() 发送选项字典（内部方法）。

        :param options: 选项字典，键名使用 JS 驼峰格式（如 layout, grid, crosshair）。
                        None 值会被 js_json 自动过滤。
        
        示例::

            chart._apply_options({
                'layout': {'background': {'color': '#000'}},
                'grid': {'vertLines': {'visible': False}},
                'crosshair': {'mode': 0}
            })
        """
        self.run_script(f'{self.id}.chart.applyOptions({js_json(options)})')

    def watermark(self, text: str, font_size: int = 44, color: str = 'rgba(180, 180, 200, 0.5)'):
        """
        Adds a watermark to the chart.
        """
        self.run_script(f'''{self.id}.createWatermark('{text}', {font_size}, '{color}')''')

    def legend(self, visible: bool = False, ohlc: bool = True, percent: bool = False, lines: bool = True,
               color: str = 'rgb(191, 195, 203)', font_size: int = 11, font_family: str = 'Monaco',
               text: str = '', color_based_on_candle: bool = False, persistent: bool = False,
               shorthand: bool = True):
        """
        配置图表的图例显示选项。

        :param visible: 图例是否可见，默认为 False
        :param ohlc: 是否显示 OHLC（开盘/最高/最低/收盘）信息，默认为 True
        :param percent: 是否显示涨跌幅百分比，默认为 False
        :param lines: 是否显示指标线信息，默认为 True
        :param color: 图例文本颜色，默认为 'rgb(191, 195, 203)'
        :param font_size: 字体大小（像素），默认为 11
        :param font_family: 字体族，默认为 'Monaco'
        :param text: 自定义图例文本
        :param color_based_on_candle: 是否根据K线颜色动态改变文本颜色，默认为 False
        :param persistent: 当为 True 时，鼠标离开图表区域后 OHLC 信息保持可见，默认为 False
        :param shorthand: 当为 True 时，成交量和持仓量使用缩写形式（如 24.5K, 1.2M），默认为 True。设为 False 显示完整数字。
        """
        l_id = f'{self.id}.legend'
        if not visible:
            self.run_script(f'''
            {l_id}.div.style.display = "none"
            {l_id}.ohlcEnabled = false
            {l_id}.percentEnabled = false
            {l_id}.linesEnabled = false
            ''')
            return
        self.run_script(f'''
        {l_id}.div.style.display = 'flex'
        {l_id}.ohlcEnabled = {jbool(ohlc)}
        {l_id}.percentEnabled = {jbool(percent)}
        {l_id}.linesEnabled = {jbool(lines)}
        {l_id}.colorBasedOnCandle = {jbool(color_based_on_candle)}
        {l_id}.persistent = {jbool(persistent)}
        {l_id}.shorthand = {jbool(shorthand)}
        {l_id}.div.style.color = '{color}'
        {l_id}.color = '{color}'
        {l_id}.div.style.fontSize = '{font_size}px'
        {l_id}.div.style.fontFamily = '{font_family}'
        {l_id}.text.innerText = '{text}'
        ''')

    def spinner(self, visible):
        """显示或隐藏加载动画。"""
        self.run_script(f"{self.id}.spinner.style.display = '{'block' if visible else 'none'}'")

    def hotkey(self, modifier_key: Literal['ctrl', 'alt', 'shift', 'meta', None],
               keys: Union[str, tuple, int], func: Callable):
        """注册键盘快捷键。
        :param modifier_key: 修饰键（'ctrl'/'alt'/'shift'/'meta'/None）
        :param keys: 按键名或按键名元组
        :param func: 回调函数"""
        if not isinstance(keys, tuple):
            keys = (keys,)
        for key in keys:
            key = str(key)
            if key.isalnum() and len(key) == 1:
                key_code = f'Digit{key}' if key.isdigit() else f'Key{key.upper()}'
                key_condition = f'event.code === "{key_code}"'
            else:
                key_condition = f'event.key === "{key}"'
            if modifier_key is not None:
                key_condition += f'&& event.{modifier_key}Key'

            self.run_script(f'''
                    {self.id}.commandFunctions.unshift((event) => {{
                        if ({key_condition}) {{
                            event.preventDefault()
                            window.callbackFunction(`{modifier_key, keys}_~_{key}`)
                            return true
                        }}
                        else return false
                    }})''')
        self.win.handlers[f'{modifier_key, keys}'] = func

    def create_table(
        self,
        width: NUM,
        height: NUM,
        headings: tuple,
        widths: Optional[tuple] = None,
        alignments: Optional[tuple] = None,
        position: FLOAT = 'left',
        draggable: bool = False,
        background_color: str = '#121417',
        border_color: str = 'rgb(70, 70, 70)',
        border_width: int = 1,
        heading_text_colors: Optional[tuple] = None,
        heading_background_colors: Optional[tuple] = None,
        return_clicked_cells: bool = False,
        func: Optional[Callable] = None
    ) -> Table:
        """
        在图表上创建一个可交互的表格组件，并将其注册到当前图表。

        :param width: 表格宽度。支持三种格式：
            - 整数（如 200）：固定像素宽度
            - 小数（如 0.2）：相对窗口宽度的百分比（0-1）
            - None：自动适应内容宽度
        :param height: 表格高度。支持三种格式：
            - 整数（如 150）：固定像素高度
            - 小数（如 0.3）：相对窗口高度的百分比（0-1）
            - None：自动适应内容高度
        :param headings: 表头列名元组，如 ('Symbol', 'Price', 'Volume')
        :param widths: 各列宽度比例元组，总和应为 1，如 (0.3, 0.35, 0.35)
        :param alignments: 各列对齐方式元组，可选值：'left', 'right', 'center'
        :param position: 表格位置，支持：
            - 'left'：左侧浮动
            - 'right'：右侧浮动
            - 元组 (x, y)：绝对位置，使用百分比坐标（0-1范围），如 (0.7, 0.1)
        :param draggable: 是否可拖动，默认为 False
        :param background_color: 表格背景颜色，默认为 '#121417'
        :param border_color: 边框颜色，默认为 'rgb(70, 70, 70)'
        :param border_width: 边框宽度（像素），默认为 1
        :param heading_text_colors: 表头文字颜色元组，如 ('#FFFFFF', '#FFFFFF', '#FFFFFF')
        :param heading_background_colors: 表头背景颜色元组，如 ('rgba(70, 130, 180, 0.8)',) * 3
        :param return_clicked_cells: 是否返回点击的单元格信息，默认为 False。
            为 True 时，回调函数会接收 (row, column) 参数；否则只接收 row 参数
        :param func: 行点击回调函数，签名为 func(row) 或 func(row, column)（当 return_clicked_cells=True 时）
        :return: Table 实例，可用于添加行、更新单元格数据等操作
        """
        args = locals()
        del args['self']
        tbl = self.win.create_table(*args.values())
        tbl._chart = self
        self._tables.append(tbl)
        # 将表格 div 追加到当前图表的 div 中
        self.run_script(f'{self.id}.div.appendChild({tbl.id}._div)')
        return tbl

    def screenshot(self, add_top_layer: bool = False, include_crosshair: bool = False) -> bytes:
        """
        Takes a screenshot. This method can only be used after the chart window is visible.
        :param add_top_layer: 截图是否包含顶层元素（水印等），v5.2.0+ 新增
        :param include_crosshair: 截图是否包含十字光标，v5.2.0+ 新增
        :return: a bytes object containing a screenshot of the chart.
        """
        options = []
        if add_top_layer:
            options.append('addTopLayer: true')
        if include_crosshair:
            options.append('includeCrosshair: true')
        opts = f'{{{", ".join(options)}}}' if options else ''
        serial_data = self.win.run_script_and_get(f'{self.id}.chart.takeScreenshot({opts}).toDataURL()')
        return b64decode(serial_data.split(',')[1])

    def create_subchart(self, position: Position = 111, width: float = 1.0, height: float = 1.0,
                        sync_id: Optional[Union[str, bool]] = None, scale_candles_only: bool = False,
                        sync_crosshairs_only: bool = False,
                        toolbox: bool = False,
                        autosize: bool = True,
                        pane_index: int = 0,
                        marker_auto_scale: bool = True) -> 'AbstractChart':
        """创建子图表，支持独立缩放或同步十字光标。
        :param position: 子图位置（网格格式或字符串格式，如 111, (2,2,1), 'left'）
        :param width: 宽度比例（相对于网格单元，1.0=占满，<1.0=内缩对齐左上角，>1.0=侵占）
        :param height: 高度比例（相对于网格单元）
        :param sync_id: 同步组名（str/True/False/None），同名组内的图表自动同步
        :param scale_candles_only: 是否仅以 K 线范围缩放
        :param sync_crosshairs_only: 是否仅同步十字光标
        :param toolbox: 是否启用绘图工具箱
        :param autosize: 是否自动调整大小
        :param pane_index: 面板索引
        :param marker_auto_scale: 标记是否自动缩放
        :return: AbstractChart 子图实例"""
        sync_id = self._normalize_sync_id(sync_id)

        chart = self.win.create_subchart(position, width, height, sync_id, scale_candles_only,
                                         sync_crosshairs_only, toolbox, autosize, pane_index,
                                         marker_auto_scale)
        self.subcharts.append(chart.id)
        return chart

    def sync_charts(self, sync_crosshairs_only: bool = False):
        """同步所有子图表的十字光标和时间轴。
        :param sync_crosshairs_only: True 则仅同步十字光标"""
        if (len(self.subcharts) > 1):
            self.run_script(f'''
                Lib.Handler.syncChartsAll
                    ([{', '.join(self.subcharts)}],
                    {'true' if sync_crosshairs_only else 'false'}
                )
            ''', run_last=True)

    def resize_pane(self, pane_index: int, height: int):
        """调整指定面板的高度。
        :param pane_index: 面板索引
        :param height: 目标高度（像素）"""
        self.run_script(f'''
            if ({self.id}.chart.panes().length > {pane_index}) {{
                {self.id}.chart.panes()[{pane_index}].setHeight({height});
            }}
        ''')

    def remove_pane(self, pane_index: int):
        """移除指定索引的面板。"""
        self.run_script(f'''
                    {self.id}.chart.removePane({pane_index});
            ''')
