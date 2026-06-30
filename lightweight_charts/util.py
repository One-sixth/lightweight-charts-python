import asyncio
import json
import inspect
import warnings
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Literal, Union, Tuple, TYPE_CHECKING, Optional
import pandas as pd
import numpy as np


if TYPE_CHECKING:
    from .abstract import Window


class Pane:
    """所有可放置在图表上的组件的基类。自动分配唯一 ID 并持有窗口引用。"""
    def __init__(self, window, prefix=''):
        self.win: 'Window' = window
        self.run_script = window.run_script
        self.bulk_run = window.bulk_run
        if hasattr(self, 'id'):
            return
        self.id = window._id_gen.generate(f'{type(self).__name__}_')


class IDGen:
    """自增 ID 生成器，生成格式如 window.Chart_1 的人类可读 ID。"""
    def __init__(self):
        self._counter = 0

    def generate(self, prefix: str = '') -> str:
        """生成一个全局唯一的 JS 变量名 ID。
        :param prefix: ID 前缀（如 'Chart_'），最终输出 window.前缀+序号"""
        self._counter += 1
        return f'window.{prefix}{self._counter}'


def format_datetime(dt: datetime, tz: Union[str, ZoneInfo] = None) -> str:
    """格式化时间为字符串，可选时区转换。
    :param dt: 待格式化的时间
    :param tz: 目标时区（IANA 名称或 ZoneInfo 对象），None 则不做时区转换
    :return: 格式如 '2026-05-11 14:30' 或 '2026-05-11 14:30 GMT+0800'"""
    if tz is None:
        return dt.strftime('%Y-%m-%d %H:%M')
    elif isinstance(tz, str):
        tz = ZoneInfo(tz)
    # If dt does not contain tzinfo, assume it is in the specified zone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    else:
        # Convert datetime to the required timezone
        dt = dt.astimezone(tz)
    return dt.strftime('%Y-%m-%d %H:%M GMT%z')


def parse_event_message(window, string):
    """解析 JS 端发来的事件消息，拆分为处理器名称和参数列表。
    :param window: Window 实例（持有 handlers 字典）
    :param string: 原始消息字符串，格式: handlerName_~_arg1;;;arg2
    :return: (handler_func, args_list)"""
    name, args = string.split('_~_')
    args = args.split(';;;')
    if name == 'null':
        return None, args
    func = window.handlers.get(name)
    if func is None:
        print(f'[Warning] Event handler "{name}" not found (may have been removed).')
        return None, args
    return func, args


def df_data(data: Union[pd.DataFrame, pd.Series]):
    """将 DataFrame/Series 转为不含 NaN 的 dict/list 结构。
    :param data: 输入数据
    :return: list[dict]（DataFrame）或 dict（Series），已去除 NaN 值"""
    if isinstance(data, pd.DataFrame):
        d = data.to_dict(orient='records')
        filtered_records = [{k: v for k, v in record.items() if v is not None and not pd.isna(v)} for record in d]
    else:
        d = data.to_dict()
        filtered_records = {k: v for k, v in d.items()}
    return filtered_records


def series_data(data: Union[pd.DataFrame, pd.Series]):
    """将 Series 转为 [{index, value}] 格式，float 保留 4 位小数。
    :param data: 输入数据
    :return: list[dict]，每项含 index 和 value 字段"""
    filtered_records = []
    for idx, val in data.items():
        if isinstance(val, float):
            val_str = f'{val:.4f}'
        else:
            val_str = str(val)
        filtered_records.append({'index': idx, 'value': val_str})
    return filtered_records


def js_data(data: Union[pd.DataFrame, pd.Series]):
    """将 DataFrame/Series 转为 JSON 字符串，已去除 NaN 值。
    :param data: 输入数据
    :return: JSON 字符串，可直接嵌入 JS 代码"""
    if isinstance(data, pd.DataFrame):
        d = data.to_dict(orient='records')
        filtered_records = [{k: v for k, v in record.items() if v is not None and not pd.isna(v)} for record in d]
    else:
        d = data.to_dict()
        filtered_records = {k: v for k, v in d.items()}
    return json.dumps(filtered_records)


def snake_to_camel(s: str):
    """将蛇形命名转为驼峰命名。
    :param s: 如 'hello_world'
    :return: 如 'helloWorld'"""
    components = s.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def js_json(d: dict):
    """将 Python dict 转为 JS 侧 JSON.parse() 调用，键名自动转驼峰。
    :param d: 输入字典
    :return: 形如 JSON.parse('{...}') 的 JS 代码字符串"""
    filtered_dict = {}
    for key, val in d.items():
        if key in ('self') or val in (None,):
            continue
        if '_' in key:
            key = snake_to_camel(key)
        filtered_dict[key] = val
    return f"JSON.parse('{json.dumps(filtered_dict)}')"


def jbool(b: bool):
    return 'true' if b is True else 'false' if b is False else None


LINE_STYLE = Literal['solid', 'dotted', 'dashed', 'large_dashed', 'sparse_dotted']

MARKER_POSITION = Literal['above', 'below', 'inside', 'atPriceMiddle', 'atPriceTop', 'atPriceBottom']

MARKER_SHAPE = Literal['arrow_up', 'arrow_down', 'circle', 'square']

CROSSHAIR_MODE = Literal['normal', 'magnet', 'hidden']

PRICE_SCALE_MODE = Literal['normal', 'logarithmic', 'percentage', 'index100']

TIME = Union[datetime, pd.Timestamp, str, float]

NUM = Union[float, int]

FLOAT = Literal['left', 'right', 'top', 'bottom']

# 新增类型定义
GridPosition = Tuple[int, int, int]  # (nrows, ncols, index)
Position = Union[GridPosition, int, str]  # 支持三种格式（字符串已弃用）


def _validate_grid(nrows: int, ncols: int, index: int) -> None:
    """验证网格参数的有效性"""
    if nrows <= 0:
        raise ValueError(f"行数必须是正整数，当前值: {nrows}")
    if ncols <= 0:
        raise ValueError(f"列数必须是正整数，当前值: {ncols}")
    if index <= 0:
        raise ValueError(f"位置索引必须是正整数，当前值: {index}")
    if index > nrows * ncols:
        raise ValueError(f"index {index} 超出网格范围 {nrows}x{ncols}={nrows*ncols}")


def parse_position(pos: Position) -> dict:
    """
    解析 position 参数为统一格式

    :param pos: 位置参数，支持三种格式：
                - 字符串: 'left', 'right', 'top', 'bottom'
                - 元组: (nrows, ncols, index)
                - 整数: 3位数字，如 111, 221, 311
    :return: {'nrows': int, 'ncols': int, 'index': int}
    """
    if isinstance(pos, str):
        warnings.warn(
            f"字符串格式 position='{pos}' 已弃用，请使用数字格式，如 position=121",
            DeprecationWarning,
            stacklevel=3
        )
        return _convert_string_to_grid(pos)

    if isinstance(pos, tuple) and len(pos) == 3:
        nrows, ncols, index = pos
        _validate_grid(nrows, ncols, index)
        return {'nrows': nrows, 'ncols': ncols, 'index': index}

    if isinstance(pos, int):
        s = str(pos)
        if len(s) != 3:
            raise ValueError(f"整数格式必须是3位数字，如 311，当前值: {pos}")
        nrows, ncols, index = int(s[0]), int(s[1]), int(s[2])
        _validate_grid(nrows, ncols, index)
        return {'nrows': nrows, 'ncols': ncols, 'index': index}

    raise ValueError(f"无效的 position 格式: {pos}")


def _convert_string_to_grid(pos: str) -> dict:
    """将字符串格式转换为网格格式"""
    mapping = {
        'left': {'nrows': 1, 'ncols': 2, 'index': 1},
        'right': {'nrows': 1, 'ncols': 2, 'index': 2},
        'top': {'nrows': 2, 'ncols': 1, 'index': 1},
        'bottom': {'nrows': 2, 'ncols': 1, 'index': 2},
    }
    if pos not in mapping:
        raise ValueError(f"无效的字符串 position: {pos}")
    return mapping[pos]


def as_enum(value, string_types):
    """将字符串枚举值转为对应的数值索引。
    :param value: 字符串值（如 'solid'）
    :param string_types: Literal 类型（如 LINE_STYLE）
    :return: 对应索引值，未匹配则返回 -1"""
    types = string_types.__args__
    return -1 if value not in types else types.index(value)


def marker_shape(shape: MARKER_SHAPE):
    """将标记形状名转为 Lightweight Charts 识别的格式。
    :param shape: 如 'arrow_up', 'arrow_down', 'circle', 'square'"""
    return {
        'arrow_up': 'arrowUp',
        'arrow_down': 'arrowDown',
    }.get(shape) or shape


def marker_position(p: MARKER_POSITION):
    """将标记位置名转为 Lightweight Charts 识别的格式。
    :param p: 如 'above', 'below', 'inside', 'atPriceMiddle' 等"""
    return {
        'above' : 'aboveBar',
        'below' : 'belowBar',
        'inside': 'inBar',
        'atPriceMiddle': 'atPriceMiddle',
        'atPriceTop'   : 'atPriceTop',
        'atPriceBottom': 'atPriceBottom',
    }.get(p)


class Emitter:
    """简单的事件发射器，支持同步/异步回调。"""
    def __init__(self):
        self._callable = None

    def __iadd__(self, other):
        """注册回调函数。"""
        self._callable = other
        return self

    def _emit(self, *args):
        """触发事件，自动判断是否异步执行。"""
        if self._callable:
            if inspect.iscoroutinefunction(self._callable):
                asyncio.create_task(self._callable(*args))
            else:
                self._callable(*args)

    def __isub__(self, other):
        """注销回调函数。"""
        if self._callable is other:
            self._callable = None
        return self


class JSEmitter:
    """JS 端事件发射器，将 Python 回调绑定到 JS 窗口事件。"""
    def __init__(self, chart, name, on_iadd, on_isub=None, wrapper=None):
        """
        :param chart: 图表实例
        :param name: 事件名称（同时也是 JS handler 注册名）
        :param on_iadd: 注册时触发的 JS 绑定函数
        :param on_isub: 注销时触发的 JS 解绑函数
        :param wrapper: 可选包装器，用于转换回调参数"""
        self._on_iadd = on_iadd
        self._on_isub = on_isub
        self._chart = chart
        self._name = name
        self._wrapper = wrapper
        # 目前只能增加一个函数回调，不支持多个函数回调，设定个变量，如果多次增加就报错
        self._inited = False

    def __iadd__(self, other):
        """注册回调到 JS 事件。
        :raises ValueError: 如果该事件已注册过回调（仅支持单回调）"""
        if self._inited:
            raise ValueError(f'JSEmitter {self._name} already initialized')

        def final_wrapper(*arg):
            other(self._chart, *arg) if not self._wrapper else self._wrapper(other, self._chart, *arg)
        async def final_async_wrapper(*arg):
            await other(self._chart, *arg) if not self._wrapper else await self._wrapper(other, self._chart, *arg)

        self._chart.win.handlers[self._name] = final_async_wrapper if inspect.iscoroutinefunction(other) else final_wrapper
        self._on_iadd(other)
        self._inited = True
        return self

    def __isub__(self, other):
        """注销回调。"""
        if not self._inited:
            raise ValueError(f'JSEmitter {self._name} not initialized')

        # 它应该在 handlers 里面。如果不是，则代表有意料之外的东西清空了 handlers，此时应该打印警告，而不做任何清理
        if self._name in self._chart.win.handlers:
            if self._on_isub:
                self._on_isub(other)
            del self._chart.win.handlers[self._name]
        else:
            print(f'Warn! JSEmitter {self._name} not found in handlers. Skip resource recycling')

        self._inited = False
        return self


class Events:
    """事件注册中心，管理图表相关的事件（新建 K 线、搜索、范围变化、点击、十字光标移动）。"""
    def __init__(self, chart):
        """
        :param chart: 图表实例，用于绑定 JS 事件回调
        """
        # 如果新的bar被创建，该事件会被触发，注意批量更新导致多个bar创建时，只会触发一次事件
        self.new_bar = Emitter()

        # 搜索事件，该事件注册后，不能删除
        self.search = JSEmitter(chart, f'search{chart.id}',
            on_iadd=lambda o: chart.run_script(f'''
                Lib.Handler.makeSpinner({chart.id})
                {chart.id}.search = Lib.Handler.makeSearchBox({chart.id})
                ''')
        )

        # -------------------------------------------------
        salt = '_' + chart.id[chart.id.index('.')+1:]

        # 可见范围范围改变事件
        self.range_change = JSEmitter(chart, f'range_change{salt}',
            on_iadd=lambda o: chart.run_script(f'''
                window.checkLogicalRange{salt} = (logical) => {{
                    {chart.id}.chart.timeScale().unsubscribeVisibleLogicalRangeChange(window.checkLogicalRange{salt});
                    
                    let barsInfo = {chart.id}.series.barsInLogicalRange(logical);
                    if (barsInfo) window.callbackFunction(`range_change{salt}_~_${{barsInfo.barsBefore}};;;${{barsInfo.barsAfter}}`);
                        
                    setTimeout(() => {chart.id}.chart.timeScale().subscribeVisibleLogicalRangeChange(window.checkLogicalRange{salt}), 50);
                }};
                {chart.id}.chart.timeScale().subscribeVisibleLogicalRangeChange(window.checkLogicalRange{salt});
                '''),
            on_isub=lambda o: chart.run_script(f'''
                {chart.id}.chart.timeScale().unsubscribeVisibleLogicalRangeChange(window.checkLogicalRange{salt})
                '''),
            wrapper=lambda o, c, *arg: o(c, *[float(a) for a in arg])
        )

        # 鼠标点击事件
        self.click = JSEmitter(chart, f'subscribe_click{salt}',
            on_iadd=lambda o: chart.run_script(f'''
                window.clickHandler{salt} = (param) => {{
                    if (!param.point) return;
                    const time = {chart.id}.chart.timeScale().coordinateToTime(param.point.x)
                    const price = {chart.id}.series.coordinateToPrice(param.point.y);
                    window.callbackFunction(`subscribe_click{salt}_~_${{time}};;;${{price}}`)
                }};
                {chart.id}.chart.subscribeClick(window.clickHandler{salt});
                '''),
            on_isub=lambda o: chart.run_script(f'''
                {chart.id}.chart.unsubscribeClick(window.clickHandler{salt})
                '''),
            wrapper=lambda func, c, *args: func(c, *[float(a) if a != 'null' else None for a in args])
        )

        # 十字光标移动事件
        self.crosshair_move = JSEmitter(chart, f'crosshair_move{salt}',
            on_iadd=lambda o: chart.run_script(f'''
                window.crosshairHandler{salt} = (param) => {{
                    if (!param.point) return;
                    let payload = {{time: null, price: null}};
                    if (param.time !== undefined) {{
                        payload.time = param.time;
                    }};
                    if (param.point) {{
                        let price = {chart.id}.series.coordinateToPrice(param.point.y);
                        payload.price = price;
                    }};
                    window.callbackFunction(`crosshair_move{salt}_~_${{JSON.stringify(payload)}}`);
                }};
                {chart.id}.chart.subscribeCrosshairMove(window.crosshairHandler{salt});
                '''),
            on_isub=lambda o: chart.run_script(f'''
                {chart.id}.chart.unsubscribeCrosshairMove(window.crosshairHandler{salt});
                '''),
            # delete window.crosshairHandler{salt};
            wrapper=lambda func, c, *args: func(c, json.loads(args[0]) if args else {})
        )


class BulkRunScript:
    """批量脚本执行上下文管理器，暂存多条 JS 脚本并在退出时一次性拼接执行。"""
    def __init__(self, script_func):
        """
        :param script_func: 执行 JS 的函数（接收字符串参数）
        """
        self.enabled = False
        self.scripts = []
        self.script_func = script_func

    def __enter__(self):
        """进入批量模式，后续 add_script 加入到缓冲区。"""
        self.enabled = True

    def __exit__(self, *args):
        """退出批量模式，一次性执行所有缓冲脚本。"""
        self.enabled = False
        self.script_func('\n'.join(self.scripts))
        self.scripts = []

    def add_script(self, script):
        """添加一条 JS 脚本到缓冲区。
        :param script: JS 代码字符串"""
        self.scripts.append(script)


# ── 数据工具纯函数（从 SeriesCommon 提取）──

def get_df_interval_offset(df: pd.DataFrame) -> (int, int):
    """获取数据 DF 内时间点的通常间隔（秒）。

    :param df: 标准化后的 DataFrame，time 列为秒级时间戳
    :return: (interval 秒, offset 秒)
    """

    if df['time'].dtype not in (np.int64, np.float64):
        raise ValueError('请先使用 normal_df 对输入进行标准化')

    time_df = pd.to_datetime(df['time'], unit='s')

    common_interval = time_df.diff().value_counts(sort=True, ascending=False, dropna=True)
    if common_interval.empty:
        raise AssertionError("No common interval found.")

    interval = common_interval.index[0].total_seconds()

    units = [
        pd.Timedelta(microseconds=time_df.dt.microsecond.value_counts().index[0]),
        pd.Timedelta(seconds=time_df.dt.second.value_counts().index[0]),
        pd.Timedelta(minutes=time_df.dt.minute.value_counts().index[0]),
        pd.Timedelta(hours=time_df.dt.hour.value_counts().index[0]),
        pd.Timedelta(days=time_df.dt.day.value_counts().index[0]),
    ]
    offset = 0
    for value in units:
        value = value.total_seconds()
        if value == 0:
            continue
        elif value >= interval:
            break
        offset = value
        break

    return interval, offset


def normal_df(df: pd.DataFrame, required_cols: Optional[list[str]] = None) -> pd.DataFrame:
    """标准化输入 DataFrame。

    - 无 time 列时用 index
    - 时间转换为秒级时间戳

    注意：不再自动将列名转为小写，也不再自动将 date 列重命名为 time。
    输入 DataFrame 的列名必须已经是正确的小写形式（如 time, open, high, low, close, value）。

    :param df: 输入 DataFrame
    :param required_cols: 必需列名列表，并且按照顺序排列，None 则不检查
    :return: 标准化后的 DataFrame（副本）
    """
    df = df.copy()
    # 检查 time 列是否存在 和 按需转换时间到 秒级时间戳
    if 'time' not in df.columns:
        df['time'] = df.index

    if df['time'].dtype in (np.int64, np.float64):
        pass
    else:
        df['time'] = pd.to_datetime(df['time'], unit='s').dt.tz_localize(None)
        df['time'] = (df['time'] - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')
    # ------------------------------------------
    # 检查必需列是否存在，并按顺序取出
    if required_cols is not None:
        missing = set(required_cols) - set(df.columns)
        if missing:
            raise ValueError(f"缺少必需列: {missing}")
        df = df[list(required_cols)]
    # ------------------------------------------
    return df


def time_to_bar_time(data, offset: int, interval: int):
    """将时间戳对齐到 bar 时间边界。

    :param data: 时间值（int/float/Series/DataFrame）
    :param offset: 时间偏移（秒）
    :param interval: 时间间隔（秒）
    :return: 对齐后的时间值
    """
    if isinstance(data, pd.DataFrame):
        data["time"] = np.int64((data["time"].array - offset) // interval * interval + offset)
        return data
    else:
        r = (data - offset) // interval * interval + offset
        if isinstance(data, pd.Series):
            return r.astype(np.int64)
        else:
            return int(r)


def filter_old_bars(df: pd.DataFrame, last_bar_time=None) -> pd.DataFrame:
    """丢弃 time < last_bar_time 的数据，并检查单调递增。

    :param df: 包含 time 列的 DataFrame
    :param last_bar_time: 上一根 bar 的时间戳（int/float），None 则跳过过滤
    :return: 过滤后的 DataFrame
    """
    if df.empty:
        return df

    if len(df) > 1 and not df['time'].is_monotonic_increasing:
        raise ValueError("Time column must be monotonic increasing.")

    if last_bar_time is not None:
        mask = df['time'] >= last_bar_time
        n_drop = len(mask) - mask.sum()
        if n_drop > 0:
            print(f'Warning! Drop {n_drop} lines because earlier than _last_bar.')
        df = df[mask]

    return df


def merge_volume_by_time(df: pd.DataFrame, is_tick: bool = False) -> pd.DataFrame:
    """按 time 合并 volume 数据。

    :param df: 输入 DataFrame
    :param is_tick: False = bar 模式（输入 time/value/open/close）
                    True  = tick 模式（输入 time/value/price）
    :return: time, value, open, close
    """
    if is_tick:
        # 特别注意，tick 模式下，value 取的是每个时间的总和
        required = {'time', 'value', 'price'}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"tick 模式缺少必需列: {missing}")

        grouped = df.groupby('time')
        new_df = pd.DataFrame({
            'time': list(grouped.groups),
            'value': grouped['value'].sum().array,
            'open': grouped['price'].first().array,
            'close': grouped['price'].last().array,
        })
        return new_df

    else:
        # 特别注意，bar模式的 value 取的是每个时间的最后一个值
        required = {'time', 'value', 'open', 'close'}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"bar 模式缺少必需列: {missing}")

        grouped = df.groupby('time')
        new_df = pd.DataFrame({
            'time': list(grouped.groups),
            'value': grouped['value'].last().array,
            'open': grouped['open'].first().array,
            'close': grouped['close'].last().array,

        })
        return new_df


def merge_candle_by_time(df: pd.DataFrame, is_tick: bool = False) -> pd.DataFrame:
    """按 time 合并 candle (OHLC) 数据。

    :param df: 输入 DataFrame
    :param is_tick: False = bar 模式（输入 time/open/high/low/close）
                    True  = tick 模式（输入 time/value，聚合为 OHLC）
    :return: time, open, high, low, close
    """
    if is_tick:
        required = {'time', 'value'}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"tick 模式缺少必需列: {missing}")

        grouped = df.groupby('time')
        new_df = pd.DataFrame({
            "time": list(grouped.groups),
            "open": grouped['value'].first().array,
            "high": grouped['value'].max().array,
            "low": grouped['value'].min().array,
            "close": grouped['value'].last().array
        })
        return new_df

    else:
        required = {'time', 'open', 'high', 'low', 'close'}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"bar 模式缺少必需列: {missing}")

        grouped = df.groupby('time')
        new_df = pd.DataFrame({
            "time": list(grouped.groups),
            "open": grouped['open'].first().array,
            "high": grouped['high'].max().array,
            "low": grouped['low'].min().array,
            "close": grouped['close'].last().array
        })
        return new_df


def merge_value_by_time(df: pd.DataFrame) -> pd.DataFrame:
    """合并同样时间戳的 bar。

    :param df: 包含 time 列的 DataFrame
    :return: 合并后的 DataFrame
    """
    group_df = df.groupby('time')

    new_df = pd.DataFrame({
        'time': list(group_df.groups)
    })

    if 'open' in df.columns:
        new_df['open'] = group_df['open'].first().array
        if 'high' in df.columns:
            new_df['high'] = group_df['high'].max().array
        if 'low' in df.columns:
            new_df['low'] = group_df['low'].min().array
        new_df['close'] = group_df['close'].last().array

    if 'volume' in df.columns:
        new_df['volume'] = group_df['volume'].sum().array

    if 'open_interest' in df.columns:
        new_df['open_interest'] = group_df['open_interest'].last().array

    # 除了目标的对象，其他都是取last
    for col in set(df.columns).difference({'time', 'open', 'high', 'low', 'close', 'volume', 'open_interest'}):
        new_df[col] = group_df[col].last().array

    return new_df
