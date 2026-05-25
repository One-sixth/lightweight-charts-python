import asyncio
import json
import inspect
import warnings
from datetime import datetime
from zoneinfo import ZoneInfo
from tzlocal import get_localzone_name
from typing import Literal, Union, Tuple
import pandas as pd


class Pane:
    """所有可放置在图表上的组件的基类。自动分配唯一 ID 并持有窗口引用。"""
    def __init__(self, window, prefix=''):
        from .abstract import Window
        self.win: Window = window
        self.run_script = window.run_script
        self.bulk_run = window.bulk_run
        if hasattr(self, 'id'):
            return
        self.id = Window._id_gen.generate(f'{type(self).__name__}_')


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
        # tz = ZoneInfo(get_localzone_name())
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
    func = window.handlers[name]
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


def jbool(b: bool): return 'true' if b is True else 'false' if b is False else None


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


def parse_position(pos: Position, chart_count: int = 1) -> dict:
    """
    解析 position 参数为统一格式
    :param pos: 位置参数
    :param chart_count: 当前图表数量（用于字符串格式转换）
    :return: {'nrows': 3, 'ncols': 1, 'index': 1}
    """
    if isinstance(pos, str):
        # 字符串格式支持 Chart() 和 create_subchart()
        if pos not in ('left', 'right', 'top', 'bottom'):
            raise ValueError(f"无效的字符串 position: {pos}")
        
        # 超过 2 个图表时不支持字符串格式
        if chart_count > 2:
            raise ValueError(
                f"超过2个图表时不支持字符串格式 position='{pos}'，"
                f"请使用数字格式，如 position=111 或 position=(2,2,1)"
            )
        
        # 单个图表时字符串没有实际意义，不发出警告
        if chart_count > 1:
            warnings.warn(
                f"字符串格式 position='{pos}' 已弃用，请使用数字格式，如 position=111",
                DeprecationWarning,
                stacklevel=2
            )
        return _convert_string_to_grid(pos, chart_count)
    
    elif isinstance(pos, tuple) and len(pos) == 3:
        nrows, ncols, index = pos
        if not all(isinstance(x, int) and x > 0 for x in (nrows, ncols, index)):
            raise ValueError("nrows, ncols, index 必须是正整数")
        if index > nrows * ncols:
            raise ValueError(f"index {index} 超出网格范围 {nrows}x{ncols}={nrows*ncols}")
        return {'nrows': nrows, 'ncols': ncols, 'index': index}
    
    elif isinstance(pos, int):
        s = str(pos)
        if len(s) != 3:
            raise ValueError(f"整数格式必须是3位数字，如 311")
        nrows = int(s[0])
        ncols = int(s[1])
        index = int(s[2])
        if nrows == 0 or ncols == 0:
            raise ValueError("行数和列数不能为0")
        if index == 0:
            raise ValueError(f"位置索引不能为0，必须是 1-{nrows*ncols}")
        if index > nrows * ncols:
            raise ValueError(f"index {index} 超出网格范围 {nrows}x{ncols}={nrows*ncols}")
        return {'nrows': nrows, 'ncols': ncols, 'index': index}
    
    else:
        raise ValueError(f"无效的 position 格式: {pos}")


def _convert_string_to_grid(pos: str, chart_count: int) -> dict:
    """将字符串格式转换为网格格式（仅支持 1-2 个图表）"""
    if chart_count == 1:
        # 单个图表：1行1列
        return {'nrows': 1, 'ncols': 1, 'index': 1}
    
    elif chart_count == 2:
        # 两个图表
        if pos in ('left', 'right'):
            # 左右布局：1行2列
            index = 1 if pos == 'left' else 2
            return {'nrows': 1, 'ncols': 2, 'index': index}
        else:
            # 上下布局：2行1列
            index = 1 if pos == 'top' else 2
            return {'nrows': 2, 'ncols': 1, 'index': index}
    
    else:
        raise ValueError("字符串格式仅支持 1-2 个图表")


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
