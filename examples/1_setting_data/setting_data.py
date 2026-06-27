import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart()

    # Columns: time | open | high | low | close | volume
    df = pd.read_csv('ohlcv.csv').rename(columns={'date': 'time'})
    chart.set(df)

    chart.show(wait=120)
    chart.exit()
