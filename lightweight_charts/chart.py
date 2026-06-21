import asyncio
import ast
import inspect
import multiprocessing as mp
import os
import sys
from queue import Empty
import typing
from typing import Optional, Union
from pprint import pp

import webview
from webview.errors import JavascriptException

from . import abstract
from .util import parse_event_message, FLOAT, Position


def _get_native_handle(window):
    """获取 pywebview 窗口的原生句柄（跨平台）。

    Windows: 返回 HWND (int)
    Linux/X11: 返回 X11 Window ID (int)
    其他平台: 抛出 OSError
    """
    if os.name == 'nt':
        return window.native.Handle.ToInt32()

    if sys.platform.startswith('linux'):
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        if session_type == 'wayland':
            raise OSError(
                'CrossProcessChart does not work under Wayland. '
                'Use X11 instead (set QT_QPA_PLATFORM=xcb).'
            )
        try:
            import gi
            gi.require_version('GdkX11', '3.0')
            from gi.repository import GdkX11
            gdk_window = window.native.get_window()
            return gdk_window.get_xid()
        except ImportError:
            raise OSError(
                'Linux/X11 support requires PyGObject and GdkX11. '
                'Install with: pip install PyGObject'
            )

    raise OSError(f'CrossProcessChart is not supported on {sys.platform}')


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
        maximize=False, title='', frameless=False
    ):
        """创建一个 pywebview 窗口。"""
        screen = webview.screens[screen] if screen is not None else None
        if maximize:
            if screen is None:
                active_screen = webview.screens[0]
                width, height = active_screen.width, active_screen.height
            else:
                width, height = screen.width, screen.height

        kwargs = dict(
            title=title,
            url=abstract.INDEX,
            js_api=self.callback_api,
            width=width,
            height=height,
            x=x,
            y=y,
            screen=screen,
            on_top=on_top,
            background_color='#000000',
        )
        if frameless:
            kwargs['frameless'] = True
            kwargs['easy_drag'] = False
        self.windows.append(webview.create_window(**kwargs))

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
            elif arg == '_~_~NATIVE_HANDLE~_~_':
                try:
                    hwnd = _get_native_handle(window)
                except Exception:
                    hwnd = None
                self.return_queue.put(hwnd)
                continue
            elif arg.startswith('_~_~RESIZE~_~_'):
                try:
                    w, h = arg[14:].split(',')
                    window.resize(int(w), int(h))
                except Exception:
                    pass
                continue
            else:
                try:
                    if '_~_~RETURN~_~_' in arg:
                        result = window.evaluate_js(arg[14:])
                        self.return_queue.put(result)
                    else:
                        window.evaluate_js(arg)
                except KeyError as e:
                    pp(f'[FATAL] KeyError in message loop: {e}')
                    if '_~_~RETURN~_~_' in arg:
                        self.return_queue.put(None)
                    break
                except JavascriptException as e:
                    msg = str(e)
                    pp(msg)
                    if '_~_~RETURN~_~_' in arg:
                        self.return_queue.put(None)
                except Exception as e:
                    pp(f'[FATAL] Unknown exception in message loop: {type(e).__name__}: {e}')
                    if '_~_~RETURN~_~_' in arg:
                        self.return_queue.put(None)
                    break


class WebviewHandler:
    """pywebview 进程管理器，负责窗口进程的启动、通信和生命周期管理。"""
    def __init__(self) -> None:
        self.debug = False
        self._inited = False
        self._destroyed = False

        self.loaded_event = None
        self.return_queue = None
        self.function_call_queue = None
        self.emit_queue = None
        self.wv_process = None
        self.max_window_num = None

        self.init()

    def init(self):
        if self._destroyed:
            raise RuntimeError('WebviewHandler is destroyed. Cannot initialize again.')
        if self._inited:
            raise RuntimeError('WebviewHandler is already initialized.')

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
        self._inited = True

    def create_window(
        self, width, height, x, y, screen=None, on_top=False,
        maximize=False, title='', frameless=False
    ):
        """向窗口进程发送创建窗口指令，返回窗口编号。"""
        self.function_call_queue.put((
            'create_window', (width, height, x, y, screen, on_top, maximize, title, frameless)
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

    def get_native_handle(self, window_num, timeout=10.0):
        """获取指定窗口的原生句柄（Windows: HWND, Linux/X11: X11 Window ID）。"""
        self._raise_exit_if_destroyed()
        self.function_call_queue.put((window_num, '_~_~NATIVE_HANDLE~_~_'))
        import time as _time
        deadline = _time.time() + timeout
        while _time.time() < deadline:
            try:
                result = self.return_queue.get_nowait()
                return result
            except Empty:
                _time.sleep(0.02)
        raise TimeoutError("get_native_handle timed out")

    def resize_window(self, window_num, width, height):
        """调整指定窗口的大小。"""
        self.function_call_queue.put((window_num, f'_~_~RESIZE~_~_{width},{height}'))

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
        if self._destroyed:
            return
        if not self._inited:
            return

        """终止窗口进程并清理所有队列。"""
        if self.wv_process.is_alive():
            self.wv_process.terminate()
            self.wv_process.join()
        self._clear_all_queue()
        self._destroyed = True


class Chart(abstract.AbstractChart):
    """桌面窗口图表，基于 pywebview 实现。

    这是 lightweight-charts-python 的核心图表类，提供完整的交互式图表功能，
    包括 K线显示、技术指标、绘图工具、事件回调等。

    Example:
        >>> chart = Chart(width=1000, height=600, title='My Chart')
        >>> chart.set(df)
        >>> chart.show(block=True)
    """

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
        position: Position = 111,
        marker_auto_scale: bool = True,
        frameless: bool = False,
        sync_id: Optional[Union[str, bool]] = None,
        sync_crosshairs_only: bool = False,
    ):
        """
        :param width: 窗口宽度（像素），默认 800
        :param height: 窗口高度（像素），默认 600
        :param x: 窗口左上角 X 坐标（像素），None 表示居中
        :param y: 窗口左上角 Y 坐标（像素），None 表示居中
        :param title: 窗口标题，默认为空字符串
        :param screen: 多显示器环境下的屏幕索引，None 表示主屏幕
        :param on_top: 是否置顶显示，默认 False
        :param maximize: 是否最大化窗口，默认 False
        :param debug: 是否启用调试模式（输出 JS 错误信息），默认 False
        :param toolbox: 是否启用绘图工具箱，默认 False
        :param inner_width: 图表在窗口内的宽度比例（0.0-1.0），默认 1.0
        :param inner_height: 图表在窗口内的高度比例（0.0-1.0），默认 1.0
        :param scale_candles_only: 缩放时是否仅依据 K线范围，默认 False
        :param position: 图表位置（网格格式），支持三种格式：
                        - 整数：如 111（百位=行数，十位=列数，个位=位置索引）
                        - 元组：如 (2, 2, 1)（行数, 列数, 位置索引）
                        - 字符串：'left', 'right', 'top', 'bottom'（已弃用）
        :param marker_auto_scale: 标记是否参与价格轴自动缩放，默认 True
        :param frameless: 是否无边框窗口，默认 False
        :param sync_id: 同步组名（str/True/False/None），同名组内的图表自动同步。None 或 False 表示不同步，True 转为字符串 'True' 作为组名
        :param sync_crosshairs_only: True 则仅同步十字光标，不同步时间范围（需配合 sync_id 使用）
        """
        self.wv = WebviewHandler()
        self.wv.debug = debug
        self._i = self.wv.create_window(
                    width, height, x, y, screen, on_top, maximize, title,
                    frameless=frameless
                )

        window = abstract.Window(
                    script_func=lambda s: self.wv.evaluate_js(self._i, s),
                    js_api_code='pywebview.api.callback'
                )

        window._return_q = self.wv.return_queue

        self.is_alive = True

        super().__init__(window, inner_width, inner_height, scale_candles_only, toolbox, position=position, marker_auto_scale=marker_auto_scale)

        # 如果指定了 sync_id，加入同步组
        if sync_id:
            self.join_sync_group(sync_id, sync_crosshairs_only)

    def show(self, block: bool = False):
        """
        显示图表窗口。

        :param block: 如果为 True，阻塞当前线程直到窗口关闭；
                     如果为 False，窗口显示后立即返回，适用于异步场景。
        :type block: bool

        Example:
            >>> chart.show()  # 非阻塞模式
            >>> chart.show(block=True)  # 阻塞模式，等待窗口关闭
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
                    if func is not None:
                        await func(*args) if inspect.iscoroutinefunction(func) else func(*args)
        except KeyboardInterrupt:
            return

    def hide(self):
        """
        隐藏图表窗口（不销毁）。

        窗口被隐藏后可以通过再次调用 show() 重新显示。
        """
        self.wv.function_call_queue.put((self._i, 'hide'))

    def exit(self):
        """
        退出并销毁图表窗口。

        关闭窗口并释放所有相关资源，包括：
        - 停止 pywebview 进程
        - 设置 is_alive 为 False
        - 标记窗口已销毁

        调用此方法后，图表对象将不再可用。
        """
        self.wv.exit()
        self.is_alive = False
        self.win.destroyed = True


class CrossProcessChart:
    """跨进程图表：将 pywebview 窗口嵌入到 Qt Widget 中。

    支持 Windows 和 Linux/X11。图表运行在独立子进程中（pywebview），
    通过原生窗口句柄嵌入到 Qt 布局中，类似 Chrome 多进程窗口嵌入。
    不支持 Wayland 和 macOS。

    所有 AbstractChart 方法（set, update, marker, create_line 等）
    均通过委托转发给内部的 Chart 实例。

    Example:
        >>> from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
        >>> import sys
        >>>
        >>> app = QApplication(sys.argv)
        >>> parent = QWidget()
        >>> layout = QVBoxLayout(parent)
        >>>
        >>> chart = CrossProcessChart(parent, width=800, height=600)
        >>> layout.addWidget(chart.widget)
        >>>
        >>> parent.show()
        >>> chart.set(df)
        >>> app.exec()
    """

    def __init__(
        self,
        parent=None,
        width: int = 800,
        height: int = 600,
        inner_width: float = 1.0,
        inner_height: float = 1.0,
        scale_candles_only: bool = False,
        toolbox: bool = False,
        title: str = '',
        debug: bool = False,
        position: Position = 111,
        marker_auto_scale: bool = True
    ):
        """
        :param parent: 父 Qt 控件，用于嵌入布局，默认为 None
        :type parent: QWidget or None
        :param width: 窗口宽度（像素），默认 800
        :type width: int
        :param height: 窗口高度（像素），默认 600
        :type height: int
        :param inner_width: 图表在窗口内的宽度比例（0.0-1.0），默认 1.0
        :type inner_width: float
        :param inner_height: 图表在窗口内的高度比例（0.0-1.0），默认 1.0
        :type inner_height: float
        :param scale_candles_only: 缩放时是否仅依据 K线范围，默认 False
        :type scale_candles_only: bool
        :param toolbox: 是否启用绘图工具箱，默认 False
        :type toolbox: bool
        :param title: 窗口标题，默认为空字符串
        :type title: str
        :param debug: 是否启用调试模式（输出 JS 错误信息），默认 False
        :type debug: bool
        :param position: 图表位置（网格格式），支持三种格式：
                        - 整数：如 111（百位=行数，十位=列数，个位=位置索引）
                        - 元组：如 (2, 2, 1)（行数, 列数, 位置索引）
                        - 字符串：'left', 'right', 'top', 'bottom'（已弃用）
        :type position: Position
        :param marker_auto_scale: 标记是否参与价格轴自动缩放，默认 True
        :type marker_auto_scale: bool

        :raises ModuleNotFoundError: 如果未安装 PySide6 或 PyQt6
        :raises OSError: 如果平台不支持（Wayland 或 macOS）
        :raises RuntimeError: 如果无法获取原生窗口句柄
        """

        try:
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QWindow
            from PySide6.QtWidgets import QWidget
        except ImportError:
            try:
                from PyQt6.QtCore import Qt
                from PyQt6.QtGui import QWindow
                from PyQt6.QtWidgets import QWidget
            except ImportError:
                raise ModuleNotFoundError(
                    'PySide6 or PyQt6 is required for CrossProcessChart. '
                    'Install with: pip install PySide6'
                )

        self._chart = Chart(
            width=width, height=height,
            title=title, debug=debug,
            toolbox=toolbox,
            inner_width=inner_width,
            inner_height=inner_height,
            scale_candles_only=scale_candles_only,
            position=position,
            marker_auto_scale=marker_auto_scale,
            frameless=True
        )

        self._chart.show()

        hwnd = self._chart.wv.get_native_handle(self._chart._i)
        if hwnd is None:
            raise RuntimeError('Failed to get native window handle from pywebview')

        qwindow = QWindow.fromWinId(hwnd)
        qwindow.setFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ForeignWindow)
        self._container = QWidget.createWindowContainer(qwindow, parent)
        self._qwindow = qwindow

    @property
    def widget(self):
        """
        返回嵌入用的 QWidget，将其添加到 Qt 布局中。

        :return: 包装了原生窗口的 QWidget 容器
        :rtype: QWidget

        Example:
            >>> layout.addWidget(chart.widget)
        """
        return self._container

    def get_webview(self):
        """
        兼容 QtChart 接口，返回嵌入用的 QWidget。

        此方法是为了兼容旧版 API，功能与 widget 属性相同。

        :return: 包装了原生窗口的 QWidget 容器
        :rtype: QWidget
        """
        return self._container

    def resize(self, width, height):
        """
        调整嵌入窗口的大小。

        :param width: 新的宽度（像素）
        :type width: int
        :param height: 新的高度（像素）
        :type height: int

        Example:
            >>> chart.resize(1000, 600)  # 将图表调整为 1000x600
        """
        self._chart.wv.resize_window(self._chart._i, width, height)

    def exit(self):
        """
        终止子进程并清理资源。

        关闭嵌入的图表窗口，释放所有相关资源。
        调用此方法后，图表对象将不再可用。
        """
        self._chart.exit()

    def __getattr__(self, name):
        """
        将所有未定义的属性/方法委托给内部 Chart 实例。

        这使得 CrossProcessChart 可以直接调用 AbstractChart 的所有方法，
        如 set(), update(), create_line(), create_subchart() 等。

        :param name: 属性或方法名称
        :type name: str
        :return: 内部 Chart 实例的属性或方法
        :rtype: Any

        Example:
            >>> chart.set(df)  # 委托给 self._chart.set(df)
            >>> chart.create_line('SMA')  # 委托给 self._chart.create_line('SMA')
        """
        return getattr(self._chart, name)
