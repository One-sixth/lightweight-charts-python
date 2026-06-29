import json
from typing import Callable


class _CallbackList:
    """支持 += / -= 的回调列表。

    用法：
        chart.toolbox.on_change += my_func   # 注册
        chart.toolbox.on_change -= my_func   # 卸载
    """
    def __init__(self):
        self._callbacks: list[Callable] = []

    def __iadd__(self, func: Callable):
        self._callbacks.append(func)
        return self

    def __isub__(self, func: Callable):
        if func in self._callbacks:
            self._callbacks.remove(func)
        return self

    def __len__(self):
        return len(self._callbacks)

    def __bool__(self):
        return True  # 永远为 True，不被 __len__ 影响

    def emit(self, *args):
        for func in self._callbacks[:]:
            try:
                func(*args)
            except Exception as e:
                print(f'[ToolBox] on_change callback error: {e}')

    def clear(self):
        self._callbacks.clear()


class DrawingInfo:
    """单个 drawing 的元信息。"""
    __slots__ = ('id', 'type', 'points', 'options')

    def __init__(self, id: str, type: str, points: list, options: dict):
        self.id = id
        self.type = type
        self.points = points
        self.options = options

    def __repr__(self):
        return f'<DrawingInfo type={self.type} id={self.id}>'


class ToolBox:
    def __init__(self, chart):
        self.run_script = chart.run_script
        self.id = chart.id
        self._save_under = None
        self.drawings: dict = {}            # tag → JSON（save_under 持久化）
        self._chart = chart

        # 回调系统：支持 += / -= 注册/卸载
        self.on_change = _CallbackList()

        # 内部 drawing 列表：同步 JS 端的 drawing 状态
        self._drawing_list: list[DrawingInfo] = []

        self._build()

    def _build(self):
        """（重建）注册 handler + 创建 JS toolBox。"""
        self._chart.win.handlers[f'save_drawings{self.id}'] = self._on_callback
        self.run_script(f'{self.id}.createToolBox()')

    def _delete(self):
        """（销毁）移除 handler + 清空所有 Python 状态 + 销毁 JS toolBox。

        顺序关键：必须先清理 JS（此时 handler 仍在），再移除 Python handler。
        否则 JS 清理过程中触发的回调（如 onChanged → saveDrawings）会找不到 handler。
        """
        # 1. 先清理 JS（handler 仍在，回调能正常处理）
        self.run_script(f'''
            if ({self.id}.toolBox) {{
                {self.id}.toolBox._cleanup();
            }}
        ''')
        # 2. JS 清理完毕后再移除 Python handler
        self._chart.win.handlers.pop(f'save_drawings{self.id}', None)
        # 清空 Python 状态
        self.drawings.clear()
        self._drawing_list.clear()
        self.on_change.clear()

    @property
    def drawings_list(self) -> list[DrawingInfo]:
        """返回当前图表中所有 drawing 的元信息列表（只读快照）。"""
        return list(self._drawing_list)

    def _on_callback(self, raw_msg: str):
        """JS 端 saveDrawings 触发时的内部处理。"""
        try:
            items = json.loads(raw_msg)
        except (json.JSONDecodeError, TypeError):
            items = []

        # 更新内部 drawing 列表
        self._drawing_list.clear()
        for i, d in enumerate(items):
            self._drawing_list.append(DrawingInfo(
                id=f'{d.get("type", "Drawing")}_{i}',
                type=d.get('type', 'Unknown'),
                points=d.get('points', []),
                options=d.get('options', {}),
            ))

        # 更新 save_under 存储
        if self._save_under:
            self.drawings[self._save_under.value] = items

        # 触发回调
        self.on_change.emit(self._drawing_list)

    def save_drawings_under(self, widget: 'Widget'):
        """
        Drawings made on charts will be saved under the widget given. eg `chart.toolbox.save_drawings_under(chart.topbar['symbol'])`.
        """
        self._save_under = widget

    def load_drawings(self, tag: str):
        """
        Loads and displays the drawings on the chart stored under the tag given.
        """
        if not self.drawings.get(tag):
            return
        self.run_script(f'if ({self.id}.toolBox) {self.id}.toolBox.loadDrawings({json.dumps(self.drawings[tag])})')

    def import_drawings(self, file_path):
        """
        Imports a list of drawings stored at the given file path.
        """
        with open(file_path, 'r') as f:
            json_data = json.load(f)
            self.drawings = json_data

    def export_drawings(self, file_path):
        """
        Exports the current list of drawings to the given file path.
        """
        with open(file_path, 'w+') as f:
            json.dump(self.drawings, f, indent=4)

    def clear_drawings(self):
        """清空所有绘图。"""
        self.run_script(f'if ({self.id}.toolBox) {self.id}.toolBox.clearDrawings()')

    def reposition_drawings(self):
        """将绘图重新定位到当前时间轴。"""
        self.run_script(f'{self.id}.toolBox?._drawingTool.repositionOnTime()')
