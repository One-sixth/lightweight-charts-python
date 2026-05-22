"""Example: 在 Reflex 应用中嵌入 Lightweight Charts。

运行方式（需先安装 reflex）:
    pip install lightweight-charts-python[reflex]

    方式 1（推荐）: 用 reflex 开发服务器
        cd examples/27_reflex_chart
        reflex run

    方式 2: 直接 python 运行
        python -m rx_chart.rx_chart
"""

import reflex as rx
import pandas as pd
from pathlib import Path
from lightweight_charts import ReflexChart

# ── 1. 构造图表数据 ──────────────────────────────────────────────
# 复用 examples/1_setting_data/ohlcv.csv
data_path = Path(__file__).resolve().parent.parent.parent / '1_setting_data' / 'ohlcv.csv'
df = pd.read_csv(data_path)

# ── 2. 创建并配置 ReflexChart ────────────────────────────────────
chart = ReflexChart(width=1000, height=600)

chart.set(df)
chart.layout(background_color='#0c0d0f', text_color='#d8d9db')
chart.candle_style(up_color='#26a69a', down_color='#ef5350')
chart.volume_config(up_color='#26a69a80', down_color='#ef535080')
chart.watermark('Reflex + LWC')
chart.legend(visible=True)

# 创建折线指标
sma = chart.create_line(name='sma', color='#FFD700', width=2)
sma_values = df['close'].rolling(20).mean()
sma_df = pd.DataFrame({'date': df['date'], 'sma': sma_values}).dropna()
sma.set(sma_df)

# ── 3. Reflex 页面定义 ──────────────────────────────────────────
class ChartState(rx.State):
    """图表状态（未来可扩展为响应式更新用）。"""
    pass


def index() -> rx.Component:
    return rx.vstack(
        rx.heading(
            'Lightweight Charts in Reflex',
            size='3',
            color='#d8d9db',
        ),
        rx.text(
            'K线图 + SMA 20 折线 | 嵌入方式: iframe + srcdoc',
            color='#888',
        ),
        chart.to_reflex(width='100%'),
        width='100%',
        height='100vh',
        padding='2em',
        bg='#0c0d0f',
        align='stretch',
        spacing='4',
        overflow='hidden',
    )


app = rx.App()
app.add_page(index, title='Reflex + Lightweight Charts')
