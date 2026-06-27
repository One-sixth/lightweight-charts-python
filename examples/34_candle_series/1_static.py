"""示例 34-1：CandleSeries 静态演示 - 两组 K 线并排显示"""

import sys
sys.path.insert(0, '..')
from lightweight_charts import Chart
from generate_data import generate_ohlcv

if __name__ == '__main__':
    chart = Chart(width=1400, height=900, title='CandleSeries 静态演示')

    # 主K线 (pane 0)
    df_main = generate_ohlcv(100, base_price=100, seed=42)
    chart.set(df_main)
    chart.candle_style(
        up_color='rgba(39, 157, 130, 100)',
        down_color='rgba(200, 97, 100, 100)'
    )

    # 参考K线 (pane 1)
    df_ref = generate_ohlcv(100, base_price=200, seed=123)
    ref = chart.create_candle_series(
        name='参考品种',
        pane_index=1,
        up_color='rgba(0, 150, 255, 0.8)',
        down_color='rgba(255, 100, 0, 0.8)',
        price_line=False,
        price_label=True,
    )
    ref.set(df_ref)

    # 打标记
    ref.marker(time=df_ref['time'].iloc[20], position='above',
               shape='arrow_down', color='#FF6B35', text='卖出信号')
    ref.marker(time=df_ref['time'].iloc[50], position='below',
               shape='arrow_up', color='#0096FF', text='买入信号')

    chart.fit()
    chart.show(wait=120)
    chart.exit()
