from typing import Optional

from .widgets import StaticLWC

try:
    import reflex as rx
except ImportError:
    rx = None


class ReflexChart(StaticLWC):
    """基于 Reflex 框架的图表组件。

    生成自包含的 HTML，可嵌入 Reflex 应用。
    用法与 StreamlitChart / JupyterChart 类似。

    两种使用方式:
    1. 纯 HTML 生成（无需安装 reflex）:
        chart = ReflexChart(width=900, height=600)
        chart.set(df)
        html_str = chart.get_html()

    2. Reflex 组件嵌入 + 实时更新（需 pip install reflex）:
        chart = ReflexChart(width=900, height=600, auto_flush=True)
        chart.set(df)
        # 在 Reflex 页面中:
        def index() -> rx.Component:
            return rx.vstack(chart.to_reflex(), ...)
        # 更新数据:
        chart.update(bar); return chart.flush()  # → rx.call_script(postMessage)
    """

    def __init__(self, width: Optional[int] = None, height: Optional[int] = None,
                 inner_width: float = 1.0, inner_height: float = 1.0,
                 scale_candles_only: bool = False, toolbox: bool = False,
                 output_file: Optional[str] = None,
                 auto_flush: bool = True):
        """
        :param width: 图表宽度（像素）
        :param height: 图表高度（像素）
        :param inner_width: 图表在容器中的宽度比例 (0~1)
        :param inner_height: 图表在容器中的高度比例 (0~1)
        :param scale_candles_only: 缩放时仅依据 K 线
        :param toolbox: 是否启用绘图工具箱
        :param output_file: 可选，调用 load() 时写入的 HTML 文件路径
        :param auto_flush: 加载后自动将增量 JS 加入发送队列
        """
        self._auto_flush = auto_flush
        self._pending = []
        self._output_file = output_file
        super().__init__(width, height, inner_width, inner_height,
                         scale_candles_only, toolbox, autosize=True)
        self._iframe_id = 'lwc-frame'

    def get_html(self) -> str:
        """生成并返回完整的自包含 HTML 字符串（无需 reflex 包）。"""
        self.export()
        return self._build_html()

    def _build_html(self) -> str:
        fill_css = (
            '<style>'
            'html,body,#container{width:100%;height:100%;min-height:100vh;margin:0;padding:0}'
            '</style>'
        )
        head_close = '</head>'
        html_init = self._html_init.replace(
            head_close, fill_css + head_close
        )
        messaging = (
            'window.addEventListener("message",(e)=>{'
            'if(e.data?.type==="lwc-eval"){'
            'try{eval(e.data.script)}catch(e){console.error("iframe eval error:",e)}'
            '}'
            '});'
            'window.callbackFunction=(msg)=>{'
            'window.parent.postMessage('
            'JSON.stringify({type:"lwc-callback",payload:msg}),"*")'
            '};'
        )
        return (f"{html_init}{messaging}  (async ()=> {{\n{self._html}\n}})();\n"
                "</script></body></html>")

    def _export(self):
        """若指定了 output_file，写入文件。"""
        if self._output_file:
            with open(self._output_file, 'w', encoding='utf-8') as f:
                f.write(self._build_html())

    def run_script(self, script, run_last=False):
        short_id = self.id.replace('window.', '', 1)
        if script.startswith(f'window.{short_id} = ') and 'new Lib.Handler' in script:
            import json as _json
            guard = (
                f';!function(){{'
                f'var h=window.{short_id};'
                f'if(h){{'
                f'Lib.Handler.removeHandlerFromAll({_json.dumps(self.id)});'
                f'try{{h.chart.remove()}}catch(e){{}}'
                f'try{{h.wrapper.remove()}}catch(e){{}}'
                f'delete window.{short_id};'
                f'}}'
                f'}}();'
            )
            script = guard + script
        super().run_script(script, run_last)
        if self._auto_flush:
            self._pending.append(script)

    def flush(self):
        """将 _pending 中的增量脚本直接 postMessage 给 iframe。

        返回 `rx.call_script(...)` 或 None（无待发脚本）。
        在 State handler 中 return 即可：
            def handle(self): chart.update(bar); return chart.flush()
        """
        if not self._pending:
            return None
        import json as _json
        scripts = '; '.join(self._pending)
        self._pending = []
        encoded = _json.dumps(scripts)
        _id = _json.dumps(self._iframe_id)
        return rx.call_script(
            f'document.getElementById({_id})'
            f'?.contentWindow?.postMessage({{type:"lwc-eval",script:{encoded}}},"*")'
        )

    def to_reflex(self, id: str = 'lwc-frame', width: Optional[str] = None,
                  height: Optional[str] = None) -> 'rx.Component':
        """将图表包装为 Reflex 组件。

        :param id: iframe DOM id（用于 postMessage 定位）
        :param width: CSS 宽度值，如 '100%', '900px'（默认 100%）
        :param height: CSS 高度值，如 '600px'（默认 None，由 flex 撑满）
        :return: rx.Component 实例
        """
        if rx is None:
            raise ModuleNotFoundError(
                'reflex is required to use to_reflex(). '
                'Install it via: pip install reflex'
            )
        import base64

        self._iframe_id = id
        html_str = self.get_html()
        b64 = base64.b64encode(html_str.encode('utf-8')).decode('utf-8')
        self._pending = []  # 清理 setup 阶段积累的脚本（已包含于 iframe HTML）

        style = {'border': 'none', 'width': '100%'}
        if height is not None:
            style['height'] = height
        else:
            style['flex'] = '1'
            style['minHeight'] = '0'

        return rx.el.iframe(
            id=id,
            src=f'data:text/html;base64,{b64}',
            style=style,
        )
