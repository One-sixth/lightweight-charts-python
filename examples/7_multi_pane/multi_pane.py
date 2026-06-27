import pandas as pd
from lightweight_charts import Chart


def calculate_sma(df, period: int = 50, name = None):
    name = name or f'SMA {period}'
    return pd.DataFrame({
        'time': df['date'],
        name: df['close'].rolling(window=period).mean()
    }) #.dropna()


def demo():
    # chart = HTMLChart(width=1200, height=800, inner_height=-500)
    # chart.export('charts.html')
    chart = Chart(width=1200, height=800, title='Multi Pane Demo')
    chart.legend(visible=True)
    df = pd.read_csv('ohlcv.csv').rename(columns={'date': 'time'})
    chart.set(df)

    # Pane 0
    line7 = chart.create_line('SMA 7', color='red', price_line=False, price_label=False)
    sma7_data = calculate_sma(df, period=7)
    line7.set(sma7_data)
    line14 = chart.create_line('SMA 14', color='blue', price_line=False, price_label=False)
    sma14_data = calculate_sma(df, period=14)
    line14.set(sma14_data)

    # Pane 1
    sma20_data = calculate_sma(df, period=20, name='Hist SMA(20)')
    line20 = chart.create_histogram('Hist SMA(20)', price_line=False, price_label=False, pane_index=1)
    line20.set(sma20_data)

    # Pane 2
    sma50_data = calculate_sma(df, period=50)
    line50 = chart.create_line('SMA 50', color='green', price_line=False, price_label=False, pane_index=2)
    line50.set(sma50_data)

    chart.show(wait=120)
    chart.exit()


if __name__ == '__main__':
    demo()
