import json
import os
import warnings
from base64 import b64decode
from datetime import datetime
from typing import Callable, Union, Literal, List, Optional
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
    Position, GridPosition, parse_position
)

current_dir = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(current_dir, 'js', 'index.html')
INDEX_BN = os.path.join(current_dir, 'js', 'index_bn.html')


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
        self._grid_spec: Optional[Tuple[int, int]] = None  # (nrows, ncols)

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
        :param sync_id: 可选的同步目标图表 ID，用于将此子图与指定图表同步时间轴和十字光标
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
        # 如果指定了 sync_id，执行图表同步
        if sync_id:
            self.run_script(f'''
                Lib.Handler.syncCharts(
                    {subchart.id},
                    {sync_id},
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
        if hasattr(chart, '_interval'):
            self._interval = chart._interval
        else:
            self._interval = 1
        self._last_bar = None
        self.name = name
        self.num_decimals = 2
        self.offset = 0
        self.data = pd.DataFrame()
        self.markers = {}
        self.pane_index = pane_index
        self._period_locked = False

    def set_period(self, seconds: Optional[int] = None):
        """
        Locks the chart's time interval to the given value in seconds.
        When locked, set() will skip automatic interval detection,
        using the locked interval for time alignment instead.

        :param seconds: The interval in seconds to lock to, or None to unlock.

        Example::

            chart.set_period(60)       # lock to 1-minute bars
            chart.set_period(300)      # lock to 5-minute bars
            chart.set_period(None)     # unlock, re-enable auto-detection
        """
        if seconds is not None:
            self._interval = seconds
            self._period_locked = True
        else:
            self._period_locked = False

    def pop(self, count: int = 1):
        """从系列末尾移除指定数量的数据点。"""
        self.run_script(f'{self.id}.series.pop({count})')

    def _set_interval(self, df: pd.DataFrame):
        if self._period_locked:
            return

        df = df.copy()
        df.columns = self._format_labels(df, df.columns, df.index, self.name)
        time_df = pd.to_datetime(df['time'], unit='s').dt.tz_localize(None)

        common_interval = time_df.diff().value_counts(sort=True, ascending=False, dropna=True)
        if common_interval.empty:
            raise AssertionError("No common interval found.")

        self._interval = common_interval.index[0].total_seconds()

        units = [
            pd.Timedelta(microseconds=time_df.dt.microsecond.value_counts().index[0]),
            pd.Timedelta(seconds=time_df.dt.second.value_counts().index[0]),
            pd.Timedelta(minutes=time_df.dt.minute.value_counts().index[0]),
            pd.Timedelta(hours=time_df.dt.hour.value_counts().index[0]),
            pd.Timedelta(days=time_df.dt.day.value_counts().index[0]),
        ]
        self.offset = 0
        for value in units:
            value = value.total_seconds()
            if value == 0:
                continue
            elif value >= self._interval:
                break
            self.offset = value
            break

    @staticmethod
    def _format_labels(data, labels, index, exclude_lowercase: Optional[Union[str, list, tuple, set]] = None):
        '''
        格式化列名，将所有列名转换为小写，排除exclude_lowercase中的列名。
        如果有 date 列，就改名为 time 列。
        如果没有 time 列，就用 index 作为 time 列。
        '''
        labels = list(labels)

        if isinstance(exclude_lowercase, str):
            exclude_lowercase = [exclude_lowercase]

        exclude_lowercase = set() if exclude_lowercase is None else set(exclude_lowercase)

        new_labels = []
        for l in labels:
            new_labels.append(l if l in exclude_lowercase else l.lower())

        del labels

        # 不允许 date 和 time 同时出现
        if 'date' in new_labels and 'time' in new_labels:
            raise ValueError("date and time cannot be used at the same time.")

        # 替换 date 到 time，如果有
        new_labels = [l if l != 'date' else 'time' for l in new_labels]

        # 如果没有 time ，就用 index 作为 time 列
        if 'time' not in new_labels:
            data['time'] = index
            new_labels.append('time')

        return new_labels

    def _df_datetime_format(self, df: pd.DataFrame, exclude_lowercase=None, drop_duplicates=False):
        '''
        格式化DataFrame，将所有列名转换为小写，排除exclude_lowercase中的列名。
        如果有 date 列，就改名为 time 列。
        如果没有 time 列，就用 index 作为 time 列。
        :param df: 输入的DataFrame
        :param exclude_lowercase:
        :param set_interval: 是否设置时间间隔，若 _period_locked 为 True 则不生效
        :return:
        '''
        df = df.copy()
        df.columns = self._format_labels(df, df.columns, df.index, exclude_lowercase)
        if df['time'].dtype in (np.int64, np.float64):
            # 如果输入是 np.int64 或 np.float64，则直接认为是 秒级时间戳。
            pass
        else:
            # 转换为时间戳，清除时区信息
            df['time'] = pd.to_datetime(df['time'], unit='s').dt.tz_localize(None)
            # 转换为秒级时间戳，单位是秒，类型是int
            df['time'] = (df['time'] - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')

        # 确保时间值被锁定到最近的bar起点，单位是秒，类型是 np.int64
        df['time'] = (self._interval * (df['time'] // self._interval)).astype(np.int64)
        if drop_duplicates:
            df = df.groupby('time', as_index=False).last()
        return df

    def _series_datetime_format(self, series: pd.Series, exclude_lowercase=None):
        series = series.copy()
        series.index = self._format_labels(series, series.index, series.name, exclude_lowercase)
        series['time'] = self._single_datetime_format(series['time'])
        return series

    def _single_datetime_format(self, arg) -> int:
        if not isinstance(arg, (int, np.int64, float, np.float64)):
            arg = pd.to_datetime(arg, unit='s').tz_localize(None).timestamp()
        # 把时间锁定到最近的bar起点，单位是秒
        arg = int(self._interval * (arg // self._interval) + self.offset)
        return arg

    def set(self, df: Optional[pd.DataFrame] = None, format_cols: bool = True):
        """
        设置或更新系列数据。

        :param df: 包含时间序列数据的 DataFrame，必须包含 'time' 列。
            对于 Line 系列，还需要 'value' 列或与系列同名的列。
            对于 Candlestick 系列，需要 'open', 'high', 'low', 'close' 列。
            如果为 None 或空 DataFrame，则清空数据。
        :param format_cols: 是否自动格式化列（包括日期时间转换），默认为 True
        """
        if df is None or df.empty:
            self.run_script(f'{self.id}.series.setData([])')
            self.data = pd.DataFrame()
            return

        if format_cols:
            self._set_interval(df)
            df = self._df_datetime_format(df, exclude_lowercase=self.name)

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
        series = self._series_datetime_format(series, exclude_lowercase=self.name)
        if self.name in series.index:
            series.rename({self.name: 'value'}, inplace=True)
        if series['time'] == self._last_bar['time']:
            self.data.iloc[-1] = series
        else:
            self.data = pd.concat([self.data, series.to_frame().T], ignore_index=True)
        self._last_bar = self.data.iloc[-1]
        self.run_script(f'{self.id}.series.update({js_data(series)});')

    def _clean_update_batch(self, df: pd.DataFrame, exclude_lowercase=None):
        '''
        通用函数，清理批量更新数据，确保时间是单调递增的，且在 _last_bar 后面。
        :return:
        '''
        if df.empty:
            return df

        # 先直接清理格式
        df = self._df_datetime_format(df, exclude_lowercase=exclude_lowercase)

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
        batch for efficiency.  This mirrors Candlestick.update_bars()
        for Line and Histogram series.

        :param df: DataFrame, must contain a 'time' column plus the
                   series value column(s) (e.g. the line name column
                   or a 'value' column for Histogram).
        """
        if df.empty:
            return

        # 先直接清理格式
        df = self._df_datetime_format(df, exclude_lowercase=self.name)
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

    def _update_markers(self):
        if not self.markers:
            self.run_script(f'{self.id}.seriesMarkers.setMarkers([])')
            return
        str_markers = json.dumps(list(self.markers.values()))
        self.run_script(f'{self.id}.seriesMarkers.setMarkers({str_markers})')

    def marker_list(self, markers: list):
        """
        Creates multiple markers.\n
        :param markers: The list of markers to set. These should be in the format:\n
        [
            {"time": "2021-01-21", "position": "below", "shape": "circle", "color": "#2196F3", "text": ""},
            {"time": "2021-01-22", "position": "below", "shape": "circle", "color": "#2196F3", "text": ""},
            ...
        ]
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
                "text": marker['text'],
                "price": marker.get('price', None),
                "size": marker.get('size', 1),
            }
            marker_ids.append(marker_id)
        self._update_markers()
        return marker_ids

    def _clear_marker_list(self):
        self.markers = {}

    def marker(self, time: Optional[datetime] = None, position: MARKER_POSITION = 'below',
               shape: MARKER_SHAPE = 'arrow_up', color: str = '#2196F3', text: str = ''
               ) -> str:
        """
        Creates a new marker.\n
        :param time: Time location of the marker. If no time is given, it will be placed at the last bar.
        :param position: The position of the marker.
        :param color: The color of the marker (rgb, rgba or hex).
        :param shape: The shape of the marker.
        :param text: The text to be placed with the marker.
        :return: The id of the marker placed.
        """
        try:
            formatted_time = self._last_bar['time'] if not time else self._single_datetime_format(time)
        except TypeError:
            raise TypeError('Chart marker created before data was set.')
        marker_id = self.win._id_gen.generate('Marker_')

        marker_dict = {
            "time": int(formatted_time),
            "position": marker_position(position),
            "color": color,
            "shape": marker_shape(shape),
            "text": text,
        }
        self.markers[marker_id] = marker_dict
        self._update_markers()
        return marker_id

    def remove_marker(self, marker_id: str):
        """
        Removes the marker with the given id.\n
        """
        self.markers.pop(marker_id)
        self._update_markers()

    def horizontal_line(self, price: NUM, color: str = 'rgb(122, 146, 202)', width: int = 2,
                        style: LINE_STYLE = 'solid', text: str = '', axis_label_visible: bool = True,
                        func: Optional[Callable] = None
                        ) -> 'HorizontalLine':
        """
        在指定价格位置创建一条水平线。

        :param price: 水平线所在的价格位置
        :param color: 线条颜色，默认为 'rgb(122, 146, 202)'
        :param width: 线条宽度（像素），默认为 2
        :param style: 线条样式，可选值：'solid', 'dotted', 'dashed', 'large_dashed', 'sparse_dotted'
        :param text: 线条标签文本
        :param axis_label_visible: 是否在坐标轴上显示标签，默认为 True
        :param func: 点击回调函数，签名为 func(price)
        :return: HorizontalLine 实例
        """
        return HorizontalLine(self, price, color, width, style, text, axis_label_visible, func)

    def trend_line(
        self,
        start_time: TIME,
        start_value: NUM,
        end_time: TIME,
        end_value: NUM,
        round: bool = False,
        line_color: str = '#1E80F0',
        width: int = 2,
        style: LINE_STYLE = 'solid',
    ) -> TwoPointDrawing:
        """创建一条趋势线。
        :param start_time: 起点时间
        :param start_value: 起点价格
        :param end_time: 终点时间
        :param end_value: 终点价格
        :param round: 是否取整坐标
        :param line_color: 线条颜色
        :param width: 线宽
        :param style: 线条样式"""
        return TrendLine(*locals().values())

    def box(
        self,
        start_time: TIME,
        start_value: NUM,
        end_time: TIME,
        end_value: NUM,
        round: bool = False,
        color: str = '#1E80F0',
        fill_color: str = 'rgba(255, 255, 255, 0.2)',
        width: int = 2,
        style: LINE_STYLE = 'solid',
    ) -> TwoPointDrawing:
        """创建一个矩形方框。
        :param start_time: 左上角时间
        :param start_value: 左上角价格
        :param end_time: 右下角时间
        :param end_value: 右下角价格
        :param fill_color: 填充色"""
        return Box(*locals().values())

    def ray_line(
        self,
        start_time: TIME,
        value: NUM,
        round: bool = False,
        color: str = '#1E80F0',
        width: int = 2,
        style: LINE_STYLE = 'solid',
        text: str = ''
    ) -> RayLine:
        """创建一条射线（从起点延伸至无穷远）。
        :param start_time: 起点时间
        :param value: 起点价格
        :param text: 标签文本"""
        return RayLine(*locals().values())

    def vertical_line(
        self,
        time: TIME,
        color: str = '#1E80F0',
        width: int = 2,
        style: LINE_STYLE ='solid',
        text: str = ''
    ) -> VerticalLine:
        """创建一条垂直线。
        :param time: 时间位置
        :param text: 标签文本"""
        return VerticalLine(*locals().values())

    def clear_markers(self):
        """
        Clears the markers displayed on the data.\n
        """
        self.markers.clear()
        self._update_markers()

    def create_price_line(self, price: float = 0.0, color: str = 'rgba(214, 237, 255, 0.6)',
            style: LINE_STYLE = 'large_dashed', width: int = 1, price_label: bool = False,
            title: str = '') -> 'PriceLine':
        """
        Creates a horizontal price line on the series.

        Returns a PriceLine object with a delete() method.
        """
        return PriceLine(self, price, color, style, width, price_label, title)

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

    def vertical_span(
        self,
        start_time: Union[TIME, tuple, list],
        end_time: Optional[TIME] = None,
        color: str = 'rgba(252, 219, 3, 0.2)',
        round: bool = False
    ):
        """
        Creates a vertical line or span across the chart.\n
        Start time and end time can be used together, or end_time can be
        omitted and a single time or a list of times can be passed to start_time.
        """
        if round:
            start_time = self._single_datetime_format(start_time)
            end_time = self._single_datetime_format(end_time) if end_time else None
        return VerticalSpan(self, start_time, end_time, color)


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
            )
        null''')

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


class Candlestick(SeriesCommon):
    def __init__(self, chart: 'AbstractChart'):
        super().__init__(chart)
        self._volume_up_color = 'rgba(83,141,131,0.8)'
        self._volume_down_color = 'rgba(200,127,130,0.8)'

        self.candle_data = pd.DataFrame()
        self.candle_column = []

        self._has_volume = False
        self._has_open_interest = False

    def clear_data(self):
        """
        Clears all OHLCV data from the chart without removing the series itself.
        The chart will be empty and ready for new data via set().
        """
        self.run_script(f'{self.id}.series.setData([])')
        self.run_script(f'{self.id}.volumeSeries.setData([])')
        self.run_script(f'{self.id}.openInterestSeries.setData([])')
        self.run_script(f"{self._chart.id}.toolBox?.clearDrawings()")
        self.candle_data = pd.DataFrame()
        self.candle_column = []
        self._last_bar = None
        self._has_volume = self._has_open_interest = False

    def set(self, df: Optional[pd.DataFrame] = None, keep_drawings=False):
        """
        Sets the initial data for the chart.\n
        :param df: columns: date/time, open, high, low, close, volume (if volume enabled), open_interest (if open_interest enabled).
        :param keep_drawings: keeps any drawings made through the toolbox. Otherwise, they will be deleted.
        """
        if df is None or df.empty:
            self.clear_data()
            return

        self._set_interval(df)
        df = self._df_datetime_format(df)

        self._has_volume = 'volume' in df
        self._has_open_interest = 'open_interest' in df

        self.candle_column = ['time', 'open', 'high', 'low', 'close']
        if self._has_volume:
            self.candle_column.append('volume')
        if self._has_open_interest:
            self.candle_column.append('open_interest')

        self.candle_data = df[self.candle_column]
        self._last_bar = df.iloc[-1]

        ohlc_js_data = js_data(self.candle_data[['time', 'open', 'high', 'low', 'close']])
        self.run_script(f'{self.id}.series.setData({ohlc_js_data})')

        if self._has_volume:
            vol_df = df[['time', 'volume']].rename(columns={'volume': 'value'})
            vol_df['color'] = self._volume_down_color
            vol_df.loc[df['close'] > df['open'], 'color'] = self._volume_up_color
            vol_js_data = js_data(vol_df)
            self.run_script(f'{self.id}.volumeSeries.setData({vol_js_data})')

        if self._has_open_interest:
            oi_df = df[['time', 'open_interest']].rename(columns={'open_interest': 'value'})
            oi_js_data = js_data(oi_df)
            self.run_script(f'{self.id}.openInterestSeries.setData({oi_js_data})')

        for line in self._lines:
            if line.name not in df.columns:
                continue
            line.set(df[['time', line.name]], format_cols=False)

        # set autoScale to true in case the user has dragged the price scale
        self.run_script(f'''
            if (!{self.id}.chart.priceScale("right").options.autoScale)
                {self.id}.chart.priceScale("right").applyOptions({{autoScale: true}})
        ''')
        # sync interval to JS for crosshair time formatting
        self.run_script(f'{self._chart.id}._interval = {int(self._interval)}')
        # re-send markers with updated interval alignment to prevent drift
        if self.markers:
            self._update_markers()
        # Note: keep_drawings behavior may vary depending on timing of toolbox initialization
        # The toolBox may not be fully initialized when set() is called early
        if keep_drawings:
            self.run_script(f'{self._chart.id}.toolBox?._drawingTool.repositionOnTime()')
        else:
            self.run_script(f"{self._chart.id}.toolBox?.clearDrawings()")

    def update_bar(self, series: pd.Series):
        '''
        更新单个 bar
        :param series:
        :return:
        '''
        self.update_bars(series.to_frame().T)

    update = update_bar

    def update_from_tick(self, series: pd.Series, cumulative_volume: bool = False):
        """
        使用 tick 更新
        :param series: labels: date/time, price, [volume, open_interest] .
        :param cumulative_volume: Adds the given volume onto the latest bar.
        """
        series = self._series_datetime_format(series)
        # 注意，series 的时间已经锁定到最近的bar起点，所以可安全地进行比较

        if self._last_bar is None:
            raise AssertionError('update_from_tick() must be called after set()')

        if series['time'] < self._last_bar['time']:
            raise ValueError(f'Trying to update tick of time "{pd.to_datetime(series["time"])}", which occurs before the last bar time of "{pd.to_datetime(self._last_bar["time"])}".')

        bar = self._last_bar.copy()
        if series['time'] == self._last_bar['time']:
            bar['high'] = max(self._last_bar['high'], series['price'])
            bar['low'] = min(self._last_bar['low'], series['price'])
            bar['close'] = series['price']

        else:
            for key in ('open', 'high', 'low', 'close'):
                bar[key] = series['price']
            bar['time'] = series['time']

        if self._has_volume:
            if cumulative_volume:
                bar['volume'] += series['volume']
            else:
                bar['volume'] = series['volume']
        if self._has_open_interest:
            bar['open_interest'] = series['open_interest']

        self.update(bar)

    def update_bars(self, df: pd.DataFrame):
        """
        Batch-updates the chart with multiple OHLCV bars at once.

        Processes each row from the DataFrame using the same logic as update(),
        but collects all JavaScript commands into a single batch for efficiency.

        :param df: DataFrame with columns: date/time, open, high, low, close, [volume, open_interest]
        """
        # 丢弃所有比last_bar数据更旧的数据
        df = self._clean_update_batch(df)
        if df.empty:
            return

        if self._last_bar is None or self._last_bar['time'] != df['time'].iloc[-1]:
            is_new_bar = True
        else:
            is_new_bar = False

        if self.candle_data.empty:
            self.candle_data = df
        elif self.candle_data.iloc[-1]['time'] == df['time'].iloc[0]:
            self.candle_data = pd.concat([self.candle_data.iloc[:-1], df], ignore_index=True)
        else:
            self.candle_data = pd.concat([self.candle_data, df], ignore_index=True)

        js_commands = []

        ohlc_df = df[['time', 'open', 'high', 'low', 'close']]
        for _, series in ohlc_df.iterrows():
            js_commands.append(f'{self.id}.series.update({js_data(series)})')

        if self._has_volume:
            assert 'volume' in df.columns, 'DataFrame must contain volume column'
            vol_df = df[['time', 'volume']].rename(columns={'volume': 'value'})
            vol_df['color'] = self._volume_down_color
            vol_df.loc[df['close'] > df['open'], 'color'] = self._volume_up_color
            for _, series in vol_df.iterrows():
                js_commands.append(f'{self.id}.volumeSeries.update({js_data(series)})')

        if self._has_open_interest:
            assert 'open_interest' in df.columns, 'DataFrame must contain open_interest column'
            oi_df = df[['time', 'open_interest']].rename(columns={'open_interest': 'value'})
            for _, series in oi_df.iterrows():
                js_commands.append(f'{self.id}.openInterestSeries.update({js_data(series)})')

        self._last_bar = df.iloc[-1]

        if is_new_bar:
            self._chart.events.new_bar._emit(self)

        # Send all JS commands in one batch
        self.run_script('; '.join(js_commands))

    def update_from_ticks(self, df: pd.DataFrame, cumulative_volume: bool = False):
        """
        Batch-updates the chart from multiple ticks at once.

        Processes each tick row using the same logic as update_from_tick(),
        but collects all JavaScript commands into a single batch for efficiency.

        需要自己组装为多个 bars，然后发给 update_bars进行更新，有点麻烦

        :param df: DataFrame with columns: date/time, price, [volume, open_interest]
        :param cumulative_volume: If True, adds tick volume onto the latest bar's volume.
        """
        if df.empty:
            return

        if self._last_bar is None:
            raise AssertionError('update_from_ticks() must be called after set()')

        df = self._df_datetime_format(df)

        # 使用 pandas 聚合技巧，把 tick 变成 bar
        group_df = df.groupby('time')

        bars = pd.DataFrame({
            'time': list(group_df.groups),
            'open': group_df['price'].first().array,
            'high': group_df['price'].max().array,
            'low': group_df['price'].min().array,
            'close': group_df['price'].last().array,
        })

        vol_df = oi_df = None

        if self._has_volume:
            if cumulative_volume:
                vol_df = group_df['volume'].sum().array
            else:
                vol_df = group_df['volume'].last().array

        if self._has_open_interest:
            oi_df = group_df['open_interest'].last().array

        if self._last_bar['time'] == bars['time'].iloc[0]:
            # 发现同一个bar，更新
            bars.iloc[0, 1] = self._last_bar['open']
            bars.iloc[0, 2] = max(self._last_bar['high'], bars.iloc[0, 2])
            bars.iloc[0, 3] = min(self._last_bar['low'], bars.iloc[0, 3])

            if self._has_volume:
                if cumulative_volume:
                    vol_df.iloc[0] += self._last_bar['volume']
                else:
                    # 无需更新volume，因为volume是单向的
                    pass

            # 无需更新open_interest，因为open_interest是单向的
            # if self._has_open_interest:
            #     pass

        if self._has_volume:
            bars['volume'] = vol_df

        if self._has_open_interest:
            bars['open_interest'] = oi_df

        self.update_bars(bars)

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
                permWidth: {perm_width}
            }})''')

    def set_price_format(self, type: Literal['base', 'custom'] = 'base', base: int = None, precision: int = 2):
        """
        Set the price format for the price scale. The 'base' format avoids floating point precision issues.
        :param type: 'base' or 'custom' (v5.2.0+). Default 'base'.
        :param base: The base value for format 'base'. Required when type='base'.
        :param precision: Number of decimal places. Default 2.
        """
        if type == 'base':
            if base is None:
                raise ValueError("base parameter is required when type='base'")
            options = {'type': 'base', 'base': base, 'precision': precision}
        else:
            options = {'type': type, 'precision': precision}
        self.run_script(f'''
            {self.id}.series.priceScale().applyOptions({{
                priceFormat: {js_json(options)}
            }})
        ''')

    def candle_style(
            self, up_color: str = 'rgba(39, 157, 130, 100)', down_color: str = 'rgba(200, 97, 100, 100)',
            wick_visible: bool = True, border_visible: bool = True, border_up_color: str = '',
            border_down_color: str = '', wick_up_color: str = '', wick_down_color: str = ''):
        """
        Candle styling for each of its parts.\n
        If only `up_color` and `down_color` are passed, they will color all parts of the candle.
        """
        border_up_color = border_up_color if border_up_color else up_color
        border_down_color = border_down_color if border_down_color else down_color
        wick_up_color = wick_up_color if wick_up_color else up_color
        wick_down_color = wick_down_color if wick_down_color else down_color
        self.run_script(f"{self.id}.series.applyOptions({js_json(locals())})")

    def volume_config(self, scale_margin_top: float = 0.8, scale_margin_bottom: float = 0.0,
                      up_color='rgba(83,141,131,0.8)', down_color='rgba(200,127,130,0.8)'):
        """
        Configure volume settings.\n
        Numbers for scaling must be greater than 0 and less than 1.\n
        Volume colors must be applied prior to setting/updating the bars.\n
        """
        self._volume_up_color = up_color if up_color else self._volume_up_color
        self._volume_down_color = down_color if down_color else self._volume_down_color
        self.run_script(f'''
        {self.id}.volumeSeries.priceScale().applyOptions({{
            scaleMargins: {{
                top: {scale_margin_top},
                bottom: {scale_margin_bottom},
            }}
        }})''')

    def open_interest_config(self, scale_margin_top: float = 0.8, scale_margin_bottom: float = 0.0):
        """
        Configure open interest settings.

        Numbers for scaling must be greater than 0 and less than 1.
        """
        self.run_script(f'''
        {self.id}.openInterestSeries.priceScale().applyOptions({{
            scaleMargins: {{
                top: {scale_margin_top},
                bottom: {scale_margin_bottom},
            }}
        }})''')


class AbstractChart(Candlestick, Pane):

    def __init__(self, window: Window, width: float = 1.0, height: float = 1.0,
                 scale_candles_only: bool = False, toolbox: bool = False,
                 autosize: bool = True, position: Position = 111, pane_index:int = 0, marker_auto_scale: bool = True
                 ):
        Pane.__init__(self, window)

        self._lines = []
        self.subcharts = []
        self._drawings = []
        self._tables = []
        self._price_lines: List['PriceLine'] = []
        self._scale_candles_only = scale_candles_only
        self._width = width
        self._height = height
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

        Candlestick.__init__(self, self)
        self.subcharts.append(self.id)

        self.topbar: TopBar = TopBar(self)
        if toolbox:
            self.toolbox: ToolBox = ToolBox(self)

    def fit(self):
        """
        Fits the maximum amount of the chart data within the viewport.
        """
        self.run_script(f'{self.id}.chart.timeScale().fitContent()')

    def clear_handlers(self):
        """
        Clears all registered event/message handlers in the Window.
        Use this when resetting a chart to prevent handler accumulation
        in long-running embedded applications.
        """
        self.win.handlers.clear()

    def reset(self):
        """
        Resets the chart to a clean initial state without destroying the WebView.

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
            {subchart_id}.chart.remove();
            {subchart_id}.wrapper.remove();
            var _hid = Lib.Handler._all.findIndex(function(h) {{ return h.id === "{subchart_id}" }});
            if (_hid >= 0) Lib.Handler._all.splice(_hid, 1);
            delete {subchart_id};
        ''')

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
                'has_data': not self.candle_data.empty,
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
        for mid, m in self.markers.items():
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
        return self._lines[-1]

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

    def lines(self) -> List[Line]:
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
        self.run_script(f'''{self._chart.id}.createWatermark('{text}', {font_size}, '{color}')''')

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
                        sync: Optional[Union[str, bool]] = None, scale_candles_only: bool = False,
                        sync_crosshairs_only: bool = False,
                        toolbox: bool = False,
                        autosize: bool = True,
                        pane_index: int = 0,
                        marker_auto_scale: bool = True) -> 'AbstractChart':
        """创建子图表，支持独立缩放或同步十字光标。
        :param position: 子图位置（网格格式或字符串格式，如 111, (2,2,1), 'left'）
        :param width: 宽度比例（相对于网格单元，1.0=占满，<1.0=内缩对齐左上角，>1.0=侵占）
        :param height: 高度比例（相对于网格单元）
        :param sync: 同步 ID 或 True（使用当前图表 ID）
        :param scale_candles_only: 是否仅以 K 线范围缩放
        :param sync_crosshairs_only: 是否仅同步十字光标
        :param toolbox: 是否启用绘图工具箱
        :param autosize: 是否自动调整大小
        :param pane_index: 面板索引
        :param marker_auto_scale: 标记是否自动缩放
        :return: AbstractChart 子图实例"""
        if sync is True:
            sync = self.id
        chart = self.win.create_subchart(position, width, height, sync, scale_candles_only,
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
