import json
from datetime import datetime
from typing import Optional, TYPE_CHECKING
import numpy as np
import pandas as pd

from .util import (
    Pane, as_enum, jbool, js_json, TIME, NUM, FLOAT,
    LINE_STYLE, MARKER_POSITION, MARKER_SHAPE,
    PRICE_SCALE_MODE, marker_position, marker_shape, js_data,
    normal_df, merge_value_by_time, merge_candle_by_time,
    get_df_interval_offset, time_to_bar_time, merge_volume_by_time, filter_old_bars
)


if TYPE_CHECKING:
    # 类型检查时专用，不会在运行时导入
    from .abstract import AbstractChart


class SeriesCommon(Pane):
    """图表的系列数据基类，管理数据更新、标记、绘图和价格线。"""

    tick_required_cols = ['time', 'value']
    bar_required_cols = ['time', 'value']

    def __init__(self, chart: 'AbstractChart', name: str = '', pane_index: int = 0, _fixed_id: str = None, _option_columns: list[str] = None, legend: bool = True):
        """
        :param chart: 所属的 AbstractChart 实例
        :param name: 系列名称（用于图例标识）
        :param pane_index: 所属面板索引
        :param _fixed_id: 固定 ID（如 'window.Chart_1_candle'），跳过 IDGen 自动生成
        :param _option_columns: 可选列名列表（全小写），set/update_bars 时若输入 df 中存在这些列则自动携带
        :param legend: 是否在图例中显示此系列。默认 True。设为 False 时不创建图例行。
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
        self._option_columns = _option_columns or []
        self._legend = legend

    def pop(self, count: int = 1):
        """从系列末尾移除指定数量的数据点。"""
        self.run_script(f'{self.id}.series.pop({count})')

    def delete(self):
        """删除此系列（清除标记、重置状态、移除 JS 对象、清理图例）。"""
        self.clear_data()

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
            }};
            delete {self.id};
        ''')

    def clear_data(self):
        """清空系列数据和标记。"""
        self.clear_markers()
        self.data = pd.DataFrame()
        self._last_bar = None
        self.run_script(f'{self.id}.series.setData([])')

    def _time_to_bar_time(self, data: int | float | pd.Series | pd.DataFrame) -> int | float | pd.Series | pd.DataFrame:
        """将时间戳转换为bar时间戳（委托到所属图表的时间级别）。"""
        return self._chart._time_to_bar_time(data)

    def _single_datetime_format(self, arg) -> int:
        """格式化单个时间值（委托到所属图表的时间级别）。"""
        return self._chart._single_datetime_format(arg)

    def set(self, df: Optional[pd.DataFrame] = None, _df_cleaned=False):
        """
        设置或更新系列数据。

        :param df: 包含 time 和 value 列的 DataFrame。
            如果为 None 或空 DataFrame，则清空数据。
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
        """
        self.clear_data()
        if df is None or df.empty:
            return
        self.update_bars(df, _df_cleaned)

    def update_bar(self, series: pd.Series):
        """更新最新一根 bar 或追加新 bar。"""
        self.update_bars(series.to_frame().T)

    def update_bars(self, df: pd.DataFrame, _df_cleaned=False):
        """
        批量更新系列数据。

        :param df: DataFrame，需要包含 time 和 value 列。
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
        """
        if df is None or df.empty:
            return

        # ── 清洗 ──
        if not _df_cleaned:
            df = normal_df(df)
            df = self._time_to_bar_time(df)
            df = merge_value_by_time(df)
        df = filter_old_bars(df, self._last_bar['time'] if self._last_bar is not None else None)
        if df is None or df.empty:
            return

        # ── 校验 + 选列 ──
        missing = [c for c in self.bar_required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"DataFrame 缺少必需列: {missing}")
        cols = ['time', 'value']
        for c in self._option_columns:
            if c in df.columns and c not in cols:
                cols.append(c)
        df = df[cols]

        # ── JS 更新 ──
        if self.data is None or self.data.empty:
            self.data = df.copy()
            self._last_bar = df.iloc[-1]
            self.run_script(f'{self.id}.series.setData({js_data(df)})')
        else:
            js_commands = [f'{self.id}.series.update({js_data(row)});' for _, row in df.iterrows()]
            self.run_script(' '.join(js_commands))
            if self.data['time'].iloc[-1] == df['time'].iloc[0]:
                self.data = pd.concat([self.data.iloc[:-1], df], ignore_index=True)
            else:
                self.data = pd.concat([self.data, df], ignore_index=True)
            self._last_bar = df.iloc[-1]

    def update_tick(self, series: pd.Series):
        """
        使用单个 tick 更新图表。
        :param series: 包含 time 和 value 的 Series
        """
        self.update_ticks(series.to_frame().T)

    def update_ticks(self, df: pd.DataFrame, _df_cleaned=False):
        """
        批量使用 tick 更新图表，内部自动按时间分片取 last 值。

        通用版本：按 time 分组，取每组最后一条数据的 value。
        CandleSeries 会覆盖此方法，实现 OHLC 聚合。

        :param df: DataFrame，需要 time 列和 value 列
        :param _df_cleaned: True 表示数据已清洗过，跳过重复清洗。
        """
        if df is None or df.empty:
            return

        if not _df_cleaned:
            df = normal_df(df)
            df = self._time_to_bar_time(df)

        missing = [c for c in self.tick_required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"DataFrame 缺少必需列: {missing}")

        df = merge_value_by_time(df)
        self.update_bars(df, _df_cleaned=True)

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

    def add_markers(self, markers: list[dict]):
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

    def add_marker(self, time: Optional[datetime] = None, position: MARKER_POSITION = 'below',
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
        self.run_script(f'{self.id}.precision = {precision}')
        self._apply_options({'priceFormat': {'precision': precision, 'minMove': min_move}})
        self.num_decimals = precision

    def hide_data(self):
        """隐藏当前系列的数据（K 线、成交量、持仓量）。"""
        self._toggle_data(False)

    def show_data(self):
        """显示当前系列的数据。"""
        self._toggle_data(True)

    def _toggle_data(self, visible: bool):
        self._apply_options({'visible': visible})

    def _apply_options(self, options: dict):
        """向 JS 端的 series.applyOptions() 发送选项字典。

        :param options: 选项字典，键名使用 JS 驼峰格式（如 lineWidth, upColor）。
                        None 值会被 js_json 自动过滤。
        """
        self.run_script(f'{self.id}.series.applyOptions({js_json(options)})')

    def price_scale(
        self,
        auto_scale: Optional[bool] = None,
        mode: Optional[PRICE_SCALE_MODE] = None,
        invert_scale: Optional[bool] = None,
        align_labels: Optional[bool] = None,
        scale_margin_top: Optional[float] = None,
        scale_margin_bottom: Optional[float] = None,
        border_visible: Optional[bool] = None,
        border_color: Optional[str] = None,
        text_color: Optional[str] = None,
        entire_text_only: Optional[bool] = None,
        visible: Optional[bool] = None,
        ticks_visible: Optional[bool] = None,
        tick_mark_density: Optional[float] = None,
        minimum_width: Optional[int] = None,
        ensure_edge_tick_marks_visible: Optional[bool] = None,
        price_format: Optional[dict] = None,
    ):
        """配置价格坐标轴的外观与行为。

        所有参数均为可选，不传则由 JS 端使用官方默认值。
        scale_margin_top / scale_margin_bottom 互锁：必须同时指定或同时省略。

        :param auto_scale: 自动缩放以适应可见数据范围
        :param mode: 价格轴模式 — 'normal' | 'logarithmic' | 'percentage' | 'indexedTo100'
        :param invert_scale: 反转价格轴
        :param align_labels: 对齐标签防止重叠
        :param scale_margin_top: 顶部留白比例 (0~1)
        :param scale_margin_bottom: 底部留白比例 (0~1)
        :param border_visible: 是否在价格轴和图表区域之间绘制边框
        :param border_color: 边框颜色，如 '#2B2B43'
        :param text_color: 标签文字颜色，不设置则跟随全局 LayoutOptions.textColor
        :param entire_text_only: 仅在完整文字可见时显示角标
        :param visible: 是否显示此价格轴（叠加轴始终可见）
        :param ticks_visible: 是否在标签旁绘制小水平刻度线
        :param tick_mark_density: 标签密度，值越大间距越大、标签越少（默认 2.5）
        :param minimum_width: 价格轴最小宽度（像素）
        :param ensure_edge_tick_marks_visible: 始终在价格轴顶部和底部绘制刻度线
        :param price_format: 价格格式，如 {'type': 'base', 'base': 100, 'precision': 2}
        """
        if (scale_margin_top is None) != (scale_margin_bottom is None):
            raise ValueError(
                'scale_margin_top 和 scale_margin_bottom 必须同时指定，'
                f'当前只传了 {"scale_margin_top" if scale_margin_top is not None else "scale_margin_bottom"}。'
            )

        options = {}
        if auto_scale is not None:
            options['autoScale'] = auto_scale
        if mode is not None:
            options['mode'] = as_enum(mode, PRICE_SCALE_MODE)
        if invert_scale is not None:
            options['invertScale'] = invert_scale
        if align_labels is not None:
            options['alignLabels'] = align_labels
        if scale_margin_top is not None:
            options['scaleMargins'] = {'top': scale_margin_top, 'bottom': scale_margin_bottom}
        if border_visible is not None:
            options['borderVisible'] = border_visible
        if border_color is not None:
            options['borderColor'] = border_color
        if text_color is not None:
            options['textColor'] = text_color
        if entire_text_only is not None:
            options['entireTextOnly'] = entire_text_only
        if visible is not None:
            options['visible'] = visible
        if ticks_visible is not None:
            options['ticksVisible'] = ticks_visible
        if tick_mark_density is not None:
            options['tickMarkDensity'] = tick_mark_density
        if minimum_width is not None:
            options['minimumWidth'] = minimum_width
        if ensure_edge_tick_marks_visible is not None:
            options['ensureEdgeTickMarksVisible'] = ensure_edge_tick_marks_visible
        if price_format is not None:
            options['priceFormat'] = price_format

        if options:
            self.run_script(f'{self.id}.series.priceScale().applyOptions({js_json(options)})')


class LineSeries(SeriesCommon):
    """折线系列，用于绘制折线图。"""
    def __init__(self, chart, name, color, style, width, price_line, price_label, price_scale_id=None,
                 crosshair_marker=True, pane_index: int = 0, legend: bool = True,
    ):

        super().__init__(chart, name, pane_index, legend=legend)
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
                {pane_index},
                false,
                {jbool(legend)}
            );
            0;
        ''')


class HistogramSeries(SeriesCommon):
    """柱状图系列，常用于成交量或持仓量展示。

    支持通过 ``option_columns`` 传入可选列（如 ``['color']``），set/update_bars 时若输入 df 中存在这些列则自动携带到 JS 端。

    示例::

        df = pd.DataFrame({'time': [1,2,3], 'value': [10,20,15], 'color': ['#f00','#0f0','#00f']})
        hist = chart.create_histogram()
        hist.set(df)
    """
    def __init__(self, chart, name, color, price_line, price_label, scale_margin_top, scale_margin_bottom,
                 pane_index: int = 0, legend: bool = True
    ):
        super().__init__(chart, name, pane_index, _option_columns=['color'], legend=legend)
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
                {pane_index},
                false,
                {jbool(legend)}
            );
            0;
        ''')
        self.price_scale(scale_margin_top=scale_margin_top, scale_margin_bottom=scale_margin_bottom)

    def scale(self, scale_margin_top: float = 0.0, scale_margin_bottom: float = 0.0):
        """调整柱状图的 Y 轴边距。"""
        self.price_scale(scale_margin_top=scale_margin_top, scale_margin_bottom=scale_margin_bottom)


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
    tick_required_cols = ['time', 'value', 'price']
    bar_required_cols = ['time', 'value', 'open', 'close']

    def __init__(self, chart: 'AbstractChart', pane_index: int = None,
                 up_color: str = 'rgba(83,141,131,0.8)',
                 down_color: str = 'rgba(200,127,130,0.8)',
                 scale_margin_top: float = 0.8,
                 scale_margin_bottom: float = 0.0,
                 price_scale_id: str = 'volume_scale',
                 _fixed_id: str = None,
                 _dont_add_list: bool = False,
                 legend: bool = True):
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
        super().__init__(chart, name='', pane_index=pane, _fixed_id=_fixed_id, legend=legend)

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
                {jbool(self._dont_add_list)},
                {jbool(self._legend)}
            );
            0;
        ''')
        self.price_scale(scale_margin_top=self.scale_margin_top, scale_margin_bottom=self.scale_margin_bottom)

    def set(self, df: Optional[pd.DataFrame] = None, _df_cleaned=False):
        """设置成交量数据。自动根据 open/close 涨跌着色。

        :param df: DataFrame，需要包含 time, value, open, close 列。open/close 用于涨跌着色和持久化。
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
        """
        self.clear_data()
        if df is None or df.empty:
            return
        self.update_bars(df, _df_cleaned)

    def update_bar(self, series: pd.Series):
        """更新最新一根 bar 的成交量或追加新 bar。"""
        self.update_bars(series.to_frame().T)

    def update_bars(self, df: pd.DataFrame, _df_cleaned=False, _cumulative_volume=False):
        """批量更新成交量。

        :param df: DataFrame，需要包含 time, value, open, close 列。
        :param _df_cleaned: True 表示数据已由 AbstractChart 或 update_ticks 清洗过，跳过重复清洗。
        :param _cumulative_volume: 内部参数，True 时将新 volume 累加到已有 bar（由 update_ticks 传入）。
        """
        if df is None or df.empty:
            return
        if not _df_cleaned:
            df = normal_df(df, self.bar_required_cols)
            df = merge_volume_by_time(df, is_tick=False)

        assert list(df.columns) == list(self.bar_required_cols),\
            f'发现数据列名不符合要求: {list(df.columns)} != {list(self.bar_required_cols)}'

        # 过滤旧数据
        if self._last_bar is not None:
            df = filter_old_bars(df, self._last_bar['time'])

        if df.empty:
            return

        if self.data is None or self.data.empty:
            # 首批数据 → setData 批量写入（JS 只需要 time, value, color）
            self.data = df.copy()
            js_df = df[['time', 'value']]
            js_df['color'] = np.where(df['close'] > df['open'], self.up_color, self.down_color)
            self.run_script(f'{self.id}.series.setData({js_data(js_df)})')

        else:
            # 确保数据列名一致，并且顺序正确
            assert list(self.data.columns) == list(self.bar_required_cols), \
                f'{list(self.data.columns)} != {list(self.bar_required_cols)}'
            col_time_idx = 0
            col_value_idx = 1
            col_open_idx = 2

            # 后续数据 → per-row update
            df_len = len(df)
            if self.data.iat[-1, col_time_idx] == df.iat[0, col_time_idx]:
                if _cumulative_volume:
                    # 累加 volume
                    df.iat[0, col_value_idx] = self.data.iat[-1, col_value_idx] + df.iat[0, col_value_idx]
                    # 保留已有 open
                    df.iat[0, col_open_idx] = self.data.iat[-1, col_open_idx]
                # 拼接到data上
                self.data = pd.concat([self.data.iloc[:-1], df], ignore_index=True)
            else:
                self.data = pd.concat([self.data, df], ignore_index=True)

            df = self.data.iloc[-df_len:]
            # 现场计算 color，JS 只需要 time, value, color
            js_df = df[['time', 'value']]
            js_df['color'] = np.where(df['close'] > df['open'], self.up_color, self.down_color)
            js_commands = [f'{self.id}.series.update({js_data(row)})' for _, row in js_df.iterrows()]
            self.run_script('; '.join(js_commands))

        self._last_bar = self.data.iloc[-1]

    def update_ticks(self, df, _df_cleaned=False):
        """tick 数据聚合为 bar 后更新成交量。

        输入为原始 tick：time, value(volume), price。
        同一时间窗口内的 tick volume 求和，open/close 从 price 生成。
        聚合后委托 update_bars 统一处理过滤/更新/维护。
        """
        if df is None or df.empty:
            return
        if not _df_cleaned:
            df = normal_df(df, self.tick_required_cols)

        assert list(df.columns) == list(self.tick_required_cols),\
            f'发现数据列名不符合要求: {list(df.columns)} != {list(self.tick_required_cols)}'

        df = merge_volume_by_time(df, is_tick=True)
        self.update_bars(df, _df_cleaned=True, _cumulative_volume=True)

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
            self.price_scale(scale_margin_top=top, scale_margin_bottom=bottom)


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
                 _dont_add_list: bool = False,
                 legend: bool = True):
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
        super().__init__(chart, name='', pane_index=pane, _fixed_id=_fixed_id, legend=legend)

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
                {jbool(self._dont_add_list)},
                {jbool(self._legend)}
            );
            0;
        ''')
        self.price_scale(
            scale_margin_top=self.scale_margin_top,
            scale_margin_bottom=self.scale_margin_bottom,
            auto_scale=True,
        )

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
            self._apply_options(opts)
        if scale_margin_top is not None or scale_margin_bottom is not None:
            top = scale_margin_top if scale_margin_top is not None else 0.8
            bottom = scale_margin_bottom if scale_margin_bottom is not None else 0.0
            self.scale_margin_top = top
            self.scale_margin_bottom = bottom
            self.price_scale(scale_margin_top=top, scale_margin_bottom=bottom, auto_scale=True)


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
    tick_required_cols = ['time', 'value']
    bar_required_cols = ['time', 'open', 'high', 'low', 'close']

    def __init__(self, chart, name: str = '', pane_index: int = 0,
                 up_color: str = 'rgba(39, 157, 130, 100)',
                 down_color: str = 'rgba(200, 97, 100, 100)',
                 border_visible: bool = True, wick_visible: bool = True,
                 price_line: bool = False, price_label: bool = True,
                 price_scale_id: Optional[str] = None,
                 crosshair_marker: bool = True,
                 _fixed_id: str = None,
                 _dont_add_list: bool = False,
                 legend: bool = True):
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
        :param _dont_add_list: 是否跳过 JS 端 _seriesList 注册。默认 False。
        :param legend: 是否在图例中显示此系列。默认 True。
        """
        super().__init__(chart, name, pane_index, _fixed_id=_fixed_id, legend=legend)

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
                {jbool(self._dont_add_list)},
                {jbool(self._legend)}
            );
            0;
        ''')

    def candle_style(
            self, up_color: str = 'rgba(39, 157, 130, 100)', down_color: str = 'rgba(200, 97, 100, 100)',
            wick_visible: bool = True, border_visible: bool = True, border_up_color: str = '',
            border_down_color: str = '', wick_up_color: str = '', wick_down_color: str = ''):
        """
        Candle styling for each of its parts.
        If only `up_color` and `down_color` are passed, they will color all parts of the candle.
        """
        self.up_color = up_color
        self.down_color = down_color
        self.wick_visible = wick_visible
        self.border_visible = border_visible
        self.border_up_color = border_up_color if border_up_color else up_color
        self.border_down_color = border_down_color if border_down_color else down_color
        self.wick_up_color = wick_up_color if wick_up_color else up_color
        self.wick_down_color = wick_down_color if wick_down_color else down_color
        self._apply_options({k: v for k, v in locals().items() if k != 'self'})

    def clear_data(self):
        """清空所有 K 线数据和标记。"""
        super().clear_data()

    def set(self, df: Optional[pd.DataFrame] = None, _df_cleaned=False):
        """
        设置 K 线初始数据。

        :param df: DataFrame，必须包含 time/date 列和 open, high, low, close 列。
            如果为 None 或空 DataFrame，则清空数据。
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
        """
        self.clear_data()
        if df is None or df.empty:
            return
        self.update_bars(df, _df_cleaned)

    def update_bar(self, series: pd.Series):
        """更新最新一根 bar 或追加新 bar。"""
        self.update_bars(series.to_frame().T)

    def update_bars(self, df: pd.DataFrame, _df_cleaned=False):
        """
        批量更新多根 K 线。

        :param df: DataFrame，必须包含 time/date 列和 open, high, low, close 列。
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
        """
        if df is None or df.empty:
            return

        if not _df_cleaned:
            df = normal_df(df, self.bar_required_cols)
            df = merge_candle_by_time(df, is_tick=False)

        # 选列：AbstractChart 可能传入带 volume 等额外列的 df
        ohlc = df[list(self.bar_required_cols)]

        # 过滤旧数据
        if self._last_bar is not None:
            ohlc = filter_old_bars(ohlc, self._last_bar['time'])

        if ohlc.empty:
            return

        js_commands = []
        for _, row in ohlc.iterrows():
            js_commands.append(f'{self.id}.series.update({js_data(row)});')

        if self.data.empty:
            self.data = ohlc
        elif self.data.iloc[-1]['time'] == ohlc.iloc[0]['time']:
            self.data = pd.concat([self.data.iloc[:-1], ohlc], ignore_index=True)
        else:
            self.data = pd.concat([self.data, ohlc], ignore_index=True)

        self._last_bar = ohlc.iloc[-1]
        self.run_script(' '.join(js_commands))

    def update_tick(self, series: pd.Series):
        """
        使用单个 tick 更新图表。
        :param series: labels: date/time, price
        """
        self.update_ticks(series.to_frame().T)

    def update_ticks(self, df: pd.DataFrame, _df_cleaned=False):
        """
        批量使用 tick 更新图表，内部自动聚合成 bar。

        输入为原始 tick：time, value(=price)。
        同一时间窗口内的 tick 聚合为 OHLC。
        聚合后委托 update_bars 统一处理过滤/更新/维护。

        :param df: DataFrame with columns: time, value (= price)
        :param _df_cleaned: True 表示数据已由 AbstractChart 清洗过，跳过重复清洗。
        """
        if df is None or df.empty:
            return

        if not _df_cleaned:
            # AbstractChart 已做 normal_df + time_to_bar_time，列名是 time + value
            df = normal_df(df, self.tick_required_cols)

        assert list(df.columns) == list(self.tick_required_cols),\
            f'发现数据列名不符合要求: {list(df.columns)} != {list(self.tick_required_cols)}'

        df = merge_candle_by_time(df, is_tick=True)
        self.update_bars(df, _df_cleaned=True)


class AreaSeries(SeriesCommon):
    """面积图系列，折线下方填充渐变色。

    适用于展示指标的 magnitude，如均线面积、波动率面积等。

    用法示例::

        df = pd.DataFrame({'time': [1,2,3], 'value': [10,20,15]})
        area = chart.create_area(name='SMA', color='#2196F3')
        area.set(df)
    """
    def __init__(self, chart, name: str = '', color: str = '#2196F3',
                 line_style: LINE_STYLE = 'solid', line_width: int = 2,
                 top_color: str = 'rgba(33, 150, 243, 0.4)',
                 bottom_color: str = 'rgba(33, 150, 243, 0)',
                 relative_gradient: bool = False,
                 invert_filled_area: bool = False,
                 price_line: bool = True, price_label: bool = True,
                 price_scale_id: Optional[str] = None,
                 crosshair_marker: bool = True,
                 pane_index: int = 0, legend: bool = True):
        """
        :param chart: 所属的 AbstractChart 实例
        :param name: 系列名称（用于图例标识）
        :param color: 线条颜色
        :param line_style: 线条样式（solid/dotted/dashed 等）
        :param line_width: 线条宽度
        :param top_color: 面积顶部渐变颜色（RGBA，含透明度）
        :param bottom_color: 面积底部渐变颜色（RGBA，含透明度）
        :param relative_gradient: 渐变是否相对于基准值
        :param invert_filled_area: 是否反转填充区域（填充线上方而非下方）
        :param price_line: 是否显示价格线
        :param price_label: 是否显示价格标签
        :param price_scale_id: 价格尺度 ID
        :param crosshair_marker: 十字光标标记
        :param pane_index: 面板索引
        :param legend: 是否在图例中显示此系列
        """
        super().__init__(chart, name, pane_index, legend=legend)
        self.color = color

        self.run_script(f'''
            {self.id} = {self._chart.id}.createAreaSeries(
                "{name}",
                {{
                    lineColor: '{color}',
                    topColor: '{top_color}',
                    bottomColor: '{bottom_color}',
                    lineWidth: {line_width},
                    lineStyle: {as_enum(line_style, LINE_STYLE)},
                    relativeGradient: {jbool(relative_gradient)},
                    invertFilledArea: {jbool(invert_filled_area)},
                    lastValueVisible: {jbool(price_label)},
                    priceLineVisible: {jbool(price_line)},
                    crosshairMarkerVisible: {jbool(crosshair_marker)},
                    priceScaleId: {f'"{price_scale_id}"' if price_scale_id else 'undefined'},
                }},
                {pane_index},
                false,
                {jbool(legend)}
            );
            0;
        ''')


class OHLCBarSeries(CandleSeries):
    """美国线（OHLC 横向柱状图）系列。

    继承自 CandleSeries，共享全部 OHLC 数据处理逻辑（set/update_bars/update_ticks）。
    仅覆盖 JS 创建方法（BarSeries 替代 CandlestickSeries）和样式配置。

    与 K 线使用同一套 OHLC 数据，但用横向短横表示 open（左）和 close（右），
    无矩形实体，适合习惯美股经典图表风格的用户。

    用法示例::

        df = pd.DataFrame({'time': [1,2,3], 'open': [10,12,11], 'high': [15,16,14], 'low': [8,10,9], 'close': [13,11,14]})
        bar = chart.create_ohlc_bar(name='美国线')
        bar.set(df)
    """
    def __init__(self, chart, name: str = '',
                 up_color: str = '#26a69a', down_color: str = '#ef5350',
                 open_visible: bool = True, thin_bars: bool = True,
                 price_line: bool = False, price_label: bool = True,
                 price_scale_id: Optional[str] = None,
                 crosshair_marker: bool = True,
                 pane_index: int = 0, legend: bool = True):
        """
        :param chart: 所属的 AbstractChart 实例
        :param name: 系列名称
        :param up_color: 上涨颜色（close > open）
        :param down_color: 下跌颜色（close <= open）
        :param open_visible: 是否显示 open 横线
        :param thin_bars: 是否用细棒显示
        :param price_line: 是否显示价格线
        :param price_label: 是否显示价格标签
        :param price_scale_id: 价格尺度 ID
        :param crosshair_marker: 十字光标标记
        :param pane_index: 面板索引
        :param legend: 是否在图例中显示此系列
        """
        # 跳过 CandleSeries.__init__，直接调用 SeriesCommon.__init__
        # 避免 CandleSeries 创建 CandlestickSeries JS 对象
        SeriesCommon.__init__(self, chart, name, pane_index, legend=legend)

        self.up_color = up_color
        self.down_color = down_color
        self.open_visible = open_visible
        self.thin_bars = thin_bars
        self.price_line = price_line
        self.price_label = price_label
        self.price_scale_id = price_scale_id
        self.crosshair_marker = crosshair_marker
        self._dont_add_list = False

        self._build()

    def _build(self):
        """创建 JS 端 BarSeries 对象。"""
        self.run_script(f'''
            {self.id} = {self._chart.id}.createOHLCBarSeries(
                "{self.name}",
                {{
                    upColor: '{self.up_color}',
                    downColor: '{self.down_color}',
                    openVisible: {jbool(self.open_visible)},
                    thinBars: {jbool(self.thin_bars)},
                    lastValueVisible: {jbool(self.price_label)},
                    priceLineVisible: {jbool(self.price_line)},
                    crosshairMarkerVisible: {jbool(self.crosshair_marker)},
                    priceScaleId: {f'"{self.price_scale_id}"' if self.price_scale_id else 'undefined'},
                }},
                {self.pane_index},
                false,
                {jbool(self._legend)}
            );
            0;
        ''')

    def candle_style(self, *args, **kwargs):
        """美国线不支持 candle_style，请使用 bar_style() 代替。"""
        raise AttributeError("OHLCBarSeries 没有 candle_style，请使用 bar_style() 代替")

    def bar_style(self, up_color: str = '', down_color: str = '',
                  open_visible: bool = None, thin_bars: bool = None):
        """
        修改美国线样式。

        :param up_color: 上涨颜色（留空则不变）
        :param down_color: 下跌颜色（留空则不变）
        :param open_visible: 是否显示 open 横线（None 则不变）
        :param thin_bars: 是否用细棒显示（None 则不变）
        """
        opts = {}
        if up_color:
            self.up_color = up_color
            opts['upColor'] = up_color
        if down_color:
            self.down_color = down_color
            opts['downColor'] = down_color
        if open_visible is not None:
            self.open_visible = open_visible
            opts['openVisible'] = open_visible
        if thin_bars is not None:
            self.thin_bars = thin_bars
            opts['thinBars'] = thin_bars
        if opts:
            self._apply_options(opts)


class BaselineSeries(SeriesCommon):
    """基准线系列，以某个基准值为界，上方/下方分别着色。

    适合展示相对于某个参考值（如零轴、均线、开盘价）的变化。

    用法示例::

        df = pd.DataFrame({'time': [1,2,3], 'value': [10, -5, 8]})
        baseline = chart.create_baseline(name='RSI偏差', base_value=0)
        baseline.set(df)
    """
    def __init__(self, chart, name: str = '',
                 base_value: float = 0,
                 top_fill_color1: str = 'rgba(38, 166, 154, 0.28)',
                 top_fill_color2: str = 'rgba(38, 166, 154, 0.05)',
                 top_line_color: str = 'rgba(38, 166, 154, 1)',
                 bottom_fill_color1: str = 'rgba(239, 83, 80, 0.05)',
                 bottom_fill_color2: str = 'rgba(239, 83, 80, 0.28)',
                 bottom_line_color: str = 'rgba(239, 83, 80, 1)',
                 line_width: int = 2,
                 line_style: LINE_STYLE = 'solid',
                 relative_gradient: bool = False,
                 price_line: bool = True, price_label: bool = True,
                 price_scale_id: Optional[str] = None,
                 crosshair_marker: bool = True,
                 pane_index: int = 0, legend: bool = True):
        """
        :param chart: 所属的 AbstractChart 实例
        :param name: 系列名称
        :param base_value: 基准值，上方区域和下方区域的分界线
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
        :param price_scale_id: 价格尺度 ID
        :param crosshair_marker: 十字光标标记
        :param pane_index: 面板索引
        :param legend: 是否在图例中显示此系列
        """
        super().__init__(chart, name, pane_index, legend=legend)

        self.run_script(f'''
            {self.id} = {self._chart.id}.createBaselineSeries(
                "{name}",
                {{
                    baseValue: {{ type: 'price', price: {base_value} }},
                    topFillColor1: '{top_fill_color1}',
                    topFillColor2: '{top_fill_color2}',
                    topLineColor: '{top_line_color}',
                    bottomFillColor1: '{bottom_fill_color1}',
                    bottomFillColor2: '{bottom_fill_color2}',
                    bottomLineColor: '{bottom_line_color}',
                    lineWidth: {line_width},
                    lineStyle: {as_enum(line_style, LINE_STYLE)},
                    relativeGradient: {jbool(relative_gradient)},
                    lastValueVisible: {jbool(price_label)},
                    priceLineVisible: {jbool(price_line)},
                    crosshairMarkerVisible: {jbool(crosshair_marker)},
                    priceScaleId: {f'"{price_scale_id}"' if price_scale_id else 'undefined'},
                }},
                {pane_index},
                false,
                {jbool(legend)}
            );
            0;
        ''')
