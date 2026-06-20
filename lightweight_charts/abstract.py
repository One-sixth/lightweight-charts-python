import json
import os
import warnings
from base64 import b64decode
from datetime import datetime
from typing import Callable, Union, Literal, Optional
import pandas as pd
import time as _time
import tomllib
import numpy as np

from .table import Table
from .toolbox import ToolBox
from .drawings import Box, HorizontalLine, RayLine, TrendLine, TwoPointDrawing, VerticalLine, VerticalSpan
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
            while not self.run_script_and_get('document.readyState == "complete"'):
                continue    # scary, but works

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
        # 获取当前图表数量（用于字符串格式转换）
        chart_count = len(self.handlers) + 1

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


class SeriesCommon(Pane):
    """图表的系列数据基类，管理数据更新、标记、绘图和价格线。"""
    def __init__(self, chart: 'AbstractChart', name: str = '', pane_index: int = 0):
        """
        :param chart: 所属的 AbstractChart 实例
        :param name: 系列名称（用于图例标识）
        :param pane_index: 所属面板索引"""
        super().__init__(chart.win)
        self._chart = chart
        self._last_bar = None
        self.name = name
        self.num_decimals = 2
        self.data = pd.DataFrame()
        self.markers = {}
        self.pane_index = pane_index

    def pop(self, count: int = 1):
        """从系列末尾移除指定数量的数据点。"""
        self.run_script(f'{self.id}.series.pop({count})')

    def _get_df_interval_offset(self, df: pd.DataFrame) -> (int, int):
        """获取数据DF内时间点的通常间隔（秒），返回，时间间隔（秒）和偏移时间（秒）"""
        return get_df_interval_offset(df)

    @staticmethod
    def _normal_df(df: pd.DataFrame, exclude_lowercase: Optional[Union[str, list, tuple, set]] = None) -> pd.DataFrame:
        '''标准化输入DF'''
        return normal_df(df, exclude_lowercase)

    def _time_to_bar_time(self, data: int | float | pd.Series | pd.DataFrame) -> int | float | pd.Series | pd.DataFrame:
        """将时间戳转换为bar时间戳（委托到所属图表的时间级别）。"""
        return self._chart._time_to_bar_time(data)

    def _merge_value_by_time(self, df: pd.DataFrame) -> pd.DataFrame:
        """合并同样时间戳的bar"""
        return merge_value_by_time(df)

    def _single_datetime_format(self, arg) -> int:
        """格式化单个时间值（委托到所属图表的时间级别）。"""
        return self._chart._single_datetime_format(arg)

    def set(self, df: Optional[pd.DataFrame] = None):
        """
        设置或更新系列数据。

        :param df: 包含时间序列数据的 DataFrame，需要包含 'time' 列 或 'date' 列，否则使用 'index' 作为 ‘time’ 列。
            对于 Line 系列，还需要 'value' 列或与系列同名的列。
            对于 CandleSeries 系列，需要 'open', 'high', 'low', 'close' 列。
            如果为 None 或空 DataFrame，则清空数据。
        """
        # 重置系列
        self.run_script(f"{self.id}.series.setData([])")
        self.data = pd.DataFrame()

        if df is None or df.empty:
            return

        # 检查时间级别是否已初始化
        if self._chart._interval is None:
            raise RuntimeError(
                f"时间级别未初始化。请先调用 chart.set(df) 或 chart.set_period(seconds)。"
            )

        df = self._normal_df(df, exclude_lowercase=self.name)
        df = self._time_to_bar_time(df)
        df = self._merge_value_by_time(df)

        if self.name:
            if self.name not in df:
                raise NameError(f'No column named "{self.name}".')
            df = df.rename(columns={self.name: 'value'})

        self.data = df.copy()
        self._last_bar = df.iloc[-1]
        self.run_script(f'{self.id}.series.setData({js_data(df)}); ')
        if self.markers:
            self._update_markers()

    def update(self, series: pd.Series):
        """
        更新系列的最后一个数据点或添加新数据点。

        :param series: 包含单个数据点的 Series，必须包含 'time' 索引。
            如果时间与最后一个数据点相同，则更新该数据点；否则添加为新数据点。
        :raises AssertionError: 如果尚未调用 set() 设置初始数据
        """
        if self._last_bar is None:
            raise AssertionError("set() must be called first.")
        self.update_batch(series.to_frame().T)

    def _clean_update_batch(self, df: pd.DataFrame, exclude_lowercase=None):
        '''
        通用函数，清理批量更新数据，确保时间是单调递增的，且在 _last_bar 后面。
        :return:
        '''
        if df.empty:
            return df

        # 先直接清理格式
        df = self._normal_df(df, exclude_lowercase=exclude_lowercase)
        df = self._time_to_bar_time(df)
        df = self._merge_value_by_time(df)

        # 确保时间是单调递增
        if len(df) > 1:
            if not df['time'].is_monotonic_increasing:
                raise ValueError("Time column must be monotonic increasing.")

        # 确保时间都在 _last_bar 后面
        if self._last_bar is not None:
            mask = df['time'] >= self._last_bar['time']
            df = df[mask]
            n_drop = len(mask) - mask.sum()
            if n_drop > 0:
                print(f'Warning! Drop {n_drop} lines because early than _last_bar.')

        return df

    def update_batch(self, df: pd.DataFrame):
        """
        Batch-updates the series with multiple data points at once.

        Processes each row from the DataFrame using the same logic as
        update(), but collects all JavaScript commands into a single
        batch for efficiency.  This mirrors CandleSeries.update_batch()
        for Line and Histogram series.

        :param df: DataFrame, must contain a 'time' column plus the
                   series value column(s) (e.g. the line name column
                   or a 'value' column for Histogram).
        """
        if df.empty:
            return

        # 先直接清理格式
        df = self._clean_update_batch(df, exclude_lowercase=self.name)
        df.rename(columns={self.name: 'value'}, inplace=True)
        # 取出有效数据
        df = df[['time', 'value']]

        # 确保时间是单调递增
        if len(df) > 1:
            if not df['time'].is_monotonic_increasing:
                raise ValueError("Time column must be monotonic increasing.")

        # 确保时间都在 _last_bar 后面
        if self._last_bar is not None:
            mask = df['time'] >= self._last_bar['time']
            df = df[mask]
            n_drop = len(mask) - mask.sum()
            if n_drop > 0:
                print(f'Warning! Drop {n_drop} lines because early than _last_bar.')

            if df.empty:
                return

        # 生成 js 命令
        js_commands = []
        for _, row in df.iterrows():
            js_commands.append(f'{self.id}.series.update({js_data(row)});')

        if self.data is None or self.data.empty:
            # 如果数据为空，则直接设置新数据
            self.data = df
        elif self.data['time'].iloc[-1] == df['time'].iloc[0]:
            # 如果最后一个时间点和第一个时间点相同，则去除原数据的最后一个点，合并新数据
            self.data = pd.concat([self.data.iloc[:-1], df], ignore_index=True)
        else:
            # 如果最后一个时间点和第一个时间点不同，则直接合并新数据
            self.data = pd.concat([self.data, df], ignore_index=True)

        self._last_bar = df.iloc[-1]

        # 一次性执行
        self.run_script(' '.join(js_commands))

    def price_scale(
        self,
        auto_scale: bool = True,
        mode: PRICE_SCALE_MODE = 'normal',
        invert_scale: bool = False,
        align_labels: bool = True,
        scale_margin_top: float = 0.2,
        scale_margin_bottom: float = 0.2,
        border_visible: bool = False,
        border_color: Optional[str] = None,
        text_color: Optional[str] = None,
        entire_text_only: bool = False,
        visible: bool = True,
        ticks_visible: bool = False,
        tick_mark_density: float = None,
        minimum_width: int = 0,
        perm_width: int = 0
    ):
        """配置价格坐标轴的外观与行为。"""
        self.run_script(f'''
            {self.id}.series.priceScale().applyOptions({{
                autoScale: {jbool(auto_scale)},
                mode: {as_enum(mode, PRICE_SCALE_MODE)},
                invertScale: {jbool(invert_scale)},
                alignLabels: {jbool(align_labels)},
                scaleMargins: {{top: {scale_margin_top}, bottom: {scale_margin_bottom}}},
                borderVisible: {jbool(border_visible)},
                {f'borderColor: "{border_color}",' if border_color else ''}
                {f'textColor: "{text_color}",' if text_color else ''}
                entireTextOnly: {jbool(entire_text_only)},
                visible: {jbool(visible)},
                ticksVisible: {jbool(ticks_visible)},
                {f'tickMarkDensity: {tick_mark_density},' if tick_mark_density is not None else ''}
                minimumWidth: {minimum_width},
                {f'permWidth: {perm_width},' if perm_width else ''}
            }})''')

    def update_from_tick(self, series: pd.Series):
        """
        使用单个 tick 更新图表。
        :param series: 包含 time 和 value 的 Series
        """
        self.update_from_ticks(series.to_frame().T)

    def update_from_ticks(self, df: pd.DataFrame):
        """
        批量使用 tick 更新图表，内部自动按时间分片取 last 值。

        通用版本：按 time 分组，取每组最后一条数据的 value。
        CandleSeries 会覆盖此方法，实现 OHLC 聚合。

        :param df: DataFrame，需要 time 列和 value 列（或与系列同名的列）
        """
        if df.empty:
            return

        if self._last_bar is None:
            raise AssertionError('update_from_ticks() must be called after set()')

        df = self._normal_df(df, exclude_lowercase=self.name)
        df = self._time_to_bar_time(df)

        # 确定值列名
        value_col = self.name if self.name and self.name in df.columns else 'value'
        if value_col not in df.columns:
            raise ValueError(f"DataFrame 缺少值列 '{value_col}'")

        # 按时间分组，取每组最后一条
        group_df = df.groupby('time')
        bars = pd.DataFrame({
            'time': list(group_df.groups),
            value_col: group_df[value_col].last().array,
        })

        self.update_batch(bars)

    def _update_markers(self):
        if not self.markers:
            self.run_script(f'''
                if ({self.id}.seriesMarkers) {self.id}.seriesMarkers.setMarkers([]);
            ''')
            return
        str_markers = json.dumps(list(self.markers.values()))
        self.run_script(f'''
            try {{
                if (!{self.id}.seriesMarkers) {{
                    {self.id}.seriesMarkers = LightweightCharts.createSeriesMarkers(
                        {self.id}.series, [], {{autoScale: true}}
                    );
                }}
                {self.id}.seriesMarkers.setMarkers({str_markers});
            }} catch(e) {{
                console.error('setMarkers failed:', e.message);
            }}
        ''')

    def marker_list(self, markers: list[dict]):
        """
        Creates multiple markers.

        :param markers: The list of markers to set. Format::

            [
                {"time": "2021-01-21", "position": "below", "shape": "circle", "color": "#2196F3", "text": "", "size": 1},
                {"time": "2021-01-22", "position": "above", "shape": "arrow_down", "color": "#F44336", "text": "sell"},
            ]

        支持的字段: time(必须), position(必须), shape(必须), color(必须), text(可选), size(可选, 默认1)
        :return: a list of marker ids.
        """
        markers = markers.copy()
        marker_ids = []
        for marker in markers:
            marker_id = self.win._id_gen.generate('Marker_')
            self.markers[marker_id] = {
                "time": self._single_datetime_format(marker['time']),
                "position": marker_position(marker['position']),
                "color": marker['color'],
                "shape": marker_shape(marker['shape']),
                "text": marker.get('text', ''),
                "size": marker.get('size', 1),
            }
            marker_ids.append(marker_id)
        self._update_markers()
        return marker_ids

    def marker(self, time: Optional[datetime] = None, position: MARKER_POSITION = 'below',
               shape: MARKER_SHAPE = 'arrow_up', color: str = '#2196F3', text: str = '',
               size: int = 1
               ) -> str:
        """
        Creates a new marker.

        :param time: Time location of the marker. If no time is given, it will be placed at the last bar.
        :param position: The position of the marker ('above', 'below', 'inside').
        :param shape: The shape of the marker ('arrow_up', 'arrow_down', 'circle', 'square').
        :param color: The color of the marker (rgb, rgba or hex).
        :param text: The text to be placed with the marker.
        :param size: The size of the marker (default 1).
        :return: The id of the marker placed.
        """
        if self._last_bar is None:
            raise ValueError('Chart marker created before data was set.')

        formatted_time = self._last_bar['time'] if not time else self._single_datetime_format(time)
        marker_id = self.win._id_gen.generate('Marker_')

        marker_dict = {
            "time": int(formatted_time),
            "position": marker_position(position),
            "color": color,
            "shape": marker_shape(shape),
            "text": text,
            "size": size,
        }
        self.markers[marker_id] = marker_dict
        self._update_markers()
        return marker_id

    def remove_marker(self, marker_id: str):
        """
        Removes the marker with the given id.
        """
        self.markers.pop(marker_id)
        self._update_markers()

    def clear_markers(self, _dont_update: bool = False):
        """
        Clears the markers displayed on the data.\n
        """
        self.markers.clear()
        if not _dont_update:
            self._update_markers()

    def precision(self, precision: int):
        """
        Sets the precision and minMove.\n
        :param precision: The number of decimal places.
        """
        min_move = 1 / (10**precision)
        self.run_script(f'''
        {self.id}.precision = {precision}
        {self.id}.series.applyOptions({{
            priceFormat: {{precision: {precision}, minMove: {min_move}}}
        }})''')
        self.num_decimals = precision

    def hide_data(self):
        """隐藏当前系列的数据（K 线、成交量、持仓量）。"""
        self._toggle_data(False)

    def show_data(self):
        """显示当前系列的数据。"""
        self._toggle_data(True)

    def _toggle_data(self, arg):
        self.run_script(f'''
        {self.id}.series.applyOptions({{visible: {jbool(arg)}}});
        if ('volumeSeries' in {self.id}) {self.id}.volumeSeries.applyOptions({{visible: {jbool(arg)}}});
        if ('openInterestSeries' in {self.id}) {self.id}.openInterestSeries.applyOptions({{visible: {jbool(arg)}}});
        ''')


class PriceLine(Pane):
    """
    A price line drawn on the series (created via create_price_line).

    Use .delete() to remove it.
    """

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
        """
        Removes the price line from the series.
        """
        self._chart._price_lines.remove(self) if self in self._chart._price_lines else None
        self.run_script(f'''
        {self._chart.id}.series.removePriceLine({self.id})
        delete {self.id}
        ''')

    def update(self, price: Optional[float] = None, color: Optional[str] = None,
               style: Optional[str] = None, width: Optional[int] = None,
               title: Optional[str] = None):
        """
        Updates the price line options.
        """
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


class Line(SeriesCommon):
    """折线系列，用于绘制折线图。"""
    def __init__(self, chart, name, color, style, width, price_line, price_label, price_scale_id=None,
                 crosshair_marker=True, pane_index: int = 0,
    ):

        super().__init__(chart, name, pane_index)
        self.color = color

        self.run_script(f'''
            {self.id} = {self._chart.id}.createLineSeries(
                "{name}",
                {{
                    color: '{color}',
                    lineStyle: {as_enum(style, LINE_STYLE)},
                    lineWidth: {width},
                    lastValueVisible: {jbool(price_label)},
                    priceLineVisible: {jbool(price_line)},
                    crosshairMarkerVisible: {jbool(crosshair_marker)},
                    priceScaleId: {f'"{price_scale_id}"' if price_scale_id else 'undefined'},
                    {"""autoscaleInfoProvider: () => ({
                            priceRange: {
                                minValue: 1_000_000_000,
                                maxValue: 0,
                            },
                        }),
                    """ if chart._scale_candles_only else ''}
                }},
                {pane_index}
            );null''')  # 后面的 null 是为了防止 JS 异常，必不可少

    def delete(self):
        """
        Irreversibly deletes the line, as well as the object that contains the line.
        """
        self._chart._lines.remove(self) if self in self._chart._lines else None
        self.run_script(f'''
            {self._chart.id}.chart.removeSeries({self.id}.series)
            var _idx = {self._chart.id}._seriesList.indexOf({self.id}.series); if (_idx >= 0) {self._chart.id}._seriesList.splice(_idx, 1)

            {self.id}legendItem = {self._chart.id}.legend._lines.find((line) => line.series == {self.id}.series)
            {self._chart.id}.legend._lines = {self._chart.id}.legend._lines.filter((item) => item != {self.id}legendItem)
            try {{ if ({self.id}legendItem) {self._chart.id}.legend.div.removeChild({self.id}legendItem.row) }} catch(e) {{}}

            delete {self.id}legendItem
            delete {self.id}
        ''')


class Histogram(SeriesCommon):
    """柱状图系列，常用于成交量或持仓量展示。"""
    def __init__(self, chart, name, color, price_line, price_label, scale_margin_top, scale_margin_bottom,
                 pane_index: int = 0
    ):
        super().__init__(chart, name, pane_index)
        self.color = color
        self.run_script(f'''
        {self.id} = {chart.id}.createHistogramSeries(
            "{name}",
            {{
                color: '{color}',
                lastValueVisible: {jbool(price_label)},
                priceLineVisible: {jbool(price_line)},
                priceScaleId: {'undefined'},
                priceFormat: {{type: "volume"}},
            }},
            {pane_index}
        )
        {self.id}.series.priceScale().applyOptions({{
            scaleMargins: {{top:{scale_margin_top}, bottom: {scale_margin_bottom}}}
        }});0''')

    def delete(self):
        """
        Irreversibly deletes the histogram.
        """
        self._chart._lines.remove(self) if self in self._chart._lines else None
        self.run_script(f'''
            {self._chart.id}.chart.removeSeries({self.id}.series)
            var _idx = {self._chart.id}._seriesList.indexOf({self.id}.series); if (_idx >= 0) {self._chart.id}._seriesList.splice(_idx, 1)

            {self.id}legendItem = {self._chart.id}.legend._lines.find((line) => line.series == {self.id}.series)
            {self._chart.id}.legend._lines = {self._chart.id}.legend._lines.filter((item) => item != {self.id}legendItem)
            try {{ if ({self.id}legendItem) {self._chart.id}.legend.div.removeChild({self.id}legendItem.row) }} catch(e) {{}}

            delete {self.id}legendItem
            delete {self.id}
        ''')

    def scale(self, scale_margin_top: float = 0.0, scale_margin_bottom: float = 0.0):
        """调整柱状图的 Y 轴边距。"""
        self.run_script(f'''
        {self.id}.series.priceScale().applyOptions({{
            scaleMargins: {{top: {scale_margin_top}, bottom: {scale_margin_bottom}}}
        }})''')


class VolumeSeries(SeriesCommon):
    """成交量柱状图，绑定到 CandleSeries，自动根据 K 线涨跌着色。

    通常通过 ``CandleSeries.attach_volume()`` 或 ``AbstractChart.attach_volume()``
    创建，也可以独立创建后手动 ``set()``。

    用法示例::

        # 通过 chart 自动 attach（set 检测到 volume 列时自动创建）
        chart.set(df_with_volume)

        # 手动 attach
        vol = chart.attach_volume(up_color='green', down_color='red')
        vol.set(df)

        # 独立配置
        vol.config(scale_margin_top=0.7)

        # 删除
        vol.delete()
    """

    def __init__(self, candle: 'CandleSeries', pane_index: int = None,
                 up_color: str = 'rgba(83,141,131,0.8)',
                 down_color: str = 'rgba(200,127,130,0.8)',
                 scale_margin_top: float = 0.8,
                 scale_margin_bottom: float = 0.0,
                 price_scale_id: str = 'volume_scale',
                 _wrap_existing: bool = False):
        """
        :param candle: 绑定的 CandleSeries 实例，用于获取 OHLC 着色
        :param pane_index: 面板索引，None 则跟随 candle 的 pane_index
        :param up_color: 上涨颜色（close > open）
        :param down_color: 下跌颜色（close <= open）
        :param scale_margin_top: 价格轴顶部边距（0-1）
        :param scale_margin_bottom: 价格轴底部边距（0-1）
        :param price_scale_id: 价格尺度 ID，相同 ID 的 series 共享价格尺度。默认 'volume_scale'
        :param _wrap_existing: 内部参数，True 时包装 Handler 已有的 volumeSeries（不创建新 JS 对象）
        """
        pane = pane_index if pane_index is not None else candle.pane_index
        super().__init__(candle._chart, name='', pane_index=pane)
        self._candle = candle
        self._up_color = up_color
        self._down_color = down_color
        self._wrap_existing = _wrap_existing

        if _wrap_existing:
            # 包装模式：复用 Handler 已有的 volumeSeries，不创建新 JS 对象
            # self.id 已由 Pane.__init__ 自动生成，我们需要指向 Handler 的 volumeSeries
            # 创建一个轻量包装对象
            self.run_script(f'''
                {self.id} = {{}};
                {self.id}.series = {candle.id}.volumeSeries;
            ;0''')
        else:
            # 独立模式：创建新的 HistogramSeries
            self.run_script(f'''
                {self.id} = {self._chart.id}.createHistogramSeries(
                    "",
                    {{
                        color: '{down_color}',
                        lastValueVisible: false,
                        priceLineVisible: false,
                        priceScaleId: '{price_scale_id}',
                        priceFormat: {{type: "volume"}},
                    }},
                    {pane}
                )
                {self.id}.series.priceScale().applyOptions({{
                    scaleMargins: {{top: {scale_margin_top}, bottom: {scale_margin_bottom}}}
                }});0''')

    def set(self, df: pd.DataFrame):
        """设置成交量数据。自动根据绑定的 candle 的 OHLC 着色。

        :param df: DataFrame，需要包含 time 和 volume 列。如果包含 open/close 列则自动着色。
        """
        if df is None or df.empty:
            self.run_script(f'{self.id}.series.setData([])')
            return

        if 'volume' not in df.columns:
            return

        df = self._candle._normal_df(df)
        df = self._chart._time_to_bar_time(df)

        vol_df = df[['time', 'volume']].rename(columns={'volume': 'value'})

        # 根据 OHLC 着色
        if 'open' in df.columns and 'close' in df.columns:
            vol_df['color'] = self._down_color
            vol_df.loc[df['close'] > df['open'], 'color'] = self._up_color
        else:
            vol_df['color'] = self._down_color

        self.run_script(f'{self.id}.series.setData({js_data(vol_df)})')

    def update(self, series: pd.Series):
        """更新最新一根 bar 的成交量或追加新 bar。

        :param series: 包含 time, volume 的 Series（可选 open, close 用于着色）
        """
        self.update_batch(series.to_frame().T)

    def update_batch(self, df: pd.DataFrame):
        """批量更新成交量。

        :param df: DataFrame，需要包含 time 和 volume 列
        """
        if df is None or df.empty:
            return

        df = self._candle._normal_df(df)
        df = self._chart._time_to_bar_time(df)

        if 'volume' not in df.columns:
            return

        vol_df = df[['time', 'volume']].rename(columns={'volume': 'value'})

        if 'open' in df.columns and 'close' in df.columns:
            vol_df['color'] = self._down_color
            vol_df.loc[df['close'] > df['open'], 'color'] = self._up_color
        else:
            vol_df['color'] = self._down_color

        js_commands = []
        for _, row in vol_df.iterrows():
            js_commands.append(f'{self.id}.series.update({js_data(row)})')
        self.run_script('; '.join(js_commands))

    def config(self, scale_margin_top: float = None, scale_margin_bottom: float = None,
               up_color: str = None, down_color: str = None):
        """配置成交量样式。

        :param scale_margin_top: 价格轴顶部边距
        :param scale_margin_bottom: 价格轴底部边距
        :param up_color: 上涨颜色
        :param down_color: 下跌颜色
        """
        if up_color is not None:
            self._up_color = up_color
        if down_color is not None:
            self._down_color = down_color
        if scale_margin_top is not None or scale_margin_bottom is not None:
            top = scale_margin_top if scale_margin_top is not None else 0.8
            bottom = scale_margin_bottom if scale_margin_bottom is not None else 0.0
            self.run_script(f'''
                {self.id}.series.priceScale().applyOptions({{
                    scaleMargins: {{top: {top}, bottom: {bottom}}}
                }})''')

    def delete(self):
        """删除成交量系列。不影响绑定的 CandleSeries。"""
        self.run_script(f'''
            {self._chart.id}.chart.removeSeries({self.id}.series)
            var _idx = {self._chart.id}._seriesList.indexOf({self.id}.series);
            if (_idx >= 0) {self._chart.id}._seriesList.splice(_idx, 1);
            var _legendItem = {self._chart.id}.legend._lines.find(l => l.series == {self.id}.series);
            if (_legendItem) {{
                {self._chart.id}.legend._lines = {self._chart.id}.legend._lines.filter(l => l != _legendItem);
                try {{ {self._chart.id}.legend.div.removeChild(_legendItem.row) }} catch(e) {{}}
            }}
            delete {self.id}
        ''')

    def _toggle_data(self, arg):
        """显示/隐藏成交量系列。"""
        self.run_script(f'{self.id}.series.applyOptions({{visible: {jbool(arg)}}})')


class OpenInterestSeries(SeriesCommon):
    """持仓量折线，绑定到 CandleSeries。

    通常通过 ``CandleSeries.attach_open_interest()`` 或
    ``AbstractChart.attach_open_interest()`` 创建。

    用法示例::

        oi = chart.attach_open_interest(color='#F5A623')
        oi.set(df)
        oi.config(color='#FF6600')
        oi.delete()
    """

    def __init__(self, candle: 'CandleSeries', pane_index: int = None,
                 color: str = '#F5A623',
                 line_width: int = 1,
                 scale_margin_top: float = 0.8,
                 scale_margin_bottom: float = 0.0,
                 price_scale_id: str = 'oi_scale',
                 _wrap_existing: bool = False):
        """
        :param candle: 绑定的 CandleSeries 实例
        :param pane_index: 面板索引，None 则跟随 candle
        :param color: 线条颜色
        :param line_width: 线宽
        :param scale_margin_top: 价格轴顶部边距
        :param scale_margin_bottom: 价格轴底部边距
        :param price_scale_id: 价格尺度 ID，相同 ID 的 series 共享价格尺度。默认 'oi_scale'
        :param _wrap_existing: 内部参数，True 时包装 Handler 已有的 openInterestSeries
        """
        pane = pane_index if pane_index is not None else candle.pane_index
        super().__init__(candle._chart, name='', pane_index=pane)
        self._candle = candle
        self._color = color
        self._wrap_existing = _wrap_existing

        if _wrap_existing:
            self.run_script(f'''
                {self.id} = {{}};
                {self.id}.series = {candle.id}.openInterestSeries;
            ;0''')
        else:
            self.run_script(f'''
                {self.id} = {self._chart.id}.createLineSeries(
                    "",
                    {{
                        color: '{color}',
                        lineWidth: {line_width},
                        priceScaleId: '{price_scale_id}',
                        lastValueVisible: false,
                        priceLineVisible: false,
                        crosshairMarkerVisible: true,
                    }},
                    {pane}
                )
                {self.id}.series.priceScale().applyOptions({{
                    scaleMargins: {{top: {scale_margin_top}, bottom: {scale_margin_bottom}}},
                    autoScale: true,
                }});0''')

    def set(self, df: pd.DataFrame):
        """设置持仓量数据。

        :param df: DataFrame，需要包含 time 和 open_interest 列
        """
        if df is None or df.empty:
            self.run_script(f'{self.id}.series.setData([])')
            return

        if 'open_interest' not in df.columns:
            return

        df = self._candle._normal_df(df)
        df = self._chart._time_to_bar_time(df)

        oi_df = df[['time', 'open_interest']].rename(columns={'open_interest': 'value'})
        self.run_script(f'{self.id}.series.setData({js_data(oi_df)})')

    def update(self, series: pd.Series):
        """更新最新一根 bar 的持仓量或追加新 bar。"""
        self.update_batch(series.to_frame().T)

    def update_batch(self, df: pd.DataFrame):
        """批量更新持仓量。"""
        if df is None or df.empty:
            return

        df = self._candle._normal_df(df)
        df = self._chart._time_to_bar_time(df)

        if 'open_interest' not in df.columns:
            return

        oi_df = df[['time', 'open_interest']].rename(columns={'open_interest': 'value'})
        js_commands = []
        for _, row in oi_df.iterrows():
            js_commands.append(f'{self.id}.series.update({js_data(row)})')
        self.run_script('; '.join(js_commands))

    def config(self, color: str = None, line_width: int = None,
               scale_margin_top: float = None, scale_margin_bottom: float = None):
        """配置持仓量样式。"""
        opts = {}
        if color is not None:
            opts['color'] = color
            self._color = color
        if line_width is not None:
            opts['lineWidth'] = line_width
        if opts:
            self.run_script(f'{self.id}.series.applyOptions({js_json(opts)})')
        if scale_margin_top is not None or scale_margin_bottom is not None:
            top = scale_margin_top if scale_margin_top is not None else 0.8
            bottom = scale_margin_bottom if scale_margin_bottom is not None else 0.0
            self.run_script(f'''
                {self.id}.series.priceScale().applyOptions({{
                    scaleMargins: {{top: {top}, bottom: {bottom}}},
                    autoScale: true,
                }})''')

    def delete(self):
        """删除持仓量系列。"""
        self.run_script(f'''
            {self._chart.id}.chart.removeSeries({self.id}.series)
            var _idx = {self._chart.id}._seriesList.indexOf({self.id}.series);
            if (_idx >= 0) {self._chart.id}._seriesList.splice(_idx, 1);
            var _legendItem = {self._chart.id}.legend._lines.find(l => l.series == {self.id}.series);
            if (_legendItem) {{
                {self._chart.id}.legend._lines = {self._chart.id}.legend._lines.filter(l => l != _legendItem);
                try {{ {self._chart.id}.legend.div.removeChild(_legendItem.row) }} catch(e) {{}}
            }}
            delete {self.id}
        ''')

    def _toggle_data(self, arg):
        """显示/隐藏持仓量系列。"""
        self.run_script(f'{self.id}.series.applyOptions({{visible: {jbool(arg)}}})')


class CandleSeries(SeriesCommon):
    """独立K线系列，可在任意 pane 上绘制 OHLC 数据，无 volume/open interest。

    适用于参考K线、对比K线等场景，支持 set/update/update_batch 动态更新。

    用法示例::

        chart = Chart(width=1200, height=800)
        chart.set(df_main)  # 主K线 pane 0

        ref = chart.create_candle_series(name='参考K线', pane_index=1)
        ref.set(df_reference)  # 初始数据

        ref.update(new_bar)        # 更新最新 bar 或追加新 bar
        ref.update_batch(df_more)  # 批量追加
    """

    def __init__(self, chart, name: str = '', pane_index: int = 0,
                 up_color: str = 'rgba(39, 157, 130, 100)',
                 down_color: str = 'rgba(200, 97, 100, 100)',
                 border_visible: bool = True, wick_visible: bool = True,
                 price_line: bool = False, price_label: bool = True,
                 price_scale_id: Optional[str] = None,
                 crosshair_marker: bool = True):
        super().__init__(chart, name, pane_index)
        self.candle_data = pd.DataFrame()
        self._has_volume = False
        self._has_open_interest = False
        self._attached: list = []  # 附属 series（VolumeSeries, OpenInterestSeries）

        border_up_color = up_color
        border_down_color = down_color
        wick_up_color = up_color
        wick_down_color = down_color

        self.run_script(f'''
            {self.id} = {chart.id}.createCandleSeries(
                "{name}",
                {{
                    upColor: '{up_color}',
                    downColor: '{down_color}',
                    borderUpColor: '{border_up_color}',
                    borderDownColor: '{border_down_color}',
                    wickUpColor: '{wick_up_color}',
                    wickDownColor: '{wick_down_color}',
                    borderVisible: {jbool(border_visible)},
                    wickVisible: {jbool(wick_visible)},
                    lastValueVisible: {jbool(price_label)},
                    priceLineVisible: {jbool(price_line)},
                    crosshairMarkerVisible: {jbool(crosshair_marker)},
                    priceScaleId: {f'"{price_scale_id}"' if price_scale_id else 'undefined'},
                }},
                {pane_index}
            );0''')

    @classmethod
    def _wrap_handler(cls, chart: 'AbstractChart') -> 'CandleSeries':
        """创建包装 Handler 主 series 的 CandleSeries（不创建新 JS 对象）。

        用于组合模式：AbstractChart 通过此方法创建 self.candle，
        共享 Handler 的 JS 对象引用（self.candle.id == chart.id）。
        """
        obj = cls.__new__(cls)
        Pane.__init__(obj, chart.win)
        obj._chart = chart
        obj.id = chart.id  # 共享 Handler JS 对象
        obj.name = ''
        obj.pane_index = 0
        obj._last_bar = None
        obj.data = pd.DataFrame()
        obj.candle_data = pd.DataFrame()
        obj._has_volume = False
        obj._has_open_interest = False
        obj._attached = []
        obj.markers = {}
        obj.num_decimals = 2
        return obj

    def clear_data(self):
        """清空所有 K 线数据（candle + volume + OI）。

        _wrap_existing 的附属 series 只清数据不删除（它们是 Handler 的固有组件），
        非 _wrap_existing 的附属 series 完全删除（它们是独立创建的 JS 对象）。
        """
        self.run_script(f'{self.id}.series.setData([])')
        self.candle_data = pd.DataFrame()
        self.data = pd.DataFrame()
        self._last_bar = None
        for attached in list(self._attached):
            if getattr(attached, '_wrap_existing', False):
                # 只清数据，不删除 JS 对象
                self.run_script(f'{attached.id}.series.setData([])')
            else:
                # 独立创建的 series，完全删除
                attached.delete()
                self._attached.remove(attached)
        self._has_volume = any(isinstance(a, VolumeSeries) for a in self._attached)
        self._has_open_interest = any(isinstance(a, OpenInterestSeries) for a in self._attached)

    def attach_volume(self, **kwargs) -> 'VolumeSeries':
        """创建并绑定成交量系列。

        主图表（_wrap_handler 模式）复用 Handler 已有的 volumeSeries，
        独立 CandleSeries 创建新的 HistogramSeries。

        :return: VolumeSeries 实例
        """
        # 检测是否为主图表（id 与 chart.id 相同 → _wrap_handler 模式）
        is_main = (self.id == self._chart.id)
        vol = VolumeSeries(self, _wrap_existing=is_main, **kwargs)
        self._attached.append(vol)
        self._has_volume = True
        return vol

    def attach_open_interest(self, **kwargs) -> 'OpenInterestSeries':
        """创建并绑定持仓量系列。

        主图表复用 Handler 已有的 openInterestSeries，
        独立 CandleSeries 创建新的 LineSeries。

        :return: OpenInterestSeries 实例
        """
        is_main = (self.id == self._chart.id)
        oi = OpenInterestSeries(self, _wrap_existing=is_main, **kwargs)
        self._attached.append(oi)
        self._has_open_interest = True
        return oi

    def set(self, df: Optional[pd.DataFrame] = None, keep_drawings=False):
        """
        设置 K 线初始数据。

        :param df: DataFrame，必须包含 time/date 列和 open, high, low, close 列。
            如果包含 volume 列且未 attach VolumeSeries，会自动创建。
            如果包含 open_interest 列且未 attach OpenInterestSeries，会自动创建。
            如果为 None 或空 DataFrame，则清空数据。
        """
        self.run_script(f"{self.id}.series.setData([])")
        self.data = pd.DataFrame()
        self.candle_data = pd.DataFrame()

        if df is None or df.empty:
            return

        df = self._normal_df(df)
        df = self._time_to_bar_time(df)
        df = self._merge_value_by_time(df)

        required = ['open', 'high', 'low', 'close']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"DataFrame 缺少必需列: {missing}")

        ohlc = df[['time', 'open', 'high', 'low', 'close']]
        self.candle_data = ohlc.copy()
        self.data = ohlc.copy()
        self._last_bar = ohlc.iloc[-1]

        ohlc_js_data = js_data(ohlc)
        self.run_script(f'{self.id}.series.setData({ohlc_js_data}); ')

        # 检测并自动 attach volume/OI
        if 'volume' in df.columns and not any(isinstance(a, VolumeSeries) for a in self._attached):
            self.attach_volume()
        if 'open_interest' in df.columns and not any(isinstance(a, OpenInterestSeries) for a in self._attached):
            self.attach_open_interest()

        # 转发数据给附属 series
        for attached in self._attached:
            if isinstance(attached, VolumeSeries):
                attached.set(df)
            elif isinstance(attached, OpenInterestSeries):
                attached.set(df)

        if self.markers:
            self._update_markers()

    def update(self, series: pd.Series):
        """
        更新最新一根 bar 或追加新 bar。

        :param series: 包含 time, open, high, low, close 的 Series。
            若 time 与最后一根相同则更新，否则追加。
        :raises AssertionError: 如果尚未调用 set() 设置初始数据
        """
        if self._last_bar is None:
            raise AssertionError("set() must be called first.")
        self.update_batch(series.to_frame().T)

    def update_batch(self, df: pd.DataFrame):
        """
        批量更新多根 K 线。

        :param df: DataFrame，必须包含 time/date 列和 open, high, low, close 列。
        """
        if df.empty:
            return

        df = self._normal_df(df)
        df = self._time_to_bar_time(df)
        df = self._merge_value_by_time(df)

        required = ['open', 'high', 'low', 'close']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"DataFrame 缺少必需列: {missing}")

        ohlc = df[['time', 'open', 'high', 'low', 'close']]

        if len(ohlc) > 1 and not ohlc['time'].is_monotonic_increasing:
            raise ValueError("Time column must be monotonic increasing.")

        if self._last_bar is not None:
            mask = ohlc['time'] >= self._last_bar['time']
            ohlc = ohlc[mask]
            n_drop = len(mask) - mask.sum()
            if n_drop > 0:
                print(f'Warning! Drop {n_drop} lines because earlier than _last_bar.')
            if ohlc.empty:
                return

        js_commands = []
        for _, row in ohlc.iterrows():
            js_commands.append(f'{self.id}.series.update({js_data(row)});')

        if self.candle_data.empty:
            self.candle_data = ohlc
        elif self.candle_data.iloc[-1]['time'] == ohlc.iloc[0]['time']:
            self.candle_data = pd.concat([self.candle_data.iloc[:-1], ohlc], ignore_index=True)
        else:
            self.candle_data = pd.concat([self.candle_data, ohlc], ignore_index=True)

        self.data = self.candle_data.copy()
        self._last_bar = ohlc.iloc[-1]

        self.run_script(' '.join(js_commands))

        # 转发给附属 series
        for attached in self._attached:
            if isinstance(attached, VolumeSeries) and 'volume' in df.columns:
                attached.update_batch(df)
            elif isinstance(attached, OpenInterestSeries) and 'open_interest' in df.columns:
                attached.update_batch(df)

    def delete(self):
        """删除此 K 线系列及其附属 series（volume/OI）。"""
        # 先删除附属 series（VolumeSeries / OpenInterestSeries）
        for attached in list(self._attached):
            attached.delete()
        self._attached.clear()
        self._has_volume = False
        self._has_open_interest = False

        # 再删除自身
        self._chart._lines.remove(self) if self in self._chart._lines else None
        self.run_script(f'''
            {self._chart.id}.chart.removeSeries({self.id}.series)
            var _idx = {self._chart.id}._seriesList.indexOf({self.id}.series); if (_idx >= 0) {self._chart.id}._seriesList.splice(_idx, 1)

            {self.id}legendItem = {self._chart.id}.legend._lines.find((line) => line.series == {self.id}.series)
            {self._chart.id}.legend._lines = {self._chart.id}.legend._lines.filter((item) => item != {self.id}legendItem)
            try {{ if ({self.id}legendItem) {self._chart.id}.legend.div.removeChild({self.id}legendItem.row) }} catch(e) {{}}

            delete {self.id}legendItem
            delete {self.id}
        ''')

    def _toggle_data(self, arg):
        """显示/隐藏 K 线及其附属 series（volume/OI）。"""
        self.run_script(f'{self.id}.series.applyOptions({{visible: {jbool(arg)}}})')
        for attached in self._attached:
            attached._toggle_data(arg)

    def candle_style(
            self, up_color: str = 'rgba(39, 157, 130, 100)', down_color: str = 'rgba(200, 97, 100, 100)',
            wick_visible: bool = True, border_visible: bool = True, border_up_color: str = '',
            border_down_color: str = '', wick_up_color: str = '', wick_down_color: str = ''):
        """
        Candle styling for each of its parts.
        If only `up_color` and `down_color` are passed, they will color all parts of the candle.
        """
        border_up_color = border_up_color if border_up_color else up_color
        border_down_color = border_down_color if border_down_color else down_color
        wick_up_color = wick_up_color if wick_up_color else up_color
        wick_down_color = wick_down_color if wick_down_color else down_color
        self.run_script(f"{self.id}.series.applyOptions({js_json(locals())})")

    def volume_config(self, scale_margin_top: float = 0.8, scale_margin_bottom: float = 0.0,
                      up_color=None, down_color=None):
        """
        Configure volume settings.
        Numbers for scaling must be greater than 0 and less than 1.
        Volume colors must be applied prior to setting/updating the bars.
        """
        vol = next((a for a in self._attached if isinstance(a, VolumeSeries)), None)
        if vol:
            vol.config(scale_margin_top=scale_margin_top, scale_margin_bottom=scale_margin_bottom,
                       up_color=up_color, down_color=down_color)

    def open_interest_config(self, scale_margin_top: float = 0.8, scale_margin_bottom: float = 0.0,
                             color=None):
        """
        Configure open interest settings.
        Numbers for scaling must be greater than 0 and less than 1.
        """
        oi = next((a for a in self._attached if isinstance(a, OpenInterestSeries)), None)
        if oi:
            oi.config(scale_margin_top=scale_margin_top, scale_margin_bottom=scale_margin_bottom,
                      color=color)

    def price_scale(
        self,
        auto_scale: bool = True,
        mode: PRICE_SCALE_MODE = 'normal',
        invert_scale: bool = False,
        align_labels: bool = True,
        scale_margin_top: float = 0.2,
        scale_margin_bottom: float = 0.2,
        border_visible: bool = False,
        border_color: Optional[str] = None,
        text_color: Optional[str] = None,
        entire_text_only: bool = False,
        visible: bool = True,
        ticks_visible: bool = False,
        tick_mark_density: float = None,
        minimum_width: int = 0,
        perm_width: int = 0
    ):
        """配置价格坐标轴的外观与行为。"""
        self.run_script(f'''
            {self.id}.series.priceScale().applyOptions({{
                autoScale: {jbool(auto_scale)},
                mode: {as_enum(mode, PRICE_SCALE_MODE)},
                invertScale: {jbool(invert_scale)},
                alignLabels: {jbool(align_labels)},
                scaleMargins: {{top: {scale_margin_top}, bottom: {scale_margin_bottom}}},
                borderVisible: {jbool(border_visible)},
                {f'borderColor: "{border_color}",' if border_color else ''}
                {f'textColor: "{text_color}",' if text_color else ''}
                entireTextOnly: {jbool(entire_text_only)},
                visible: {jbool(visible)},
                ticksVisible: {jbool(ticks_visible)},
                {f'tickMarkDensity: {tick_mark_density},' if tick_mark_density is not None else ''}
                minimumWidth: {minimum_width},
                {f'permWidth: {perm_width},' if perm_width else ''}
            }})''')

    def update_from_tick(self, series: pd.Series, cumulative_volume: bool = False):
        """
        使用单个 tick 更新图表。
        :param series: labels: date/time, price, [volume, open_interest]
        :param cumulative_volume: 是否累加成交量
        """
        self.update_from_ticks(series.to_frame().T, cumulative_volume=cumulative_volume)

    def update_from_ticks(self, df: pd.DataFrame, cumulative_volume: bool = False):
        """
        批量使用 tick 更新图表，内部自动聚合成 bar。

        :param df: DataFrame with columns: date/time, price, [volume, open_interest]
        :param cumulative_volume: If True, adds tick volume onto the latest bar's volume.
        """
        if df.empty:
            return

        if self._last_bar is None:
            raise AssertionError('update_from_ticks() must be called after set()')

        df = self._normal_df(df)
        df = self._time_to_bar_time(df)

        group_df = df.groupby('time')

        bars = pd.DataFrame({
            'time': list(group_df.groups),
            'open': group_df['price'].first().array,
            'high': group_df['price'].max().array,
            'low': group_df['price'].min().array,
            'close': group_df['price'].last().array,
        })

        # 检测 volume/OI
        has_vol = 'volume' in df.columns
        has_oi = 'open_interest' in df.columns

        vol_series = None
        oi_series = None

        if has_vol:
            if cumulative_volume:
                vol_series = group_df['volume'].sum().array
            else:
                vol_series = group_df['volume'].last().array

        if has_oi:
            oi_series = group_df['open_interest'].last().array

        if self._last_bar['time'] == bars['time'].iloc[0]:
            bars.iloc[0, 1] = self._last_bar['open']
            bars.iloc[0, 2] = max(self._last_bar['high'], bars.iloc[0, 2])
            bars.iloc[0, 3] = min(self._last_bar['low'], bars.iloc[0, 3])

            if has_vol and cumulative_volume:
                vol_series.iloc[0] += self._last_bar.get('volume', 0)

        if has_vol:
            bars['volume'] = vol_series
        if has_oi:
            bars['open_interest'] = oi_series

        self.update_batch(bars)


class AbstractChart(Pane):
    """图表容器——管理所有序列和工具组件，自身不是任何 Series。

    采用组合模式：self.candle (CandleSeries) 管理 K 线数据，
    self.volume (VolumeSeries) / self.oi (OpenInterestSeries) 可选挂载。
    所有 CandleSeries 方法通过委托保持向后兼容。
    """

    def __init__(self, window: Window, width: float = 1.0, height: float = 1.0,
                 scale_candles_only: bool = False, toolbox: bool = False,
                 autosize: bool = True, position: Position = 111, pane_index:int = 0, marker_auto_scale: bool = True
                 ):
        Pane.__init__(self, window)

        self._lines = []
        self.subcharts = []
        self._drawings = []
        self._tables = []
        self._price_lines: list['PriceLine'] = []
        self._scale_candles_only = scale_candles_only
        self._width = width
        self._height = height
        self._is_subchart = False  # 由 create_subchart() 设为 True
        # 时间级别（图表级，所有 series 共享）
        self._interval = None       # None = 未初始化，需先调 set() 或 set_period()
        self.offset = 0
        self._period_locked = False
        self.events: Events = Events(self)

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
        self._html_chart_init = (
            f'{self.id} = new Lib.Handler('
            f'"{self.id}", {width}, {height}, '
            f'{self._position_info["nrows"]}, {self._position_info["ncols"]}, {self._position_info["index"]}, '
            f'{jbool(autosize)}, {pane_index}, {jbool(marker_auto_scale)})'
        )
        self.run_script(self._html_chart_init + ';0')

        # ── 组合模式：主 K 线作为 CandleSeries 包装 Handler ──
        self.candle = CandleSeries._wrap_handler(self)
        # volume 和 oi 默认创建（复用 Handler 已有的 JS series）
        self.volume: 'VolumeSeries' = self.candle.attach_volume()
        self.oi: 'OpenInterestSeries' = self.candle.attach_open_interest()

        self.subcharts.append(self.id)

        self.topbar: TopBar = TopBar(self)
        if toolbox:
            self.toolbox: ToolBox = ToolBox(self)

    # ═══════════════════════════════════════════════════════
    #  委托方法 — 向后兼容 chart.set() / chart.update() 等 API
    # ═══════════════════════════════════════════════════════

    # ── CandleSeries 属性代理 ──

    @property
    def candle_data(self):
        """K 线数据 DataFrame。"""
        return self.candle.candle_data

    @property
    def data(self):
        """系列数据 DataFrame。"""
        return self.candle.data

    @property
    def markers(self):
        """标记字典。"""
        return self.candle.markers

    @property
    def _last_bar(self):
        """最后一根 bar 的数据。"""
        return self.candle._last_bar

    # ── 时间级别方法（图表级，不再委托到 candle）──

    def _set_interval(self, df: pd.DataFrame):
        """根据数据时间点，智能地设置时间间隔。"""
        if self._period_locked:
            return
        self._interval, self.offset = get_df_interval_offset(df)

    def _time_to_bar_time(self, data):
        """将时间戳对齐到 bar 时间边界。"""
        if self._interval is None:
            raise RuntimeError("时间级别未初始化，请先调用 chart.set() 或 chart.set_period()。")
        return time_to_bar_time(data, self.offset, self._interval)

    def _single_datetime_format(self, arg) -> int:
        """格式化单个时间值为秒级时间戳。"""
        if self._interval is None:
            raise RuntimeError("时间级别未初始化，请先调用 chart.set() 或 chart.set_period()。")
        if not isinstance(arg, (int, np.int64, float, np.float64)):
            arg = (pd.to_datetime(arg, unit='s').tz_localize(None) - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')
        return int(self._time_to_bar_time(arg))

    def _normal_df(self, df, exclude_lowercase=None):
        """标准化 DataFrame。"""
        return normal_df(df, exclude_lowercase)

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

        # 更新所有附属系列的时间间隔
        for line in self._lines:
            pass  # 附属系列通过 self._chart 访问，无需单独设置

    # ── 高频数据方法（显式委托，IDE 友好）──

    def set(self, df=None, keep_drawings=False):
        """设置 K 线数据。自动检测 volume/OI 列并转发数据。"""
        if df is not None and not df.empty:
            df = self._normal_df(df)
            self._set_interval(df)
        return self.candle.set(df, keep_drawings)

    def update(self, series):
        """更新最新一根 bar 或追加新 bar。"""
        return self.candle.update(series)

    update_bar = property(lambda self: self.candle.update)

    def update_batch(self, df):
        """批量更新多根 K 线。"""
        return self.candle.update_batch(df)

    update_bars = property(lambda self: self.candle.update_batch)  # backward-compatible alias

    def update_from_tick(self, series, cumulative_volume=False):
        """使用单个 tick 更新图表。"""
        return self.candle.update_from_tick(series, cumulative_volume)

    def update_from_ticks(self, df, cumulative_volume=False):
        """批量使用 tick 更新图表。"""
        return self.candle.update_from_ticks(df, cumulative_volume)

    def clear_data(self):
        """清空所有 K 线数据。"""
        return self.candle.clear_data()

    # ── 附属 series 管理 ──

    def attach_volume(self, **kwargs) -> 'VolumeSeries':
        """创建并绑定成交量系列。

        :return: VolumeSeries 实例
        """
        vol = self.candle.attach_volume(**kwargs)
        self.volume = vol
        return vol

    def attach_open_interest(self, **kwargs) -> 'OpenInterestSeries':
        """创建并绑定持仓量系列。

        :return: OpenInterestSeries 实例
        """
        oi = self.candle.attach_open_interest(**kwargs)
        self.oi = oi
        return oi

    # ── 标记方法（显式委托）──

    def marker(self, time=None, position='below', shape='arrow_up', color='#2196F3', text='', size=1):
        """创建标记。"""
        return self.candle.marker(time=time, position=position, shape=shape, color=color, text=text, size=size)

    def remove_marker(self, marker_id):
        """移除标记。"""
        return self.candle.remove_marker(marker_id)

    def marker_list(self, marker_list):
        """批量创建标记。"""
        return self.candle.marker_list(marker_list)

    def clear_markers(self, _dont_update: bool = False):
        """清空所有标记。"""
        return self.candle.clear_markers(_dont_update)

    # ── 样式配置（显式委托）──

    def candle_style(self, **kwargs):
        """配置 K 线样式。"""
        return self.candle.candle_style(**kwargs)

    def volume_config(self, **kwargs):
        """配置成交量样式。"""
        return self.candle.volume_config(**kwargs)

    def open_interest_config(self, **kwargs):
        """配置持仓量样式。"""
        return self.candle.open_interest_config(**kwargs)

    def price_scale(self, **kwargs):
        """配置价格坐标轴。"""
        return self.candle.price_scale(**kwargs)

    def set_price_format(self, **kwargs):
        """设置价格格式。"""
        return self.candle.set_price_format(**kwargs)

    # ── 绘图方法（直接在 AbstractChart 上创建，不委托到 candle）──
    # Drawing 构造函数需要 chart 参数来注册到 chart._drawings，
    # 所以必须传 self（AbstractChart）而非 self.candle。

    def horizontal_line(self, price, color='rgb(122, 146, 202)', width=2,
                        style='solid', text='', axis_label_visible=True, func=None):
        """创建水平线。"""
        return HorizontalLine(self, price, color, width, style, text, axis_label_visible, func)

    def trend_line(self, start_time, start_value, end_time, end_value,
                   round=False, line_color='#1E80F0', width=2, style='solid'):
        """创建趋势线。"""
        return TrendLine(self, start_time, start_value, end_time, end_value, round, line_color, width, style)

    def ray_line(self, start_time, value, round=False, color='#1E80F0', width=2, style='solid', text=''):
        """创建射线。"""
        return RayLine(self, start_time, value, round, color, width, style, text)

    def vertical_line(self, time, color='#1E80F0', width=2, style='solid', text=''):
        """创建垂直线。"""
        return VerticalLine(self, time, color, width, style, text)

    def vertical_span(self, start_time, end_time=None, color='rgba(252, 219, 3, 0.2)', round=False):
        """创建垂直区间。"""
        if round:
            start_time = self.candle._single_datetime_format(start_time)
            end_time = self.candle._single_datetime_format(end_time) if end_time else None
        return VerticalSpan(self, start_time, end_time, color)

    def box(self, start_time, start_value, end_time, end_value,
            round=False, color='#1E80F0', fill_color='rgba(255, 255, 255, 0.2)', width=2, style='solid'):
        """创建矩形。"""
        return Box(self, start_time, start_value, end_time, end_value, round, color, fill_color, width, style)

    # ── 其他委托 ──

    def create_price_line(self, price=0.0, color='rgba(214, 237, 255, 0.6)',
                          style='large_dashed', width=1, price_label=False, title=''):
        """创建价格线。"""
        return PriceLine(self, price, color, style, width, price_label, title)

    def precision(self, precision=2):
        """设置精度。"""
        return self.candle.precision(precision)

    def pop(self, count=1):
        """从末尾移除数据点。"""
        return self.candle.pop(count)

    def hide_data(self):
        """隐藏数据。"""
        return self.candle.hide_data()

    def show_data(self):
        """显示数据。"""
        return self.candle.show_data()

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

    def clear_handlers(self):
        """
        Clears all registered event/message handlers in the Window.
        Only available on the main chart (not subcharts).
        """
        if self._is_subchart:
            raise RuntimeError("clear_handlers() 只能在主图表上调用，不能在子图上调用。")
        self.win.handlers.clear()

    def reset(self):
        """
        Resets the chart to a clean initial state without destroying the WebView.
        Only available on the main chart (not subcharts).

        Performs:
        1. Clears all OHLCV data (candle + volume series)
        2. Deletes all extra Line and Histogram series
        3. Clears all price markers
        4. Clears all toolbox drawings (JS + Python)
        5. Resets the subcharts list
        6. Clears event handlers to prevent accumulation

        After reset(), the chart is ready for new data via set().
        TopBar widgets and styling options are preserved.
        """
        if self._is_subchart:
            raise RuntimeError("reset() 只能在主图表上调用。子图请使用 reset_sub()。")
        self.clear_data()
        for line in list(self._lines):
            line.delete()
        self.clear_markers()
        self.run_script(f'if ({self.id}.toolBox) {self.id}.toolBox.clearDrawings()')
        if hasattr(self, 'toolbox'):
            self.toolbox.drawings.clear()
        # clean up subcharts (skip the main chart itself)
        for sub_id in list(self.subcharts):
            if sub_id != self.id:
                self.remove_subchart(sub_id)
        self.subcharts = [self.id]
        self.clear_handlers()

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
        """
        # 1. K线/成交量/持仓量数据
        self.clear_data()

        # 2. Line/Histogram 系列
        for line in list(self._lines):
            line.delete()

        # 3. PriceLine
        for pl in list(self._price_lines):
            pl.delete()

        # 4. 标记
        self.clear_markers()

        # 5. 绘图
        for d in list(self._drawings):
            d.delete()

        # 6. 表格
        for t in list(self._tables):
            t.delete()

        # 7. ToolBox 清理
        # 注意: 必须先移除 handler，再调用 JS cleanup。
        # 因为 JS _cleanup() → clearDrawings() → saveDrawings() 会向 Python
        # 发送 save_drawings 回调。如果先调 _cleanup()，回调会排队，之后移除 handler
        # 时消息已经在队列里，show_async() 处理到时 handler 已不在 → KeyError。
        # 先移除 handler 后，排队的消息到达时找不到 handler，被 try/except 静默忽略。
        if hasattr(self, 'toolbox'):
            self.win.handlers.pop(f'save_drawings{self.id}', None)
            self.toolbox._cleanup()

        # 8. TopBar 清理
        if hasattr(self, 'topbar') and self.topbar._created:
            for widget in list(self.topbar._widgets.values()):
                self.win.handlers.pop(widget.id, None)
            self.topbar._widgets.clear()
            self.run_script(f'{self.id}._topBar?._div.remove()')

        # 9. Legend 清理
        self.run_script(f'{self.id}.legend.cleanup()')

        # 10. Events 清理（JSEmitter）
        self._cleanup_events()

        # 11. syncCharts 双向解关联 + 重建
        self._unsync_all()

        # 12. handlers 清理（salt 匹配）
        self._remove_my_handlers()

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
                'has_data': not self.candle.candle_data.empty,
                'subchart_ids': [s for s in self.subcharts if s != self.id],
            },
            'lines': [],
            'price_lines': [],
            'markers': [],
            'subcharts': [],
            'tables': [],
            'drawings': [],
        }

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
        for d in self._drawings:
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
            pane_index: int = 0
    ) -> Line:
        """
        创建并返回一个折线图对象。

        :param name: 线图名称，用于图例显示
        :param color: 线条颜色，支持 CSS 颜色格式，如 'rgba(214, 237, 255, 0.6)'
        :param style: 线条样式，可选值：'solid', 'dotted', 'dashed', 'large_dashed', 'sparse_dotted'
        :param width: 线条宽度（像素），默认为 2
        :param price_line: 是否显示价格线（在图表右侧显示当前价格）
        :param price_label: 是否显示价格标签
        :param price_scale_id: 价格刻度ID，用于共享刻度
        :param pane_index: 面板索引，用于在多个面板中放置
        :return: Line 实例
        """
        line = Line(self, name, color, style, width, price_line, price_label, price_scale_id, pane_index=pane_index)
        self._lines.append(line)
        return line

    def create_histogram(
            self, name: str = '', color: str = 'rgba(214, 237, 255, 0.6)',
            price_line: bool = True, price_label: bool = True,
            scale_margin_top: float = 0.0, scale_margin_bottom: float = 0.0,
            pane_index: int = 0,
    ) -> Histogram:
        """
        创建并返回一个柱状图（直方图）对象，通常用于显示成交量。

        :param name: 柱状图名称，用于图例显示
        :param color: 柱状图颜色，支持 CSS 颜色格式
        :param price_line: 是否显示价格线
        :param price_label: 是否显示价格标签
        :param scale_margin_top: 顶部刻度边距（0-1），默认为 0.0
        :param scale_margin_bottom: 底部刻度边距（0-1），默认为 0.0
        :param pane_index: 面板索引，用于在多个面板中放置
        :return: Histogram 实例
        """
        hist = Histogram(self, name, color, price_line, price_label, scale_margin_top, scale_margin_bottom, pane_index)
        self._lines.append(hist)
        return hist

    def create_candle_series(
            self, name: str = '', pane_index: int = 0,
            up_color: str = 'rgba(39, 157, 130, 100)',
            down_color: str = 'rgba(200, 97, 100, 100)',
            border_visible: bool = True, wick_visible: bool = True,
            price_line: bool = False, price_label: bool = True,
            price_scale_id: Optional[str] = None,
            crosshair_marker: bool = True
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
        :return: CandleSeries 实例
        """
        candle = CandleSeries(
            self, name, pane_index,
            up_color=up_color, down_color=down_color,
            border_visible=border_visible, wick_visible=wick_visible,
            price_line=price_line, price_label=price_label,
            price_scale_id=price_scale_id, crosshair_marker=crosshair_marker,
        )
        self._lines.append(candle)
        return candle

    def lines(self) -> list[Line]:
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
