import inspect
import random
from typing import Union, Optional, Callable

from .util import jbool, Pane, NUM


class Section(Pane):
    """表格的页眉或页脚区域，支持多文本框。"""
    def __init__(self, table, section_type):
        """
        :param table: 所属 Table 实例
        :param section_type: 'header' 或 'footer'
        """
        super().__init__(table.win)
        self._table = table
        self.type = section_type

    def __call__(self, number_of_text_boxes: int, func: Optional[Callable] = None):
        """创建指定数量的文本框。
        :param number_of_text_boxes: 文本框数量
        :param func: 点击回调，接收 (table, box_index)"""
        if func is not None:
            self.win.handlers[self.id] = lambda boxId: func(self._table, int(boxId))
        self.run_script(f'''
        {self._table.id}.makeSection("{self.id}", "{self.type}", {number_of_text_boxes}, {"true" if func else ""})
        ''')

    def __setitem__(self, key, value):
        """设置某个文本框的文本内容。"""
        self.run_script(f'{self._table.id}.{self.type}[{key}].innerText = "{value}"')


class Row(dict):
    """表格行，支持按列设置值、背景色和文字颜色。"""
    def __init__(self, table, id, items):
        super().__init__()
        self.run_script = table.run_script
        self._table = table
        self.id = id
        self.meta = {}
        self.run_script(f'{self._table.id}.newRow("{self.id}", {jbool(table.return_clicked_cells)})')
        for key, val in items.items():
            self[key] = val

    def __setitem__(self, column, value):
        if isinstance(column, tuple):
            [self.__setitem__(col, val) for col, val in zip(column, value)]
            return
        original_value = value
        if column in self._table._formatters:
            value = self._table._formatters[column].replace(self._table.VALUE, str(value))
        self.run_script(f'{self._table.id}.updateCell("{self.id}", "{column}", "{value}")')
        return super().__setitem__(column, original_value)

    def background_color(self, column, color): self._style('backgroundColor', column, color)

    def text_color(self, column, color): self._style('textColor', column, color)

    def _style(self, style, column, arg):
        """设置单元格样式。"""
        self.run_script(f"{self._table.id}.styleCell({self.id}, '{column}', '{style}', '{arg}')")

    def delete(self):
        """删除该行。"""
        self.run_script(f"{self._table.id}.deleteRow('{self.id}')")
        self._table.pop(self.id)


class Table(Pane, dict):
    """可交互的表格组件，支持拖拽、自定义样式、行点击回调。"""
    VALUE = 'CELL__~__VALUE__~__PLACEHOLDER'

    def __init__(
            self,
            window,
            width: NUM,
            height: NUM,
            headings: tuple,
            widths: Optional[tuple] = None,
            alignments: Optional[tuple] = None,
            position='left',
            draggable: bool = False,
            background_color: str = '#121417',
            border_color: str = 'rgb(70, 70, 70)',
            border_width: int = 1,
            heading_text_colors: Optional[tuple] = None,
            heading_background_colors: Optional[tuple] = None,
            return_clicked_cells: bool = False,
            func: Optional[Callable] = None
    ):
        dict.__init__(self)
        Pane.__init__(self, window)
        self._formatters = {}
        self.headings = headings
        self.is_shown = True
        def wrapper(rId, cId=None):
            if return_clicked_cells:
                func(self[rId], cId)
            else:
                func(self[rId])

        async def async_wrapper(rId, cId=None):
            if return_clicked_cells:
                await func(self[rId], cId)
            else:
                await func(self[rId])

        self.win.handlers[self.id] = async_wrapper if inspect.iscoroutinefunction(func) else wrapper
        self.return_clicked_cells = return_clicked_cells

        self.run_script(f'''
        {self.id} = new Lib.Table(
            {width},
            {height},
            {list(headings)},
            {list(widths) if widths else []},
            {list(alignments) if alignments else []},
            '{position}',
            {jbool(draggable)},
            '{background_color}',
            '{border_color}',
            {border_width},
            {list(heading_text_colors) if heading_text_colors else []},
            {list(heading_background_colors) if heading_background_colors else []}
        )''')
        self.run_script(f'{self.id}.callbackName = "{self.id}"') if func else None
        self.footer = Section(self, 'footer')
        self.header = Section(self, 'header')

    def new_row(self, *values, id=None) -> Row:
        """添加新行，返回 Row 实例。"""
        row_id = random.randint(0, 99_999_999) if not id else id
        self[row_id] = Row(self, row_id, {heading: item for heading, item in zip(self.headings, values)})
        return self[row_id]

    def clear(self):
        """清空所有行。"""
        self.run_script(f"{self.id}.clearRows()"), super().clear()

    def get(self, __key: Union[int, str]) -> Row:
        """通过 ID 获取行。"""
        return super().get(int(__key))

    def __getitem__(self, item):
        """通过 ID 获取行。"""
        return super().__getitem__(int(item))

    def format(self, column: str, format_str: str):
        """设置列的格式化模板（用 CELL__~__VALUE__~__PLACEHOLDER 占位）。"""
        self._formatters[column] = format_str

    def resize(self, width: NUM, height: NUM):
        """调整表格尺寸。"""
        self.run_script(f'{self.id}.reSize({width}, {height})')

    def visible(self, visible: bool):
        """显示或隐藏表格。"""
        self.is_shown = visible
        self.run_script(f"""
        {self.id}._div.style.display = '{'flex' if visible else 'none'}'
        {self.id}._div.{'add' if visible else 'remove'}EventListener('mousedown', {self.id}.onMouseDown)
        """)

    def delete(self):
        """
        Irreversibly destroys the table and removes it from the DOM.
        """
        if hasattr(self, '_chart') and self in self._chart._tables:
            self._chart._tables.remove(self)
        if self.id in self.win.handlers:
            del self.win.handlers[self.id]
        self.clear()
        self.run_script(f'''
        {self.id}._div.remove()
        delete {self.id}
        ''')
