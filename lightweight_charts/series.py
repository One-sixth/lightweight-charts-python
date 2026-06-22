import json
from datetime import datetime
from typing import Optional, TYPE_CHECKING
import pandas as pd

from .util import (
    Pane, as_enum, jbool, js_json, TIME, NUM, FLOAT,
    LINE_STYLE, MARKER_POSITION, MARKER_SHAPE,
    PRICE_SCALE_MODE, marker_position, marker_shape, js_data,
    normal_df, merge_value_by_time, get_df_interval_offset, time_to_bar_time
)


if TYPE_CHECKING:
    # 类型检查时专用，不会在运行时导入
    from .abstract import AbstractChart


class SeriesCommon(Pane):
    """图表的系列数据基类，管理数据更新、标记、绘图和价格线。"""
    def __init__(self, chart: 'AbstractChart', name: str = '', pane_index: int = 0, _fixed_id: str = None):
        """
        :param chart: 所属的 AbstractChart 实例
        :param name: 系列名称（用于图例标识）
        :param pane_index: 所属面板索引
        :param _fixed_id: 固定 ID（如 'window.Chart_1_candle'），跳过 IDGen 自动生成
        """
        if _fixed_id:
            self.id = _fixed_id
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

    def delete(self):
        """删除此系列（清除标记、移除 JS 对象、清理图例）。"""
        self.clear_markers()

        if self in self._chart._lines:
            self._chart._lines.remove(self)

        self.run_script(f'''
            {self._chart.id}.chart.removeSeries({self.id}.series);
            var _idx = {self._chart.id}._seriesList.indexOf({self.id}.series);
            if (_idx >= 0) {self._chart.id}._seriesList.splice(_idx, 1);
            var _legendItem = {self._chart.id}.legend._lines.find(l => l.series == {self.id}.series);
            if (_legendItem) {{
                {self._chart.id}.legend._lines = {self._chart.id}.legend._lines.filter(l => l != _legendItem);
                try {{ {self._chart.id}.legend.div.removeChild(_legendItem.row) }} catch(e) {{}}
            }}
            delete {self.id}
        ''')

    def clear_data(self):
        """清空系列数据和标记。"""
        self.clear_markers()
        self.run_script(f'{self.id}.series.setData([])')
        self.data = pd.DataFrame()

    def _get_df_interval_offset(self, df: pd.DataFrame) -> (int, int):
        """获取数据DF内时间点的通常间隔（秒），返回，时间间隔（秒）和偏移时间（秒）"""
        return get_df_interval_offset(df)

    def _time_to_bar_time(self, data: int | float | pd.Series | pd.DataFrame) -> int | float | pd.Series | pd.DataFrame:
        """将时间戳转换为bar时间戳（委托到所属图表的时间级别）。"""
        return self._chart._time_to_bar_time(data)


    def _single_datetime_format(self, arg) -> int:
        """格式化单个时间值（委托到所属图表的时间级别）。"""
        return self._chart._single_datetime_format(arg)

    def set(self, df: Optional[pd.DataFrame] = None, _df_cleaned=False):
        """
        设置或更新系列数据。

        :param df: 包含时间序列数据的 DataFrame，需要包含 'time' 列 或 'date' 列，否则使用 'index' 作为 ‘time’ 列。
            对于 Line 系列，还需要 'value' 列或与系列同名的列。
            对于 CandleSeries 系列，需要 'open', 'high', 'low', 'close' 列。
            如果为 None 或空 DataFrame，则清空数据。
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
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

        if not _df_cleaned:
            df = normal_df(df, exclude_lowercase=self.name)
            df = self._time_to_bar_time(df)
            df = merge_value_by_time(df)

        if self.name:
            # 大小写不敏感匹配列名（AbstractChart 可能保留了原始大小写）
            col_match = next((c for c in df.columns if c.lower() == self.name.lower()), None)
            if col_match is None:
                raise NameError(f'No column named "{self.name}".')
            if col_match != 'value':
                df = df.rename(columns={col_match: 'value'})

        self.data = df.copy()
        self._last_bar = df.iloc[-1]
        self.run_script(f'{self.id}.series.setData({js_data(df)}); ')
        if self.markers:
            self._update_markers()

    def _clean_df(self, df, _df_cleaned=False):
        """清洗 DataFrame（normal_df + _time_to_bar_time + merge_value_by_time）。

        :param df: 输入 DataFrame
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过全部三步。
            False（默认）执行完整清洗流程。
        """
        if _df_cleaned:
            return df
        df = normal_df(df)
        df = self._time_to_bar_time(df)
        df = merge_value_by_time(df)
        return df

    def update_bar(self, series: pd.Series):
        """更新最新一根 bar 或追加新 bar。"""
        self.update_bars(series.to_frame().T)

    update = update_bar

    def _clean_update_bars(self, df: pd.DataFrame, exclude_lowercase=None, _df_cleaned=False):
        '''
        通用函数，清理批量更新数据，确保时间是单调递增的，且在 _last_bar 后面。
        :return:
        '''
        if df.empty:
            return df

        # 先直接清理格式
        if not _df_cleaned:
            df = normal_df(df, exclude_lowercase=exclude_lowercase)
            df = self._time_to_bar_time(df)
            df = merge_value_by_time(df)

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

    def update_bars(self, df: pd.DataFrame):
        """
        Batch-updates the series with multiple data points at once.

        Processes each row from the DataFrame using the same logic as
        update(), but collects all JavaScript commands into a single
        batch for efficiency.  This mirrors CandleSeries.update_bars()
        for Line and Histogram series.

        :param df: DataFrame, must contain a 'time' column plus the
                   series value column(s) (e.g. the line name column
                   or a 'value' column for Histogram).
        """
        if df.empty:
            return

        # 先直接清理格式
        df = self._clean_update_bars(df, exclude_lowercase=self.name)
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

    def update_from_tick(self, series: pd.Series):
        """
        使用单个 tick 更新图表。
        :param series: 包含 time 和 value 的 Series
        """
        self.update_from_ticks(series.to_frame().T)

    def update_from_ticks(self, df: pd.DataFrame, _df_cleaned=False):
        """
        批量使用 tick 更新图表，内部自动按时间分片取 last 值。

        通用版本：按 time 分组，取每组最后一条数据的 value。
        CandleSeries 会覆盖此方法，实现 OHLC 聚合。

        :param df: DataFrame，需要 time 列和 value 列（或与系列同名的列）
        :param _df_cleaned: True 表示数据已清洗过，跳过重复清洗。
        """
        if df.empty:
            return

        if self._last_bar is None:
            raise AssertionError('update_from_ticks() must be called after set()')

        if not _df_cleaned:
            df = normal_df(df, exclude_lowercase=self.name)
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

        self.update_bars(bars)

    def _update_markers(self):
        auto_scale = jbool(self._chart._marker_auto_scale)
        if len(self.markers) > 0:
            str_markers = json.dumps(list(self.markers.values()))
            self.run_script(f'''
                try {{
                    if (!{self.id}.seriesMarkers) {{
                        {self.id}.seriesMarkers = LightweightCharts.createSeriesMarkers(
                            {self.id}.series, [], {{autoScale: {auto_scale}}}
                        );
                    }}
                    {self.id}.seriesMarkers.setMarkers({str_markers});
                }} catch(e) {{
                    console.error('setMarkers failed:', e.message);
                }}
            ''')
        else:
            self.run_script(f'''
                if ({self.id}.seriesMarkers) {self.id}.seriesMarkers.setMarkers([]);
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
        self.run_script(f'{self.id}.series.applyOptions({{visible: {jbool(arg)}}})')

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
        """删除此折线系列。"""
        super().delete()


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
        """删除此柱状图系列。"""
        super().delete()

    def scale(self, scale_margin_top: float = 0.0, scale_margin_bottom: float = 0.0):
        """调整柱状图的 Y 轴边距。"""
        self.run_script(f'''
        {self.id}.series.priceScale().applyOptions({{
            scaleMargins: {{top: {scale_margin_top}, bottom: {scale_margin_bottom}}}
        }})''')


class VolumeSeries(SeriesCommon):
    """成交量柱状图，独立系列，自动根据 K 线涨跌着色。

    由 ``AbstractChart.__init__`` 自动创建为 ``self.volume``，也可独立创建后手动 ``set()``。

    用法示例::

        # chart 自动创建，直接访问
        chart = Chart()
        chart.set(df)  # volume 数据自动转发到 chart.volume

        # 独立配置
        chart.volume.config(scale_margin_top=0.7)

        # 独立创建（高级用法）
        vol = VolumeSeries(chart, pane_index=1)
        vol.set(vol_df)
        vol.delete()
    """

    def __init__(self, chart: 'AbstractChart', pane_index: int = None,
                 up_color: str = 'rgba(83,141,131,0.8)',
                 down_color: str = 'rgba(200,127,130,0.8)',
                 scale_margin_top: float = 0.8,
                 scale_margin_bottom: float = 0.0,
                 price_scale_id: str = 'volume_scale',
                 _fixed_id: str = None,
                 _dont_add_list: bool = False):
        """
        :param chart: 所属的 AbstractChart 实例
        :param pane_index: 面板索引，None 则为 0
        :param up_color: 上涨颜色（close > open）
        :param down_color: 下跌颜色（close <= open）
        :param scale_margin_top: 价格轴顶部边距（0-1）
        :param scale_margin_bottom: 价格轴底部边距（0-1）
        :param price_scale_id: 价格尺度 ID，相同 ID 的 series 共享价格尺度。默认 'volume_scale'
        :param _fixed_id: 固定 ID，跳过 IDGen 自动生成
        :param _dont_add_list: 是否跳过 JS 端 _seriesList 注册。
            默认 False（加入列表）。
            设为 True 时，创建的 series 不会进入 Handler._seriesList，
            audit() 的 extraSeriesCount 不会将其计入。
            AbstractChart 默认创建时传 True，因为成交量是图表固有组件，
            不应被视为"额外系列"。用户独立创建时保持默认 False 即可。
        """
        pane = pane_index if pane_index is not None else 0
        super().__init__(chart, name='', pane_index=pane, _fixed_id=_fixed_id)

        # 存储构造参数，供重建时使用
        self.up_color = up_color
        self.down_color = down_color
        self.scale_margin_top = scale_margin_top
        self.scale_margin_bottom = scale_margin_bottom
        self.price_scale_id = price_scale_id
        self._dont_add_list = _dont_add_list

        self._build()

    def _build(self):
        self.run_script(f'''
            {self.id} = {self._chart.id}.createHistogramSeries(
                "",
                {{
                    color: '{self.down_color}',
                    lastValueVisible: false,
                    priceLineVisible: false,
                    priceScaleId: '{self.price_scale_id}',
                    priceFormat: {{type: "volume"}},
                }},
                {self.pane_index},
                {jbool(self._dont_add_list)}
            )
            {self.id}.series.priceScale().applyOptions({{
                scaleMargins: {{top: {self.scale_margin_top}, bottom: {self.scale_margin_bottom}}}
            }});0''')

    def set(self, df: pd.DataFrame, _df_cleaned=False):
        """设置成交量数据。自动根据 OHLC 着色。

        :param df: DataFrame，需要包含 time 和 volume 列。如果包含 open/close 列则自动着色，否则使用默认色。
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
        """
        self.run_script(f'{self.id}.series.setData([])')
        self.data = pd.DataFrame()

        if df is None or df.empty:
            return

        if 'volume' not in df.columns:
            return

        df = self._clean_df(df, _df_cleaned)

        vol_df = df[['time', 'volume']].rename(columns={'volume': 'value'})

        # 根据 OHLC 着色
        if 'open' in df.columns and 'close' in df.columns:
            vol_df['color'] = self.down_color
            vol_df.loc[df['close'] > df['open'], 'color'] = self.up_color
        else:
            vol_df['color'] = self.down_color

        self.data = vol_df.copy()
        self._last_bar = vol_df.iloc[-1]
        self.run_script(f'{self.id}.series.setData({js_data(vol_df)})')

    def update_bar(self, series: pd.Series):
        """更新最新一根 bar 的成交量或追加新 bar。"""
        self.update_bars(series.to_frame().T)

    update = update_bar

    def update_bars(self, df: pd.DataFrame, _df_cleaned=False):
        """批量更新成交量。

        :param df: DataFrame，需要包含 time 和 volume 列
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
        """
        if df is None or df.empty:
            return

        df = self._clean_df(df, _df_cleaned)

        if 'volume' not in df.columns:
            return

        vol_df = df[['time', 'volume']].rename(columns={'volume': 'value'})

        if 'open' in df.columns and 'close' in df.columns:
            vol_df['color'] = self.down_color
            vol_df.loc[df['close'] > df['open'], 'color'] = self.up_color
        else:
            vol_df['color'] = self.down_color

        # 过滤旧数据（与 CandleSeries/SeriesCommon 一致）
        if self._last_bar is not None:
            mask = vol_df['time'] >= self._last_bar['time']
            vol_df = vol_df[mask]
            if vol_df.empty:
                return

        js_commands = []
        for _, row in vol_df.iterrows():
            js_commands.append(f'{self.id}.series.update({js_data(row)})')
        self.run_script('; '.join(js_commands))

        # 维护 Python 端数据（与 SeriesCommon 一致）
        if self.data is None or self.data.empty:
            self.data = vol_df[['time', 'value']].copy()
        elif self.data['time'].iloc[-1] == vol_df['time'].iloc[0]:
            self.data = pd.concat([self.data.iloc[:-1], vol_df[['time', 'value']]], ignore_index=True)
        else:
            self.data = pd.concat([self.data, vol_df[['time', 'value']]], ignore_index=True)
        self._last_bar = vol_df.iloc[-1]

    def update_from_ticks(self, df, cumulative_volume=False, _df_cleaned=False):
        """tick 数据聚合为 bar 后更新成交量。

        cumulative_volume=True 时对同一 bar 内的 volume 求和，
        False 时取最后一条。聚合后委托 update_bars 统一处理过滤/更新/维护。
        """
        if df is None or df.empty:
            return
        if self._last_bar is None:
            raise AssertionError('update_from_ticks() must be called after set()')

        df = self._clean_df(df, _df_cleaned)

        if 'volume' not in df.columns:
            return

        group_df = df.groupby('time')
        if cumulative_volume:
            vol_series = group_df['volume'].sum()
        else:
            vol_series = group_df['volume'].last()

        bars = pd.DataFrame({'time': vol_series.index, 'volume': vol_series.values})
        self.update_bars(bars, _df_cleaned=True)

    def config(self, scale_margin_top: float = None, scale_margin_bottom: float = None,
               up_color: str = None, down_color: str = None):
        """配置成交量样式。

        :param scale_margin_top: 价格轴顶部边距
        :param scale_margin_bottom: 价格轴底部边距
        :param up_color: 上涨颜色
        :param down_color: 下跌颜色
        """
        if up_color is not None:
            self.up_color = up_color
        if down_color is not None:
            self.down_color = down_color
        if scale_margin_top is not None or scale_margin_bottom is not None:
            top = scale_margin_top if scale_margin_top is not None else 0.8
            bottom = scale_margin_bottom if scale_margin_bottom is not None else 0.0
            self.scale_margin_top = top
            self.scale_margin_bottom = bottom
            self.run_script(f'''
                {self.id}.series.priceScale().applyOptions({{
                    scaleMargins: {{top: {top}, bottom: {bottom}}}
                }})''')

    def delete(self):
        """删除成交量系列。不影响绑定的 CandleSeries。"""
        super().delete()


class OpenInterestSeries(SeriesCommon):
    """持仓量折线，独立系列。

    由 ``AbstractChart.__init__`` 自动创建为 ``self.oi``，也可独立创建后手动 ``set()``。

    用法示例::

        # chart 自动创建，直接访问
        chart = Chart()
        chart.set(df)  # open_interest 数据自动转发到 chart.oi

        # 独立配置
        chart.oi.config(color='#FF6600')

        # 独立创建（高级用法）
        oi = OpenInterestSeries(chart, pane_index=1)
        oi.set(oi_df)
        oi.delete()
    """

    def __init__(self, chart: 'AbstractChart', pane_index: int = None,
                 color: str = '#F5A623',
                 line_width: int = 1,
                 scale_margin_top: float = 0.8,
                 scale_margin_bottom: float = 0.0,
                 price_scale_id: str = 'oi_scale',
                 _fixed_id: str = None,
                 _dont_add_list: bool = False):
        """
        :param chart: 所属的 AbstractChart 实例
        :param pane_index: 面板索引，None 则为 0
        :param color: 线条颜色
        :param line_width: 线宽
        :param scale_margin_top: 价格轴顶部边距
        :param scale_margin_bottom: 价格轴底部边距
        :param price_scale_id: 价格尺度 ID，相同 ID 的 series 共享价格尺度。默认 'oi_scale'
        :param _fixed_id: 固定 ID，跳过 IDGen 自动生成
        :param _dont_add_list: 是否跳过 JS 端 _seriesList 注册。
            默认 False（加入列表）。
            设为 True 时，创建的 series 不会进入 Handler._seriesList，
            audit() 的 extraSeriesCount 不会将其计入。
            AbstractChart 默认创建时传 True，因为持仓量是图表固有组件，
            不应被视为"额外系列"。用户独立创建时保持默认 False 即可。
        """
        pane = pane_index if pane_index is not None else 0
        super().__init__(chart, name='', pane_index=pane, _fixed_id=_fixed_id)

        # 存储构造参数，供重建时使用
        self.color = color
        self.line_width = line_width
        self.scale_margin_top = scale_margin_top
        self.scale_margin_bottom = scale_margin_bottom
        self.price_scale_id = price_scale_id
        self._dont_add_list = _dont_add_list

        self._build()

    def _build(self):
        self.run_script(f'''
            {self.id} = {self._chart.id}.createLineSeries(
                "",
                {{
                    color: '{self.color}',
                    lineWidth: {self.line_width},
                    priceScaleId: '{self.price_scale_id}',
                    lastValueVisible: false,
                    priceLineVisible: false,
                    crosshairMarkerVisible: true,
                }},
                {self.pane_index},
                {jbool(self._dont_add_list)}
            )
            {self.id}.series.priceScale().applyOptions({{
                scaleMargins: {{top: {self.scale_margin_top}, bottom: {self.scale_margin_bottom}}},
                autoScale: true,
            }});
            0
        ''')

    def set(self, df: pd.DataFrame, _df_cleaned=False):
        """设置持仓量数据。

        :param df: DataFrame，需要包含 time 和 open_interest 列
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
        """
        self.run_script(f'{self.id}.series.setData([])')
        self.data = pd.DataFrame()

        if df is None or df.empty:
            return

        if 'open_interest' not in df.columns:
            return

        df = self._clean_df(df, _df_cleaned)

        oi_df = df[['time', 'open_interest']].rename(columns={'open_interest': 'value'})
        self.data = oi_df.copy()
        self._last_bar = oi_df.iloc[-1]
        self.run_script(f'{self.id}.series.setData({js_data(oi_df)})')

    def update_bar(self, series: pd.Series):
        """更新最新一根 bar 的持仓量或追加新 bar。"""
        self.update_bars(series.to_frame().T)

    update = update_bar

    def update_bars(self, df: pd.DataFrame, _df_cleaned=False):
        """批量更新持仓量。

        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
        """
        if df is None or df.empty:
            return

        df = self._clean_df(df, _df_cleaned)

        if 'open_interest' not in df.columns:
            return

        oi_df = df[['time', 'open_interest']].rename(columns={'open_interest': 'value'})

        # 过滤旧数据（与 CandleSeries/SeriesCommon 一致）
        if self._last_bar is not None:
            mask = oi_df['time'] >= self._last_bar['time']
            oi_df = oi_df[mask]
            if oi_df.empty:
                return

        js_commands = []
        for _, row in oi_df.iterrows():
            js_commands.append(f'{self.id}.series.update({js_data(row)})')
        self.run_script('; '.join(js_commands))

        # 维护 Python 端数据（与 SeriesCommon 一致）
        if self.data is None or self.data.empty:
            self.data = oi_df[['time', 'value']].copy()
        elif self.data['time'].iloc[-1] == oi_df['time'].iloc[0]:
            self.data = pd.concat([self.data.iloc[:-1], oi_df[['time', 'value']]], ignore_index=True)
        else:
            self.data = pd.concat([self.data, oi_df[['time', 'value']]], ignore_index=True)
        self._last_bar = oi_df.iloc[-1]

    def update_from_ticks(self, df, cumulative_volume=False, _df_cleaned=False):
        """tick 数据聚合为 bar 后更新持仓量。聚合后委托 update_bars 统一处理过滤/更新/维护。"""
        if df is None or df.empty:
            return
        if self._last_bar is None:
            raise AssertionError('update_from_ticks() must be called after set()')

        df = self._clean_df(df, _df_cleaned)

        if 'open_interest' not in df.columns:
            return

        group_df = df.groupby('time')
        oi_series = group_df['open_interest'].last()

        bars = pd.DataFrame({'time': oi_series.index, 'open_interest': oi_series.values})
        self.update_bars(bars, _df_cleaned=True)

    def config(self, color: str = None, line_width: int = None,
               scale_margin_top: float = None, scale_margin_bottom: float = None):
        """配置持仓量样式。"""
        opts = {}
        if color is not None:
            opts['color'] = color
            self.color = color
        if line_width is not None:
            opts['lineWidth'] = line_width
        if opts:
            self.run_script(f'{self.id}.series.applyOptions({js_json(opts)})')
        if scale_margin_top is not None or scale_margin_bottom is not None:
            top = scale_margin_top if scale_margin_top is not None else 0.8
            bottom = scale_margin_bottom if scale_margin_bottom is not None else 0.0
            self.scale_margin_top = top
            self.scale_margin_bottom = bottom
            self.run_script(f'''
                {self.id}.series.priceScale().applyOptions({{
                    scaleMargins: {{top: {top}, bottom: {bottom}}},
                    autoScale: true,
                }})''')

    def delete(self):
        """删除持仓量系列。"""
        super().delete()


class CandleSeries(SeriesCommon):
    """独立K线系列，可在任意 pane 上绘制 OHLC 数据，无 volume/open interest。

    适用于参考K线、对比K线等场景，支持 set/update/update_bars 动态更新。

    用法示例::

        chart = Chart(width=1200, height=800)
        chart.set(df_main)  # 主K线 pane 0

        ref = chart.create_candle_series(name='参考K线', pane_index=1)
        ref.set(df_reference)  # 初始数据

        ref.update(new_bar)        # 更新最新 bar 或追加新 bar
        ref.update_bars(df_more)  # 批量追加
    """

    def __init__(self, chart, name: str = '', pane_index: int = 0,
                 up_color: str = 'rgba(39, 157, 130, 100)',
                 down_color: str = 'rgba(200, 97, 100, 100)',
                 border_visible: bool = True, wick_visible: bool = True,
                 price_line: bool = False, price_label: bool = True,
                 price_scale_id: Optional[str] = None,
                 crosshair_marker: bool = True,
                 _fixed_id: str = None,
                 _dont_add_list: bool = False):
        """
        :param chart: 所属的 AbstractChart 实例
        :param name: 系列名称
        :param pane_index: 面板索引，0 = 与主 K 线同面板，>0 = 独立面板
        :param up_color: 上涨颜色
        :param down_color: 下跌颜色
        :param border_visible: 是否显示边框
        :param wick_visible: 是否显示影线
        :param price_line: 是否显示价格线
        :param price_label: 是否显示价格标签
        :param price_scale_id: 价格尺度 ID
        :param crosshair_marker: 十字光标标记
        :param _fixed_id: 固定 ID，跳过 IDGen 自动生成
        :param _dont_add_list: 是否跳过 JS 端 _seriesList 注册和 legend 图例行创建。
            默认 False（加入列表 + 创建图例行）。
            设为 True 时：
            - 不进入 _seriesList（audit 的 extraSeriesCount 不计入）
            - 不创建 legend 图例行（不会显示独立的颜色方块图例）
            AbstractChart 默认创建时传 True，因为 K 线是图表固有组件，
            不应被视为"额外系列"，也不应在 legend 中显示独立条目。
            用户独立创建时保持默认 False 即可。
        """
        super().__init__(chart, name, pane_index, _fixed_id=_fixed_id)
        self.candle_data = pd.DataFrame()

        # 存储构造参数，供重建时使用
        self.up_color = up_color
        self.down_color = down_color
        self.border_visible = border_visible
        self.wick_visible = wick_visible
        self.price_line = price_line
        self.price_label = price_label
        self.price_scale_id = price_scale_id
        self.crosshair_marker = crosshair_marker
        self._dont_add_list = _dont_add_list

        self.border_up_color = up_color
        self.border_down_color = down_color
        self.wick_up_color = up_color
        self.wick_down_color = down_color

        self._build()

    def _build(self):
        self.run_script(f'''
            {self.id} = {self._chart.id}.createCandleSeries(
                "{self.name}",
                {{
                    upColor: '{self.up_color}',
                    downColor: '{self.down_color}',
                    borderUpColor: '{self.border_up_color}',
                    borderDownColor: '{self.border_down_color}',
                    wickUpColor: '{self.wick_up_color}',
                    wickDownColor: '{self.wick_down_color}',
                    borderVisible: {jbool(self.border_visible)},
                    wickVisible: {jbool(self.wick_visible)},
                    lastValueVisible: {jbool(self.price_label)},
                    priceLineVisible: {jbool(self.price_line)},
                    crosshairMarkerVisible: {jbool(self.crosshair_marker)},
                    priceScaleId: {f'"{self.price_scale_id}"' if self.price_scale_id else 'undefined'},
                }},
                {self.pane_index},
                {jbool(self._dont_add_list)}
            );
            0;
        ''')

    def clear_data(self):
        """清空所有 K 线数据和标记。"""
        super().clear_data()
        self.candle_data = pd.DataFrame()
        self._last_bar = None

    def set(self, df: Optional[pd.DataFrame] = None, _df_cleaned=False):
        """
        设置 K 线初始数据。

        :param df: DataFrame，必须包含 time/date 列和 open, high, low, close 列。
            如果为 None 或空 DataFrame，则清空数据。
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
        """
        self.run_script(f"{self.id}.series.setData([])")
        self.data = pd.DataFrame()
        self.candle_data = pd.DataFrame()

        if df is None or df.empty:
            return

        df = self._clean_df(df, _df_cleaned)

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

        if self.markers:
            self._update_markers()

    def update_bar(self, series: pd.Series):
        """更新最新一根 bar 或追加新 bar。"""
        self.update_bars(series.to_frame().T)

    update = update_bar

    def update_bars(self, df: pd.DataFrame, _df_cleaned=False):
        """
        批量更新多根 K 线。

        :param df: DataFrame，必须包含 time/date 列和 open, high, low, close 列。
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
        """
        if df.empty:
            return

        df = self._clean_df(df, _df_cleaned)

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

    def update_from_tick(self, series: pd.Series, cumulative_volume: bool = False):
        """
        使用单个 tick 更新图表。
        :param series: labels: date/time, price, [volume, open_interest]
        :param cumulative_volume: 是否累加成交量
        """
        self.update_from_ticks(series.to_frame().T, cumulative_volume=cumulative_volume)

    def update_from_ticks(self, df: pd.DataFrame, cumulative_volume: bool = False, _df_cleaned=False):
        """
        批量使用 tick 更新图表，内部自动聚合成 bar。

        :param df: DataFrame with columns: date/time, price, [volume, open_interest]
        :param cumulative_volume: If True, adds tick volume onto the latest bar's volume.
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
        """
        if df.empty:
            return

        if self._last_bar is None:
            raise AssertionError('update_from_ticks() must be called after set()')

        df = self._clean_df(df, _df_cleaned)

        group_df = df.groupby('time')

        bars = pd.DataFrame({
            'time': list(group_df.groups),
            'open': group_df['price'].first().array,
            'high': group_df['price'].max().array,
            'low': group_df['price'].min().array,
            'close': group_df['price'].last().array,
        })

        if self._last_bar['time'] == bars['time'].iloc[0]:
            bars.iloc[0, 1] = self._last_bar['open']
            bars.iloc[0, 2] = max(self._last_bar['high'], bars.iloc[0, 2])
            bars.iloc[0, 3] = min(self._last_bar['low'], bars.iloc[0, 3])

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
                {f'permWidth: {perm_width},' if perm_width else ''}
            }})''')

    def delete(self):
        """删除此 K 线系列。"""
        super().delete()
