import asyncio
import json
import inspect
from datetime import datetime
from zoneinfo import ZoneInfo
from tzlocal import get_localzone_name
from typing import Literal, Union
import pandas as pd


class Pane:
    def __init__(self, window, prefix=''):
        from .abstract import Window
        self.win: Window = window
        self.run_script = window.run_script
        self.bulk_run = window.bulk_run
        if hasattr(self, 'id'):
            return
        self.id = Window._id_gen.generate(f'{type(self).__name__}_')


class IDGen:
    def __init__(self):
        self._counter = 0

    def generate(self, prefix: str = '') -> str:
        self._counter += 1
        return f'window.{prefix}{self._counter}'

def format_datetime(dt: datetime, tz: Union[str, ZoneInfo] = None) -> str:
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
    name, args = string.split('_~_')
    args = args.split(';;;')
    func = window.handlers[name]
    return func, args

def df_data(data: Union[pd.DataFrame, pd.Series]):
    if isinstance(data, pd.DataFrame):
        d = data.to_dict(orient='records')
        filtered_records = [{k: v for k, v in record.items() if v is not None and not pd.isna(v)} for record in d]
    else:
        d = data.to_dict()
        filtered_records = {k: v for k, v in d.items()}
    return filtered_records

def series_data(data: Union[pd.DataFrame, pd.Series]):
    filtered_records = []
    for idx, val in data.items():
        if isinstance(val, float):
            val_str = f'{val:.4f}'
        else:
            val_str = str(val)
        filtered_records.append({'index': idx, 'value': val_str})
    return filtered_records

def js_data(data: Union[pd.DataFrame, pd.Series]):
    if isinstance(data, pd.DataFrame):
        d = data.to_dict(orient='records')
        filtered_records = [{k: v for k, v in record.items() if v is not None and not pd.isna(v)} for record in d]
    else:
        d = data.to_dict()
        filtered_records = {k: v for k, v in d.items()}
    return json.dumps(filtered_records)

def snake_to_camel(s: str):
    components = s.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def js_json(d: dict):
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


def as_enum(value, string_types):
    types = string_types.__args__
    return -1 if value not in types else types.index(value)


def marker_shape(shape: MARKER_SHAPE):
    return {
        'arrow_up': 'arrowUp',
        'arrow_down': 'arrowDown',
    }.get(shape) or shape


def marker_position(p: MARKER_POSITION):
    return {
        'above' : 'aboveBar',
        'below' : 'belowBar',
        'inside': 'inBar',
        'atPriceMiddle': 'atPriceMiddle',
        'atPriceTop'   : 'atPriceTop',
        'atPriceBottom': 'atPriceBottom',
    }.get(p)


class Emitter:
    def __init__(self):
        self._callable = None

    def __iadd__(self, other):
        self._callable = other
        return self

    def _emit(self, *args):
        if self._callable:
            if inspect.iscoroutinefunction(self._callable):
                asyncio.create_task(self._callable(*args))
            else:
                self._callable(*args)

    def __isub__(self, other):
        if self._callable is other:
            self._callable = None
        return self


class JSEmitter:
    def __init__(self, chart, name, on_iadd, on_isub=None, wrapper=None):
        self._on_iadd = on_iadd
        self._on_isub = on_isub
        self._chart = chart
        self._name = name
        self._wrapper = wrapper
        # 目前只能增加一个函数回调，不支持多个函数回调，设定个变量，如果多次增加就报错
        self._inited = False

    def __iadd__(self, other):
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
    def __init__(self, chart):
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
        print(f'delete window.crosshairHandler{salt};')

class BulkRunScript:
    def __init__(self, script_func):
        self.enabled = False
        self.scripts = []
        self.script_func = script_func

    def __enter__(self):
        self.enabled = True

    def __exit__(self, *args):
        self.enabled = False
        self.script_func('\n'.join(self.scripts))
        self.scripts = []

    def add_script(self, script):
        self.scripts.append(script)
