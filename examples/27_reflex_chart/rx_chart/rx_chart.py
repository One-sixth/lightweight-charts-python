"""Example: Reflex 互动图表 — 实时 bar 推送 + crosshair 回调。"""

import reflex as rx
import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path
from lightweight_charts import ReflexChart

# ── 1. 数据 ────────────────────────────────────────────────────
data_path = Path(__file__).resolve().parent.parent.parent / '1_setting_data' / 'ohlcv.csv'
ohlcv_df = pd.read_csv(data_path).rename(columns={'date': 'time'})

# ── 2. 创建 ReflexChart ────────────────────────────────────────
chart = ReflexChart(width=1000, height=600, auto_flush=True)

chart.set(ohlcv_df)
chart.layout(background_color='#0c0d0f', text_color='#d8d9db')
chart.candle_style(up_color='#26a69a', down_color='#ef5350')
chart.volume_config(up_color='#26a69a80', down_color='#ef535080')
chart.watermark('Reflex + LWC')
chart.legend(visible=True)

sma = chart.create_line(name='sma', color='#FFD700', width=2)
sma.set(pd.DataFrame({
    'time': ohlcv_df['time'],
    'value': ohlcv_df['close'].rolling(20).mean()
}).dropna())

# ── 3. 辅助: 基于最后一行生成随机新 bar ────────────────────────
_last = ohlcv_df.iloc[-1]

def _next_bar():
    global _last
    change = random.uniform(-3, 3)
    dt = datetime.strptime(str(_last['time']), '%Y-%m-%d') + timedelta(days=1)
    bar = pd.Series({
        'time': dt.strftime('%Y-%m-%d'),
        'open': _last['close'],
        'high': max(_last['close'], _last['close'] + change) + random.uniform(0, 0.5),
        'low':  min(_last['close'], _last['close'] + change) - random.uniform(0, 0.5),
        'close': round(_last['close'] + change, 2),
        'volume': int(_last['volume'] * random.uniform(0.8, 1.2)),
    })
    _last = bar
    return bar

# ── 4. Reflex State ────────────────────────────────────────────
class ChartState(rx.State):
    bar_count: int = 0
    crosshair_info: str = ''

    def tick(self):
        bar = _next_bar()
        chart.update_bar(bar)
        self.bar_count += 1
        result = chart.flush()
        return result

    def on_crosshair(self, payload: str):
        self.crosshair_info = payload
        try:
            from lightweight_charts.util import parse_event_message
            func, args = parse_event_message(chart.win, payload)
            func(*args)
        except Exception:
            pass

    def mount(self):
        return rx.call_script("""
if (!window.__LWC_BRIDGE) {
    window.__LWC_BRIDGE = true;
    window.addEventListener('message', function(e) {
        if (e.data && e.data.type === 'lwc-callback') {
            var el = document.getElementById('cb-buffer');
            if (el) {
                var setter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                setter.call(el, e.data.payload);
                el.dispatchEvent(new Event('input', {bubbles: true}));
            }
        }
    });
}
""")
# ── 注册 crosshair 回调 ──────────────────────────────────────────
chart.events.crosshair_move += lambda c, d: print(f'Crosshair: {d}')

# ── 5. 页面 ────────────────────────────────────────────────────
def index() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.heading('Lightweight Charts in Reflex', size='3', color='#d8d9db'),
            rx.spacer(),
            rx.text(ChartState.crosshair_info, color='#aaa', font_size='14px'),
            rx.spacer(),
            rx.text(f'Bars: {ChartState.bar_count}', color='#888'),
            rx.button('+1 Bar', on_click=ChartState.tick, color_scheme='gray',
                      border_radius='md'),
        ),
        chart.to_reflex(id='lwc-frame', width='100%'),
        rx.input(id='cb-buffer', on_change=ChartState.on_crosshair,
                 style={'opacity': 0, 'position': 'absolute', 'width': 0, 'height': 0, 'pointer-events': 'none'}),
        width='100%', height='100vh',
        padding='1em', bg='#0c0d0f',
        align='stretch', spacing='4', overflow='hidden',
    )


app = rx.App()
app.add_page(index, on_load=ChartState.mount, title='Reflex + Live Charts')
