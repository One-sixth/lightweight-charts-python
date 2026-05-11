import asyncio
import ast
import inspect
import multiprocessing as mp
from queue import Empty
import typing
from pprint import pp

import webview
from webview.errors import JavascriptException

from . import abstract
from .util import parse_event_message, FLOAT


class CallbackAPI:
    """pywebview JS 回调 API，接收 JS 端 emit 的消息。"""
    def __init__(self, emit_queue):
        """
        :param emit_queue: 消息队列，用于从 JS 端接收回调事件
        """
        self.emit_queue = emit_queue

    def callback(self, message: str):
        """接收 JS 端发来的消息并放入队列。"""
        self.emit_queue.put(message)


class PyWV:
    """pywebview 窗口进程，运行在独立子进程中处理窗口生命周期和 JS 求值。"""
    def __init__(self, q, emit_q, return_q, loaded_event):
        """
        :param q: 函数调用队列（接收主进程的指令）
        :param emit_q: 事件发射队列（向主进程发送回调）
        :param return_q: 返回值队列（JS 求值结果）
        :param loaded_event: 窗口加载完成事件
        """
        self.queue = q
        self.return_queue = return_q
        self.emit_queue = emit_q
        self.loaded_event = loaded_event

        self.is_alive = True

        self.callback_api = CallbackAPI(emit_q)
        self.windows: typing.List[webview.Window] = []
        self.loop()


    def create_window(
        self, width, height, x, y, screen=None, on_top=False,
        maximize=False, title=''
    ):
        """创建一个 pywebview 窗口。"""
        screen = webview.screens[screen] if screen is not None else None
        if maximize:
            if screen is None:
                active_screen = webview.screens[0]
                width, height = active_screen.width, active_screen.height
            else:
                width, height = screen.width, screen.height

        self.windows.append(webview.create_window(
            title,
            url=abstract.INDEX,
            js_api=self.callback_api,
            width=width,
            height=height,
            x=x,
            y=y,
            screen=screen,
            on_top=on_top,
            background_color='#000000')
        )

        self.windows[-1].events.loaded += lambda: self.loaded_event.set()
        self.windows[-1].events.closed += lambda: setattr(self, 'is_alive', False)


    def loop(self):
        """主事件循环，处理来自队列的指令并执行对应 JS 操作。"""

        # self.loaded_event.set()
        while self.is_alive:
            i, arg = self.queue.get()
            if not self.is_alive:
                return

            if i == 'start':
                webview.start(debug=arg, func=self.loop)
                self.is_alive = False
                self.emit_queue.put('exit')
                return
            if i == 'create_window':
                self.create_window(*arg)
                continue

            window = self.windows[i]
            if arg == 'show':
                window.show()
            elif arg == 'hide':
                window.hide()
            else:
                try:
                    if '_~_~RETURN~_~_' in arg:
                        result = window.evaluate_js(arg[14:])
                        self.return_queue.put(result)
                    else:
                        window.evaluate_js(arg)
                except KeyError as e:
                    return
                except JavascriptException as e:
                    # msg = eval(str(e))
                    msg = str(e)
                    pp(msg)
                    if '_~_~RETURN~_~_' in arg:
                        self.return_queue.put(None)
                except Exception:
                    if '_~_~RETURN~_~_' in arg:
                        self.return_queue.put(None)
                    return


class WebviewHandler():
    """pywebview 进程管理器，负责窗口进程的启动、通信和生命周期管理。"""
    def __init__(self) -> None:
        self._reset()
        self.debug = False

    def _reset(self):
        self.loaded_event = mp.Event()
        self.return_queue = mp.Queue()
        self.function_call_queue = mp.Queue()
        self.emit_queue = mp.Queue()
        self.wv_process = mp.Process(
            target=PyWV, args=(
                self.function_call_queue, self.emit_queue,
                self.return_queue, self.loaded_event
            ),
            daemon=True
        )
        self.max_window_num = -1

    def create_window(
        self, width, height, x, y, screen=None, on_top=False,
        maximize=False, title=''
    ):
        """向窗口进程发送创建窗口指令，返回窗口编号。"""
        self.function_call_queue.put((
            'create_window', (width, height, x, y, screen, on_top, maximize, title)
        ))
        self.max_window_num += 1
        return self.max_window_num

    def start(self):
        """启动窗口进程并等待加载完成。"""
        self.loaded_event.clear()
        self.wv_process.start()
        self.function_call_queue.put(('start', self.debug))
        self.loaded_event.wait()

    def show(self, window_num):
        """显示指定编号的窗口。"""
        self.function_call_queue.put((window_num, 'show'))

    def hide(self, window_num):
        """隐藏指定编号的窗口。"""
        self.function_call_queue.put((window_num, 'hide'))

    def evaluate_js(self, window_num, script):
        """在指定窗口中执行 JS 脚本。"""
        self._raise_exit_if_destroyed()
        self.function_call_queue.put((window_num, script))

    def _clear_all_queue(self):
        # 清理所有队列，只能在结束时调用
        for q in (self.function_call_queue, self.emit_queue, self.return_queue):
            # 要主动清空队列，否则会阻塞，导致进程在结束时会卡住
            try:
                while True:
                    q.get_nowait()
            except Empty:
                pass
            q.close()
            q.join_thread()

    def _raise_exit_if_destroyed(self):
        # 仅在出错时调用
        if self.wv_process.is_alive():
            return

        self.wv_process.join(timeout=2)
        self._clear_all_queue()
        raise RuntimeError("Chart window has been destroyed. Cannot execute script.")

    def exit(self):
        """终止窗口进程并清理所有队列。"""
        if self.wv_process.is_alive():
            self.wv_process.terminate()
            self.wv_process.join()
        self._clear_all_queue()
        self._reset()


class Chart(abstract.AbstractChart):
    """桌面窗口图表，基于 pywebview 实现。"""

    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        x: int = None,
        y: int = None,
        title: str = '',
        screen: int = None,
        on_top: bool = False,
        maximize: bool = False,
        debug: bool = False,
        toolbox: bool = False,
        inner_width: float = 1.0,
        inner_height: float = 1.0,
        scale_candles_only: bool = False,
        position: FLOAT = 'left',
        marker_auto_scale: bool = True
    ):
        self.wv = WebviewHandler()
        self.wv.debug = debug
        self._i = self.wv.create_window(
                    width, height, x, y, screen, on_top, maximize, title
                )

        window = abstract.Window(
                    script_func=lambda s: self.wv.evaluate_js(self._i, s),
                    js_api_code='pywebview.api.callback'
                )

        window._return_q = self.wv.return_queue

        self.is_alive = True

        super().__init__(window, inner_width, inner_height, scale_candles_only, toolbox, position=position, marker_auto_scale=marker_auto_scale)

    def show(self, block: bool = False):
        """
        Shows the chart window.\n
        :param block: blocks execution until the chart is closed.
        """
        if not self.win.loaded:
            self.wv.start()
            self.win.on_js_load()
        else:
            self.wv.show(self._i)
        if block:
            asyncio.run(self.show_async())

    async def show_async(self):
        """异步主循环，处理 JS 回调事件直到窗口关闭。"""
        self.show(block=False)
        try:
            from . import polygon
            [asyncio.create_task(self.polygon.async_set(*args)) for args in polygon._set_on_load]
            while 1:
                while self.wv.emit_queue.empty() and self.is_alive:
                    await asyncio.sleep(0.05)
                if not self.is_alive:
                    return
                response = self.wv.emit_queue.get()
                if response == 'exit':
                    self.wv.exit()
                    self.is_alive = False
                    self.win.destroyed = True
                    return
                else:
                    func, args = parse_event_message(self.win, response)
                    await func(*args) if inspect.iscoroutinefunction(func) else func(*args)
        except KeyboardInterrupt:
            return

    def hide(self):
        """
        Hides the chart window.\n
        """
        self.wv.function_call_queue.put((self._i, 'hide'))

    def exit(self):
        """
        Exits and destroys the chart window.\n
        """
        self.wv.exit()
        self.is_alive = False
        self.win.destroyed = True
