import inspect
from typing import Dict, Literal, Callable, Optional

from .util import jbool, Pane


ALIGN = Literal['left', 'right']


class Widget(Pane):
    """顶栏控件的基类，管理值状态和事件回调。"""
    def __init__(self, topbar, value, func: Optional[Callable] = None, convert_boolean=False):
        """
        :param topbar: 所属 TopBar 实例
        :param value: 初始值
        :param func: 值变化时的回调
        :param convert_boolean: 是否将 'true'/'false' 字符串转为 bool
        """
        super().__init__(topbar.win)
        self.value = value

        def wrapper(v):
            if convert_boolean:
                self.value = False if v == 'false' else True
            else:
                self.value = v
            func(topbar._chart)

        async def async_wrapper(v):
            self.value = v
            await func(topbar._chart)

        self.win.handlers[self.id] = async_wrapper if inspect.iscoroutinefunction(func) else wrapper


class TextWidget(Widget):
    """文本显示控件。"""
    def __init__(self, topbar, initial_text, align, func):
        super().__init__(topbar, value=initial_text, func=func)

        callback_name = f'"{self.id}"' if func else ''

        self.run_script(f'{self.id} = {topbar.id}.makeTextBoxWidget("{initial_text}", "{align}", {callback_name})')

    def set(self, string):
        """更新显示的文本。"""
        self.value = string
        self.run_script(f'{self.id}.innerText = "{string}"')


class SwitcherWidget(Widget):
    """选项切换控件（点击切换不同选项）。"""
    def __init__(self, topbar, options, default, align, func):
        super().__init__(topbar, value=default, func=func)
        self.options = list(options)
        self.run_script(f'{self.id} = {topbar.id}.makeSwitcher({self.options}, "{default}", "{self.id}", "{align}")')

    def set(self, option):
        """切换到指定选项。"""
        if option not in self.options:
            raise ValueError(f"option '{option}' does not exist within {self.options}.")
        self.run_script(f'{self.id}.onItemClicked("{option}")')
        self.value = option


class MenuWidget(Widget):
    """下拉菜单控件。"""
    def __init__(self, topbar, options, default, separator, align, func):
        super().__init__(topbar, value=default, func=func)
        self.options = list(options)
        self.run_script(f'''
        {self.id} = {topbar.id}.makeMenu({list(options)}, "{default}", {jbool(separator)}, "{self.id}", "{align}")
        ''')

    # TODO this will probably need to be fixed
    def set(self, option):
        """选中指定菜单项。"""
        if option not in self.options:
            raise ValueError(f"Option {option} not in menu options ({self.options})")
        self.value = option
        self.run_script(f'''
            {self.id}._clickHandler("{option}")
        ''')
        # self.win.handlers[self.id](option)

    def update_items(self, *items: str):
        """更新菜单项列表。"""
        self.options = list(items)
        self.run_script(f'{self.id}.updateMenuItems({self.options})')


class ButtonWidget(Widget):
    """按钮控件，支持普通按钮和开关按钮。"""
    def __init__(self, topbar, button, separator, align, toggle, func):
        super().__init__(topbar, value=False, func=func, convert_boolean=toggle)
        self.run_script(
            f'{self.id} = {topbar.id}.makeButton("{button}", "{self.id}", {jbool(separator)}, true, "{align}", {jbool(toggle)})')

    def set(self, string):
        """更新按钮文本。"""
        # self.value = string
        self.run_script(f'{self.id}.elem.innerText = "{string}"')


class TopBar(Pane):
    """顶栏容器，管理多个控件（文本框、切换器、菜单、按钮）。"""
    def __init__(self, chart):
        super().__init__(chart.win)
        self._chart = chart
        self._widgets: Dict[str, Widget] = {}
        self._created = False

    def _create(self):
        """内部方法：在 JS 端创建顶栏。"""
        if self._created:
            return
        self._created = True
        self.run_script(f'{self.id} = {self._chart.id}.createTopBar()')

    def __getitem__(self, item):
        """通过名称访问已注册的控件。"""
        if widget := self._widgets.get(item):
            return widget
        raise KeyError(f'Topbar widget "{item}" not found.')

    def get(self, widget_name):
        """获取已注册的控件，不存在则返回 None。"""
        return self._widgets.get(widget_name)

    def switcher(self, name, options: tuple, default: str = None,
                 align: ALIGN = 'left', func: callable = None):
        """添加一个选项切换器控件。"""
        self._create()
        self._widgets[name] = SwitcherWidget(self, options, default if default else options[0], align, func)

    def menu(self, name, options: tuple, default: str = None, separator: bool = True,
             align: ALIGN = 'left', func: callable = None):
        """添加一个下拉菜单控件。"""
        self._create()
        self._widgets[name] = MenuWidget(self, options, default if default else options[0], separator, align, func)

    def textbox(self, name: str, initial_text: str = '',
                align: ALIGN = 'left', func: callable = None):
        """添加一个文本显示控件。"""
        self._create()
        self._widgets[name] = TextWidget(self, initial_text, align, func)

    def button(self, name, button_text: str, separator: bool = True,
               align: ALIGN = 'left', toggle: bool = False, func: callable = None):
        """添加一个按钮控件。
        :param toggle: True 则为开关按钮，点击在 on/off 间切换
        """
        self._create()
        self._widgets[name] = ButtonWidget(self, button_text, separator, align, toggle, func)
