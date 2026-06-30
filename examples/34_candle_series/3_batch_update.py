"""示例 34-3：CandleSeries 批量更新 - update_bars 一次性追加多根 bar"""

import sys
sys.path.insert(0, '..')
from time import sleep
from lightweight_charts import Chart
from generate_data import generate_ohlcv

if __name__ == '__main__':
    chart = Chart(width=1400, height=900, title='CandleSeries 批量更新')

    df_main = generate_ohlcv(50, base_price=100, seed=42)
    df_ref = generate_ohlcv(50, base_price=200, seed=123)

    chart.set(df_main)

    ref = chart.create_candle_series(
        name='参考品种',
        pane_index=1,
        up_color='rgba(0, 150, 255, 0.8)',
        down_color='rgba(255, 100, 0, 0.8)',
    )
    ref.set(df_ref)

    # 添加 topbar 状态提示
    chart.topbar.textbox('status', '准备就绪 - 初始数据 50 根 bar', align='left')

    chart.show()

    # 第一批：追加 50 根 bar
    sleep(2)
    chart.topbar['status'].set('第一批 +50 根 bar (02-20 ~ 04-10)')
    df_batch1_main = generate_ohlcv(50, base_price=110, seed=42, start_date='2024-02-20')
    df_batch1_ref = generate_ohlcv(50, base_price=210, seed=123, start_date='2024-02-20')
    chart.update_bars(df_batch1_main)
    ref.update_bars(df_batch1_ref)
    sleep(3)

    # 第二批：再追加 50 根 bar
    chart.topbar['status'].set('第二批 +50 根 bar (04-10 ~ 05-30)')
    df_batch2_main = generate_ohlcv(50, base_price=120, seed=100, start_date='2024-04-10')
    df_batch2_ref = generate_ohlcv(50, base_price=220, seed=200, start_date='2024-04-10')
    chart.update_bars(df_batch2_main)
    ref.update_bars(df_batch2_ref)
    sleep(3)

    # 第三批：再追加 50 根 bar
    chart.topbar['status'].set('第三批 +50 根 bar (05-30 ~ 07-19)')
    df_batch3_main = generate_ohlcv(50, base_price=130, seed=77, start_date='2024-05-30')
    df_batch3_ref = generate_ohlcv(50, base_price=230, seed=88, start_date='2024-05-30')
    chart.update_bars(df_batch3_main)
    ref.update_bars(df_batch3_ref)
    sleep(3)

    chart.topbar['status'].set('完成! 共 200 根 bar (50 + 50 + 50 + 50)')

    # 在参考K线上打标记，展示批量更新后标记功能
    ref.add_marker(
        time=df_ref['time'].iloc[25],
        position='above', shape='arrow_down', color='#FF6B35',
        text='起始标记'
    )
    ref.add_marker(
        time=df_batch3_ref['time'].iloc[-1],
        position='below', shape='arrow_up', color='#0096FF',
        text='结束标记'
    )

    chart.fit()
    chart.show(wait=120)
    chart.exit()
