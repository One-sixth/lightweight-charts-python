import pandas as pd
from lightweight_charts import Chart


def calculate_sma(df, period: int = 50):
    return pd.DataFrame({
        'time': df['date'],
        f'SMA {period}': df['close'].rolling(window=period).mean()
    }).dropna()


if __name__ == '__main__':
    chart = Chart()
    chart.legend(visible=True)

    df = pd.read_csv('ohlcv.csv')
    chart.set(df)

    line = chart.create_line('SMA 50', color='rgb(255, 0, 0)')
    sma_data = calculate_sma(df, period=50)
    line.set(sma_data)

    line2 = chart.create_line('SMA 120', color='rgb(0, 255, 0)', pane_index=1)
    sma_data = calculate_sma(df, period=120)
    line2.set(sma_data)

    chart.show(block=True)
