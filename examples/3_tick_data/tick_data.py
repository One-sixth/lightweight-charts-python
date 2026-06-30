import pandas as pd
from time import sleep
from lightweight_charts import Chart

if __name__ == '__main__':

    df1 = pd.read_csv('ohlc.csv').rename(columns={'date': 'time'})

    # Columns: time | price
    df2 = pd.read_csv('ticks.csv')

    chart = Chart()
    chart.legend(visible=True, ohlc=True, persistent=True)

    chart.set(df1)

    chart.show()

    for i, tick in df2.iterrows():
        chart.update_tick(tick)
        sleep(0.03)
