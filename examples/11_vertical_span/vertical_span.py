"""
Demonstrates the vertical_span feature — highlighting regions on the chart.
"""
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()

    df = pd.read_csv('../1_setting_data/ohlcv.csv')
    chart.set(df)

    # Highlight a range between two dates
    chart.vertical_span(
        start_time='2011-01-05',
        end_time='2017-06-10',
        color='rgba(252, 219, 3, 0.15)',
    )

    # Multiple single-time highlights (e.g. earnings events)
    chart.vertical_span(
        start_time=['2018-06-20', '2018-09-18', '2019-12-17'],
        color='rgba(255, 100, 100, 0.6)',
    )

    # You can also use pd.Timestamp or datetime objects
    chart.vertical_span(
        start_time=pd.Timestamp('2020-03-01'),
        end_time=pd.Timestamp('2021-08-15'),
        color='rgba(100, 200, 255, 0.15)',
    )

    # single-time highlights
    chart.vertical_span(
        start_time=pd.Timestamp('2022-03-01'),
        color='rgba(250, 30, 128, 0.7)',
    )

    chart.show(block=True)
