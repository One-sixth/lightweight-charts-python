import asyncio
import json
import multiprocessing as mp
from queue import Empty
import typing
from pprint import pp

import webview
from webview.errors import JavascriptException

from . import abstract
from .util import parse_event_message, FLOAT


class CallbackAPI:
    def __init__(self, emit_queue):
        self.emit_queue = emit_queue

    def callback(self, message: str):
        self.emit_queue.put(message)


class PyWV:

    def __init__(self, q, emit_q, return_q, loaded_event):
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
                    msg = eval(str(e))
                    pp(msg)
                    if '_~_~RETURN~_~_' in arg:
                        self.return_queue.put(None)
                except Exception:
                    if '_~_~RETURN~_~_' in arg:
                        self.return_queue.put(None)
                    return


class WebviewHandler():
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
        self.function_call_queue.put((
            'create_window', (width, height, x, y, screen, on_top, maximize, title)
        ))
        self.max_window_num += 1
        return self.max_window_num

    def start(self):
        self.loaded_event.clear()
        self.wv_process.start()
        self.function_call_queue.put(('start', self.debug))
        self.loaded_event.wait()

    def show(self, window_num):
        self.function_call_queue.put((window_num, 'show'))

    def hide(self, window_num):
        self.function_call_queue.put((window_num, 'hide'))

    def evaluate_js(self, window_num, script):
        self._raise_exit_if_destroyed()
        self.function_call_queue.put((window_num, script))

    def _raise_exit_if_destroyed(self):
        # 仅在出错时调用
        if self.wv_process.is_alive():
            return

        self.wv_process.join(timeout=2)
        for q in (self.function_call_queue, self.emit_queue, self.return_queue):
            # 要主动清空队列，否则会阻塞，导致进程在结束时会卡住
            try:
                while True:
                    q.get_nowait()
            except Empty:
                pass
            q.close()
            q.join_thread()
        raise RuntimeError("Chart window has been destroyed. Cannot execute script.")

    def exit(self):
        if self.wv_process.is_alive():
            self.wv_process.terminate()
            self.wv_process.join()
        self._reset()


class Chart(abstract.AbstractChart):

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
        position: FLOAT = 'left'
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

        super().__init__(window, inner_width, inner_height, scale_candles_only, toolbox, position=position)

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
                    await func(*args) if asyncio.iscoroutinefunction(func) else func(*args)
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
