"""
HtmlTabChart Demo - 4-row layout: 2 subcharts x 2 panes each

Layout per strategy tab (top to bottom):
  Row 1: Subchart 1 K-line (SMA or BB)
  Row 2: Subchart 1 Volume
  Row 3: Subchart 2 K-line
  Row 4: Subchart 2 Volume

Demonstrates:
- create_subchart() for independent chart instances
- pane_index for vertical splitting within each subchart
"""

import pandas as pd
import numpy as np
from lightweight_charts import HtmlTabChart


def generate_ohlcv_data(days=100):
    """Generate simulated OHLCV data"""
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    np.random.seed(42)
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, days)
    prices = base_price * np.cumprod(1 + returns)

    data = []
    for i, date in enumerate(dates):
        open_price = prices[i] * (1 + np.random.uniform(-0.01, 0.01))
        high_price = max(open_price, prices[i]) * (1 + np.random.uniform(0, 0.02))
        low_price = min(open_price, prices[i]) * (1 - np.random.uniform(0, 0.02))
        close_price = prices[i]
        volume = np.random.randint(1000, 10000)

        data.append({
            'time': date.strftime('%Y-%m-%d'),
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
    return pd.DataFrame(data)


def calculate_sma(df, period=20):
    """Simple Moving Average"""
    return pd.DataFrame({
        'time': df['time'],
        'value': df['close'].rolling(window=period).mean()
    }).dropna()


def calculate_bollinger_bands(df, period=20, std_dev=2):
    """Bollinger Bands"""
    sma = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    return pd.DataFrame({
        'time': df['time'],
        'BB Middle': sma,
        'BB Upper': sma + (std * std_dev),
        'BB Lower': sma - (std * std_dev)
    }).dropna()


def generate_trades(df, strategy_name):
    """Generate simulated trade records"""
    trades = []
    num_trades = np.random.randint(5, 15)

    for i in range(num_trades):
        open_idx = np.random.randint(0, len(df) - 10)
        close_idx = np.random.randint(open_idx + 1, min(open_idx + 10, len(df)))
        is_long = np.random.random() > 0.5
        size = np.random.choice([1, 2, 5, 10]) * (1 if is_long else -1)

        open_price = df.iloc[open_idx]['open'] * (1 + np.random.uniform(-0.005, 0.005))
        close_price = df.iloc[close_idx]['close'] * (1 + np.random.uniform(-0.005, 0.005))

        pnl = (close_price - open_price) * size
        commission = abs(size) * 0.1
        pnlcomm = pnl - commission
        return_pct = pnlcomm / (abs(size) * open_price) * 100

        trades.append({
            'type': 0,
            'ref': f'{strategy_name}_{i+1:03d}',
            'size': int(size),
            'tradeid': f'T{i+1:04d}',
            'dateopen': str(df.iloc[open_idx]['time']),
            'priceopen': round(float(open_price), 2),
            'dateclose': str(df.iloc[close_idx]['time']),
            'priceclose': round(float(close_price), 2),
            'pnlcomm': round(float(pnlcomm), 2),
            'return_pct': round(float(return_pct), 2),
            'commission': round(float(commission), 2),
            'barlen': int(close_idx - open_idx)
        })

    return trades


def add_trade_markers(chart, trades):
    """Add buy/sell markers from trade records"""
    for trade in trades:
        chart.marker(
            time=trade['dateopen'],
            position='below' if trade['size'] > 0 else 'above',
            color='red' if trade['size'] > 0 else 'green',
            shape='arrow_up' if trade['size'] > 0 else 'arrow_down',
            text=f"Open {trade['size']}"
        )
        chart.marker(
            time=trade['dateclose'],
            position='above' if trade['size'] > 0 else 'below',
            color='green' if trade['size'] > 0 else 'red',
            shape='arrow_down' if trade['size'] > 0 else 'arrow_up',
            text=f"Close {trade['pnlcomm']:.1f}"
        )


def generate_performance_metrics():
    """Generate simulated performance metrics"""
    return pd.Series({
        'Return': f'{np.random.uniform(-10, 30):.2f}%',
        'Annual': f'{np.random.uniform(-5, 20):.2f}%',
        'MaxDD': f'{np.random.uniform(-15, -5):.2f}%',
        'Sharpe': f'{np.random.uniform(-0.5, 2.0):.2f}',
        'WinRate': f'{np.random.uniform(40, 65):.1f}%',
        'PnL Ratio': f'{np.random.uniform(0.8, 2.5):.2f}',
        'Trades': f'{np.random.randint(10, 50)}',
        'AvgDays': f'{np.random.uniform(1, 10):.1f}'
    })


def generate_parameters():
    """Generate simulated strategy parameters"""
    return pd.Series({
        'SMA Period': np.random.choice([5, 10, 20, 50]),
        'Stop Loss': f'{np.random.uniform(1, 5):.1f}%',
        'Take Profit': f'{np.random.uniform(3, 10):.1f}%',
        'Size': np.random.choice([1, 2, 5, 10]),
        'Max Pos': np.random.choice([1, 3, 5])
    })


def demo():
    """HtmlTabChart demo: 4-row layout"""
    print("HtmlTabChart Demo - 4-row layout")
    print("=" * 50)

    print("Generating data...")
    df = generate_ohlcv_data(100)
    vol_df = df[['time', 'volume']].rename(columns={'volume': 'value'})

    # ================================================================
    # Main chart: 2x1 grid, position=211 (left cell)
    # ================================================================
    chart = HtmlTabChart(
        width=1200,
        height=1200,
        position=211,
        marker_auto_scale=True
    )

    # ================================================================
    # Strategy 1: SMA
    # ================================================================
    print("  [1/2] SMA strategy (2 subcharts x 2 panes)")
    chart.set_name('SMA Strategy')
    chart.legend(visible=True)
    chart.set(df)

    # Subchart 1 K-line: pane 0 (already set above)
    sma10 = calculate_sma(df, period=10)
    sma20 = calculate_sma(df, period=20)
    chart.create_line('SMA 10', color='blue', price_line=False, price_label=False).set(sma10)
    chart.create_line('SMA 20', color='red', price_line=False, price_label=False).set(sma20)

    # Subchart 1 Volume: pane 1
    chart.create_histogram('Volume', color='#26a69a', price_line=False, price_label=False, pane_index=1).set(vol_df)

    # Subchart 2: create_subchart at position 212 (right cell)
    sub2 = chart.create_subchart(position=212)
    sub2.legend(visible=True)
    sub2.set(df)

    # Subchart 2 K-line: pane 0 (already set)
    sma50 = calculate_sma(df, period=50)
    sub2.create_line('SMA 50', color='green', price_line=False, price_label=False).set(sma50)

    # Subchart 2 Volume: pane 1
    sub2.create_histogram('Volume', color='#ff9800', price_line=False, price_label=False, pane_index=1).set(vol_df)

    # Trades + markers
    trades1 = generate_trades(df, 'SMA')
    chart.set_trades(trades1)
    add_trade_markers(chart, trades1)
    chart.set_performance_metrics(generate_performance_metrics(), 'SMA Strategy')
    chart.set_parameters_list(generate_parameters())

    # ================================================================
    # Strategy 2: Bollinger Band
    # ================================================================
    chart.new_window()

    print("  [2/2] BB strategy (2 subcharts x 2 panes)")
    chart.set_name('BB Strategy')
    chart.legend(visible=True)
    chart.set(df)

    # Subchart 1 K-line: pane 0
    bb = calculate_bollinger_bands(df, period=20, std_dev=2)
    chart.create_line('BB Middle', color='orange', price_line=False, price_label=False).set(
        pd.DataFrame({'time': bb['time'], 'value': bb['BB Middle']}))
    chart.create_line('BB Upper', color='red', price_line=False, price_label=False).set(
        pd.DataFrame({'time': bb['time'], 'value': bb['BB Upper']}))
    chart.create_line('BB Lower', color='green', price_line=False, price_label=False).set(
        pd.DataFrame({'time': bb['time'], 'value': bb['BB Lower']}))

    # Subchart 1 Volume: pane 1
    chart.create_histogram('Volume', color='#26a69a', price_line=False, price_label=False, pane_index=1).set(vol_df)

    # Subchart 2: create_subchart
    sub2 = chart.create_subchart(position=212)
    sub2.legend(visible=True)
    sub2.set(df)

    # Subchart 2 K-line: pane 0 (just K-line, no extra indicators)
    # Subchart 2 Volume: pane 1
    sub2.create_histogram('Volume', color='#ff9800', price_line=False, price_label=False, pane_index=1).set(vol_df)

    # Trades + markers
    trades2 = generate_trades(df, 'BB')
    chart.set_trades(trades2)
    add_trade_markers(chart, trades2)
    chart.set_performance_metrics(generate_performance_metrics(), 'BB Strategy')
    chart.set_parameters_list(generate_parameters())

    # ================================================================
    # Strategy 3: Absolute position (set_position)
    # ================================================================
    chart.new_window()

    print("  [3/3] Absolute position (set_position)")
    chart.set_name('Absolute Pos')
    chart.legend(visible=True)
    chart.set(df)

    # Absolute position: top-left quarter (0, 0, 0.5, 0.5)
    chart.set_position(x=0, y=0, width=0.5, height=0.5)

    # SMA on the main chart
    sma10 = calculate_sma(df, period=10)
    chart.create_line('SMA 10', color='blue', price_line=False, price_label=False).set(sma10)

    # Subchart 2: bottom-right quarter (0.5, 0.5, 0.5, 0.5)
    sub2 = chart.create_subchart(position=212)
    sub2.legend(visible=True)
    sub2.set(df)
    sub2.set_position(x=0.5, y=0.5, width=0.5, height=0.5)

    # Trades + markers
    trades3 = generate_trades(df, 'AbsPos')
    chart.set_trades(trades3)
    add_trade_markers(chart, trades3)
    chart.set_performance_metrics(generate_performance_metrics(), 'Absolute Pos')
    chart.set_parameters_list(generate_parameters())

    # ================================================================
    # Export
    # ================================================================
    print("Exporting...")
    filename = 'html_tab_chart_demo.html'
    chart.export(filename)

    # iframe embed
    chart_content_filename = 'html_tab_chart_iframe_content.html'
    with open(chart_content_filename, 'w', encoding='utf-8') as f:
        f.write(chart.get_html())

    iframe_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Iframe Embed Test</title>
    <style>
        body {{ margin: 0; padding: 20px; font-family: Arial, sans-serif; }}
        h2 {{ color: #333; }}
        iframe {{ border: 1px solid #ccc; width: 100%; height: 80vh; }}
    </style>
</head>
<body>
    <h2>HtmlTabChart Iframe Embed Test</h2>
    <iframe src="{chart_content_filename}"></iframe>
</body>
</html>'''
    iframe_filename = 'html_tab_chart_iframe_demo.html'
    with open(iframe_filename, 'w', encoding='utf-8') as f:
        f.write(iframe_html)

    print("=" * 50)
    print("Done!")
    print(f"  Standalone : {filename}")
    print(f"  iframe page: {iframe_filename}")
    print(f"  iframe data: {chart_content_filename}")
    print()
    print("Layout per strategy tab:")
    print("  Strategy 1 (Subcharts T/B):")
    print("    [Subchart 1] K-line + SMA       (position=211, pane 0)")
    print("    [Subchart 1] Volume              (position=211, pane 1)")
    print("    [Subchart 2] K-line              (position=212, pane 0)")
    print("    [Subchart 2] Volume              (position=212, pane 1)")
    print("  Strategy 2 (Panes T/B):")
    print("    [Subchart 1] K-line + BB         (position=211, pane 0)")
    print("    [Subchart 1] Volume              (position=211, pane 1)")
    print("    [Subchart 2] K-line              (position=212, pane 0)")
    print("    [Subchart 2] Volume              (position=212, pane 1)")
    print("  Strategy 3 (Absolute Position):")
    print("    [Chart] K-line + SMA             (set_position 0,0,50%,50%)")
    print("    [Subchart] K-line                (set_position 50%,50%,50%,50%)")


if __name__ == '__main__':
    demo()
